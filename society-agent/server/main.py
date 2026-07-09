"""
server/main.py
--------------
FastAPI server that exposes society data as tool endpoints.
Also registers all tools as MCP-compatible tools via FastMCP.

Run with:
    uvicorn server.main:app --reload --port 8000
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse
from mcp.server.fastmcp import FastMCP
import io
import sys
from pathlib import Path

# Make sure data_loader is importable from this file's location
sys.path.insert(0, str(Path(__file__).parent))

from data_loader import (
    get_all_months,
    get_pending_maintenance,
    get_collected_maintenance,
    get_expense_summary,
    get_flat_history,
    get_balance_sheet,
)

# ── App setup ──────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Society Maintenance API",
    description="Backend API for Society Maintenance AI Agent",
    version="1.0.0",
)

mcp = FastMCP("Society Maintenance MCP Server")


# ── Helper ─────────────────────────────────────────────────────────────────────
def _df_to_records(df) -> list[dict]:
    """Convert DataFrame to JSON-serialisable list of dicts."""
    return df.where(df.notna(), None).to_dict(orient="records")


# ══════════════════════════════════════════════════════════════════════════════
#  REST endpoints  (used by Streamlit directly or for testing via Swagger UI)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/months", summary="List all available months")
def list_months():
    """Return sorted list of all months present in the data."""
    return {"months": get_all_months()}


@app.get("/pending", summary="Get pending maintenance list")
def pending_maintenance(
    month: str = Query(None, description="e.g. Jan_2024"),
    year:  int = Query(None, description="e.g. 2024"),
):
    """
    Return flats that have NOT paid maintenance for the given month or year.
    Vacant flats are excluded automatically.
    """
    if not month and not year:
        raise HTTPException(status_code=400, detail="Provide either 'month' or 'year'.")
    df = get_pending_maintenance(month=month, year=year)
    return {
        "period":  month or str(year),
        "count":   len(df),
        "pending": _df_to_records(df),
    }


@app.get("/collected", summary="Get collected maintenance list")
def collected_maintenance(
    month: str = Query(None, description="e.g. Jan_2024"),
    year:  int = Query(None, description="e.g. 2024"),
):
    """Return flats that HAVE paid for the given month or year."""
    if not month and not year:
        raise HTTPException(status_code=400, detail="Provide either 'month' or 'year'.")
    df = get_collected_maintenance(month=month, year=year)
    return {
        "period":    month or str(year),
        "count":     len(df),
        "collected": _df_to_records(df),
    }


@app.get("/expenses", summary="Get expense summary")
def expense_summary(
    month: str = Query(None, description="e.g. Jan_2024"),
    year:  int = Query(None, description="e.g. 2024"),
):
    """Return expenses grouped by type for the given month or year."""
    df = get_expense_summary(month=month, year=year)
    return {
        "period":   month or str(year) if (month or year) else "All Time",
        "expenses": _df_to_records(df),
    }


@app.get("/balance", summary="Get balance sheet")
def balance_sheet(
    month: str = Query(None, description="e.g. Jan_2024"),
    year:  int = Query(None, description="e.g. 2024"),
):
    """Return income vs expenses balance for the given month or year."""
    return get_balance_sheet(month=month, year=year)


@app.get("/flat/{flat_number}", summary="Get flat payment history")
def flat_history(flat_number: int):
    """Return full payment history for a specific flat number."""
    df = get_flat_history(flat_number)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"Flat {flat_number} not found.")
    return {
        "flat_number":  flat_number,
        "name":         df.iloc[0]["name"],
        "total_paid":   float(df["amount"].sum()),
        "months_count": len(df),
        "history":      _df_to_records(df),
    }


@app.get("/download/pending", summary="Download pending maintenance as Excel")
def download_pending(
    month: str = Query(None, description="e.g. Jan_2024"),
    year:  int = Query(None, description="e.g. 2024"),
):
    """Download pending maintenance list as an Excel file."""
    if not month and not year:
        raise HTTPException(status_code=400, detail="Provide either 'month' or 'year'.")

    # Import here to avoid circular dependency
    from reports.generator import generate_pending_excel
    period = month or str(year)
    file_bytes = generate_pending_excel(month=month, year=year)
    filename = f"pending_maintenance_{period}.xlsx"
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/download/balance", summary="Download balance sheet as Excel")
def download_balance(
    month: str = Query(None, description="e.g. Jan_2024"),
    year:  int = Query(None, description="e.g. 2024"),
):
    """Download balance sheet as an Excel file."""
    from reports.generator import generate_balance_excel
    period = month or str(year) if (month or year) else "all"
    file_bytes = generate_balance_excel(month=month, year=year)
    filename = f"balance_sheet_{period}.xlsx"
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ══════════════════════════════════════════════════════════════════════════════
#  MCP Tools  (used by LangGraph agent)
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def tool_get_all_months() -> dict:
    """Return all available months in the society data."""
    return {"months": get_all_months()}


@mcp.tool()
def tool_get_pending_maintenance(month: str = "", year: int = 0) -> dict:
    """
    Get the list of flats that have NOT paid maintenance.
    Pass month like 'Jan_2024' OR year like 2024. Vacant flats are excluded.
    When year is given, results are grouped by flat with months_count and
    total_due (months_count × Rs. 1,000).
    """
    df = get_pending_maintenance(
        month=month or None,
        year=year or None,
    )
    result = {
        "period":   month or str(year),
        "count":    len(df),
        "pending":  _df_to_records(df),
    }
    # For year queries add a pre-computed grand total so the LLM doesn't have to sum
    if year and not month and "total_due" in df.columns:
        result["grand_total_due"] = int(df["total_due"].sum())
    return result


@mcp.tool()
def tool_get_balance_sheet(month: str = "", year: int = 0) -> dict:
    """
    Get income vs expenses balance sheet.
    Pass month like 'Jan_2024' OR year like 2024.
    Returns total_collected, total_expenses, net_balance, expense_breakdown.
    """
    return get_balance_sheet(
        month=month or None,
        year=year or None,
    )


@mcp.tool()
def tool_get_expense_summary(month: str = "", year: int = 0) -> dict:
    """
    Get expenses grouped by type (Cleaning, Electricity, Water Bill, etc.).
    Pass month like 'Jan_2024' OR year like 2024.
    """
    df = get_expense_summary(month=month or None, year=year or None)
    return {"expenses": _df_to_records(df)}


@mcp.tool()
def tool_get_flat_history(flat_number: int) -> dict:
    """
    Get the full payment history for a specific flat number.
    Example: flat_number=601
    """
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
    """
    Get the list of flats that HAVE paid maintenance.
    Pass month like 'Jan_2024' OR year like 2024.
    """
    df = get_collected_maintenance(month=month or None, year=year or None)
    return {
        "period":    month or str(year),
        "count":     len(df),
        "collected": _df_to_records(df),
    }
