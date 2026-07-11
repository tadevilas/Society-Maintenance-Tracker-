"""
examples/mcp_client_server/sample_server.py
--------------------------------------------
Standalone MCP server for the Society Maintenance data.
Does NOT touch server/main.py — has its own FastMCP instance.

Two modes:
  • stdio (default) — used by MultiServerMCPClient as a subprocess
  • sse             — used for external clients (Claude Desktop, Cursor, etc.)

Run in stdio mode (subprocess, called by sample_tools.py automatically):
    fastmcp run examples/mcp_client_server/sample_server.py

Run in SSE mode (persistent server, external clients):
    python examples/mcp_client_server/sample_server.py --sse
    → listens at http://localhost:8100/sse
"""

import sys
from pathlib import Path

# Make project root importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp.server.fastmcp import FastMCP
from reports.generator import generate_pending_excel, generate_balance_excel
from server.data_loader import (
    get_all_months,
    get_pending_maintenance,
    get_collected_maintenance,
    get_expense_summary,
    get_flat_history,
    get_balance_sheet,
)

# ── MCP server instance ────────────────────────────────────────────────────────
mcp = FastMCP("Society Maintenance MCP Server")

PORT = 8100   # different from the FastAPI server (8000) to avoid conflicts


# ── Helper ─────────────────────────────────────────────────────────────────────
def _df_to_records(df) -> list[dict]:
    return df.where(df.notna(), None).to_dict(orient="records")


# ── MCP Tool registrations ─────────────────────────────────────────────────────
# Identical business logic as server/main.py — just registered on this mcp instance.

@mcp.tool()
def tool_get_all_months() -> dict:
    """Return all available months in the society data."""
    return {"months": get_all_months()}


@mcp.tool()
def tool_get_pending_maintenance(month: str = "", year: int = 0) -> dict:
    """
    Get flats that have NOT paid maintenance.
    Pass month like 'Jan_2024' OR year like 2024.
    """
    df = get_pending_maintenance(month=month or None, year=year or None)
    result = {"period": month or str(year), "count": len(df), "pending": _df_to_records(df)}
    if year and not month and "total_due" in df.columns:
        result["grand_total_due"] = int(df["total_due"].sum())
    return result


@mcp.tool()
def tool_get_balance_sheet(month: str = "", year: int = 0) -> dict:
    """Get income vs expenses balance sheet for a given month or year."""
    return get_balance_sheet(month=month or None, year=year or None)


@mcp.tool()
def tool_get_expense_summary(month: str = "", year: int = 0) -> dict:
    """Get expenses grouped by type (Cleaning, Electricity, Water Bill, etc.)."""
    df = get_expense_summary(month=month or None, year=year or None)
    return {"expenses": _df_to_records(df)}


@mcp.tool()
def tool_get_flat_history(flat_number: int) -> dict:
    """Get full payment history for a specific flat. Example: flat_number=601"""
    df = get_flat_history(flat_number)
    if df.empty:
        return {"error": f"Flat {flat_number} not found."}
    return {
        "flat_number":  flat_number,
        "name":         str(df.iloc[0]["name"]),
        "total_paid":   float(df["amount"].sum()),
        "months_count": len(df),
        "history":      _df_to_records(df),
    }


@mcp.tool()
def tool_get_collected_maintenance(month: str = "", year: int = 0) -> dict:
    """Get flats that HAVE paid maintenance for a given month or year."""
    df = get_collected_maintenance(month=month or None, year=year or None)
    return {"period": month or str(year), "count": len(df), "collected": _df_to_records(df)}


@mcp.tool()
def tool_download_pending_report(month: str = "", year: int = 0) -> dict:
    """
    Generate and save a pending maintenance Excel report to the reports/ folder.
    Pass month like 'Jan_2024' OR year like 2024.
    Returns the saved file path and size so the caller knows where to find it.
    """
    file_bytes = generate_pending_excel(month=month or None, year=year or None)
    period = month or str(year)
    out_path = Path(__file__).parent.parent.parent / "downloads" / f"pending_maintenance_{period}.xlsx"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(file_bytes)
    return {
        "status":    "saved",
        "file_path": str(out_path),
        "filename":  out_path.name,
        "size_kb":   round(len(file_bytes) / 1024, 1),
        "message":   f"Pending maintenance report for {period} saved to {out_path.name}",
    }


@mcp.tool()
def tool_download_balance_report(month: str = "", year: int = 0) -> dict:
    """
    Generate and save a balance sheet Excel report to the reports/ folder.
    Pass month like 'Jan_2024' OR year like 2024, or omit both for all-time.
    Returns the saved file path and size so the caller knows where to find it.
    """
    file_bytes = generate_balance_excel(month=month or None, year=year or None)
    period = month or str(year) if (month or year) else "all"
    out_path = Path(__file__).parent.parent.parent / "downloads" / f"balance_sheet_{period}.xlsx"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(file_bytes)
    return {
        "status":    "saved",
        "file_path": str(out_path),
        "filename":  out_path.name,
        "size_kb":   round(len(file_bytes) / 1024, 1),
        "message":   f"Balance sheet report for {period} saved to {out_path.name}",
    }


# ── Entry point ────────────────────────────────────────────────────────────────
# When fastmcp launches this file as a subprocess (stdio transport),
# it does NOT call __main__ — it imports the module and calls mcp.run() itself.
# The __main__ block below is only for running manually in SSE mode.
if __name__ == "__main__":
    import sys as _sys
    if "--sse" in _sys.argv:
        print(f"Starting MCP SSE server on http://localhost:{PORT}/sse ...")
        mcp.run(transport="sse", host="0.0.0.0", port=PORT)
    else:
        # Default: stdio — useful for quick CLI testing
        mcp.run(transport="stdio")
