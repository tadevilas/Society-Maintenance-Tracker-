"""
agent/tools.py
--------------
LangChain-compatible tool definitions for the Society Maintenance Agent.
These call the data layer directly (same process) — no HTTP round-trip needed.
"""

import sys
import contextlib
from pathlib import Path

# Ensure server module is on the path
sys.path.insert(0, str(Path(__file__).parent.parent / "server"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.tools import tool
from server.main import (
    tool_get_all_months,
    tool_get_pending_maintenance,
    tool_get_balance_sheet,
    tool_get_expense_summary,
    tool_get_flat_history,
    tool_get_collected_maintenance,
)
from reports.generator import generate_pending_excel, generate_balance_excel


# ── Tool definitions ───────────────────────────────────────────────────────────
# Each @tool wraps the MCP function so LangChain can bind it to the LLM.

@tool
def get_all_months() -> dict:
    """Return all available months in the society maintenance data."""
    return tool_get_all_months()


@tool
def get_pending_maintenance(month: str = "", year: int = 0) -> dict:
    """
    Get the list of flats that have NOT paid maintenance.
    Use month like 'Jan_2024' OR year like 2024 (not both).
    Vacant flats are automatically excluded.
    """
    return tool_get_pending_maintenance(month=month, year=year)


@tool
def get_balance_sheet(month: str = "", year: int = 0) -> dict:
    """
    Get the income vs expenses balance sheet for a given month or year.
    Use month like 'Jan_2024' OR year like 2024 (not both).
    Returns total_collected, total_expenses, net_balance and expense_breakdown.
    """
    return tool_get_balance_sheet(month=month, year=year)


@tool
def get_expense_summary(month: str = "", year: int = 0) -> dict:
    """
    Get expenses grouped by category (Cleaning, Electricity, Water Bill, etc.).
    Use month like 'Jan_2024' OR year like 2024 (not both).
    """
    return tool_get_expense_summary(month=month, year=year)


@tool
def get_flat_history(flat_number: int) -> dict:
    """
    Get the complete payment history for a specific flat.
    Example: flat_number=601 returns all months paid/unpaid for flat 601.
    """
    return tool_get_flat_history(flat_number=flat_number)


@tool
def get_collected_maintenance(month: str = "", year: int = 0) -> dict:
    """
    Get the list of flats that HAVE paid maintenance.
    Use month like 'Jan_2024' OR year like 2024 (not both).
    """
    return tool_get_collected_maintenance(month=month, year=year)


def _store_download(filename: str, file_bytes: bytes) -> None:
    """
    Persist generated file bytes into Streamlit's session_state.download_store
    so the sidebar download button picks them up on the next UI cycle.

    The import is deferred and silently skipped when the tools are called
    outside of a Streamlit context (e.g. unit tests or CLI usage).
    """
    with contextlib.suppress(Exception):
        import streamlit as st
        st.session_state.setdefault("download_store", {})[filename] = file_bytes


@tool
def download_pending_report(month: str = "", year: int = 0) -> dict:
    """
    Generate a downloadable Excel report of pending (unpaid) maintenance.
    Use month like 'Jan_2024' OR year like 2024 (not both).
    Returns a confirmation that the file is ready for download.
    """
    file_bytes = generate_pending_excel(
        month=month or None,
        year=int(year) if year else None,
    )
    period = month or str(year)
    filename = f"pending_maintenance_{period}.xlsx"
    _store_download(filename, file_bytes)
    return {
        "status":   "ready",
        "filename": filename,
        "size_kb":  round(len(file_bytes) / 1024, 1),
        "message":  f"Pending maintenance report for {period} is ready to download. "
                    "Use the ⬇️ button in the sidebar to save the file.",
    }


@tool
def download_balance_report(month: str = "", year: int = 0) -> dict:
    """
    Generate a downloadable Excel report of the balance sheet.
    Use month like 'Jan_2024' OR year like 2024 (not both).
    Returns a confirmation that the file is ready for download.
    """
    file_bytes = generate_balance_excel(
        month=month or None,
        year=int(year) if year else None,
    )
    period = month or str(year) if (month or year) else "all"
    filename = f"balance_sheet_{period}.xlsx"
    _store_download(filename, file_bytes)
    return {
        "status":   "ready",
        "filename": filename,
        "size_kb":  round(len(file_bytes) / 1024, 1),
        "message":  f"Balance sheet report for {period} is ready to download. "
                    "Use the ⬇️ button in the sidebar to save the file.",
    }


# ── Tool registry (used by the graph) ─────────────────────────────────────────
ALL_TOOLS = [
    get_all_months,
    get_pending_maintenance,
    get_balance_sheet,
    get_expense_summary,
    get_flat_history,
    get_collected_maintenance,
    download_pending_report,
    download_balance_report,
]
