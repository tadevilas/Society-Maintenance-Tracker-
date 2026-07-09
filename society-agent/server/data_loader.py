"""
data_loader.py
--------------
Loads and normalises data from Maintenance.xlsx and Expenses.xlsx.
All other modules import from here — never read Excel files directly elsewhere.
"""

import re
import functools
import pandas as pd
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent.parent / "data"
MAINTENANCE_FILE = DATA_DIR / "Maintenance.xlsx"
EXPENSES_FILE    = DATA_DIR / "Expenses.xlsx"

# ── Month normalisation ────────────────────────────────────────────────────────
# Canonical month prefixes used in the actual Excel data (verified from source):
#   Jan Feb March April May June July Aug Sep Oct Nov Dec
# The LLM (and users) may supply any case or spelling variant, e.g.:
#   "january_2024", "MARCH_2025", "jun_2024", "September_2024"
# This map resolves every common English variant → the canonical prefix.

_CANONICAL_PREFIX: dict[str, str] = {
    "jan":       "Jan",
    "january":   "Jan",
    "feb":       "Feb",
    "february":  "Feb",
    "mar":       "March",
    "march":     "March",
    "apr":       "April",
    "april":     "April",
    "may":       "May",
    "jun":       "June",
    "june":      "June",
    "jul":       "July",
    "july":      "July",
    "aug":       "Aug",
    "august":    "Aug",
    "sep":       "Sep",
    "sept":      "Sep",
    "september": "Sep",
    "oct":       "Oct",
    "october":   "Oct",
    "nov":       "Nov",
    "november":  "Nov",
    "dec":       "Dec",
    "december":  "Dec",
}

# Matches "Word_YYYY" or "Word YYYY" (case-insensitive)
_MONTH_RE = re.compile(r"^([A-Za-z]+)[_\s](\d{4})$")


def _normalise_month(value: str | None) -> str | None:
    """
    Normalise any month string to the canonical form used in the data.

    Examples
    --------
    "january_2024"  → "Jan_2024"
    "MARCH_2025"    → "March_2025"
    "jun_2024"      → "June_2024"
    "July 2025"     → "July_2025"
    "september_2024"→ "Sep_2024"
    Unknown prefix  → returned unchanged (avoids silent data loss)
    """
    if not value or not isinstance(value, str):
        return value
    value = value.strip()
    m = _MONTH_RE.match(value)
    if not m:
        return value
    prefix_raw, year = m.group(1), m.group(2)
    canonical = _CANONICAL_PREFIX.get(prefix_raw.lower())
    if canonical is None:
        return value          # unrecognised prefix — pass through unchanged
    return f"{canonical}_{year}"


# ── Loaders ────────────────────────────────────────────────────────────────────

@functools.cache
def load_maintenance() -> pd.DataFrame:
    """
    Load Maintenance.xlsx and return a clean DataFrame.

    Columns returned:
        month        – str  e.g. 'Jan_2024'
        date         – datetime (payment date, NaT if not paid)
        flat_number  – int
        name         – str  ('NA' for vacant flats)
        amount       – float (0.0 if not paid)
        late_charges – float (0.0 if none)
        is_vacant    – bool  (True when name == 'NA')
        is_paid      – bool  (True when amount > 0)
        year         – int   e.g. 2024
    """
    df = pd.read_excel(MAINTENANCE_FILE, sheet_name="Maintenance")

    # Rename columns to clean snake_case
    df.columns = ["month", "date", "flat_number", "name", "amount", "late_charges"]

    # Normalise month strings
    df["month"] = df["month"].apply(_normalise_month)

    # Coerce types
    df["flat_number"]  = pd.to_numeric(df["flat_number"], errors="coerce").astype("Int64")
    df["amount"]       = pd.to_numeric(df["amount"],       errors="coerce").fillna(0.0)
    df["late_charges"] = pd.to_numeric(df["late_charges"], errors="coerce").fillna(0.0)
    df["date"]         = pd.to_datetime(df["date"], errors="coerce")
    df["name"]         = df["name"].fillna("NA").astype(str).str.strip()

    # Derived columns
    df["is_vacant"] = df["name"].str.upper() == "NA"
    df["is_paid"]   = df["amount"] > 0

    # Extract year from month string e.g. 'Jan_2024' → 2024
    df["year"] = df["month"].str.extract(r"_(\d{4})$").astype("Int64")

    # Drop completely empty rows
    df.dropna(subset=["month", "flat_number"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df


@functools.cache
def load_expenses() -> pd.DataFrame:
    """
    Load Expenses.xlsx and return a clean DataFrame.

    Columns returned:
        month        – str  e.g. 'Jan_2024'
        date         – datetime
        expense_type – str  (empty string if blank)
        details      – str
        amount       – float
        spend_by     – str
        year         – int  e.g. 2024
    """
    df = pd.read_excel(EXPENSES_FILE, sheet_name="Expenses")

    # Drop unnamed/empty trailing columns (phantom columns from Excel formatting)
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

    # The column is misspelled "Expence Type" in the Excel file — handle it
    df.columns = ["month", "date", "expense_type", "details", "amount", "spend_by"]

    # Normalise month strings
    df["month"] = df["month"].apply(_normalise_month)

    # Coerce types
    df["amount"]       = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["date"]         = pd.to_datetime(df["date"], errors="coerce")
    df["expense_type"] = df["expense_type"].fillna("Other").astype(str).str.strip()
    df["details"]      = df["details"].fillna("").astype(str).str.strip()
    df["spend_by"]     = df["spend_by"].fillna("").astype(str).str.strip()

    # Extract year
    df["year"] = df["month"].str.extract(r"_(\d{4})$").astype("Int64")

    # Drop completely empty rows
    df.dropna(subset=["month"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df


def invalidate_cache() -> None:
    """
    Clear the in-memory DataFrame cache.
    Call this if the source Excel files are updated on disk during the
    same process lifetime (e.g. in tests or after a hot-reload trigger).
    """
    load_maintenance.cache_clear()
    load_expenses.cache_clear()


# ── Query helpers ──────────────────────────────────────────────────────────────

def get_all_months() -> list[str]:
    """Return sorted list of all unique months present in Maintenance data."""
    df = load_maintenance()
    months = df["month"].dropna().unique().tolist()
    # Sort by year then month order
    month_order = ["Jan", "Feb", "March", "April", "May", "June",
                   "July", "Aug", "Sep", "Oct", "Nov", "Dec"]
    def sort_key(m):
        parts = m.split("_")
        mon = parts[0] if len(parts) == 2 else m
        yr  = parts[1] if len(parts) == 2 else "0"
        idx = next((i for i, x in enumerate(month_order) if x.lower() == mon.lower()), 99)
        return (yr, idx)
    return sorted(months, key=sort_key)


MAINTENANCE_RATE = 1_000  # Rs. per flat per month


def get_pending_maintenance(month: str = None, year: int = None) -> pd.DataFrame:
    """
    Return flats that have NOT paid for the given month or year.
    Vacant flats (name == 'NA') are excluded.

    When filtering by **month** the result is flat-per-row:
        month, flat_number, name, amount_due, late_charges

    When filtering by **year** the result is grouped by flat:
        flat_number, name, months_pending (list joined as comma string),
        months_count, total_due
    The total_due is months_count × MAINTENANCE_RATE so it is always a
    clean multiple of 1,000 regardless of what the raw data records.
    """
    df = load_maintenance()
    df = df[~df["is_vacant"]]  # exclude vacant flats

    if month:
        month = _normalise_month(month)
        df = df[df["month"].str.lower() == month.lower()]
        pending = df[~df["is_paid"]][["month", "flat_number", "name", "amount", "late_charges"]]
        pending = pending.rename(columns={"amount": "amount_due"})
        return pending.reset_index(drop=True)

    elif year:
        df = df[df["year"] == int(year)]
        unpaid = df[~df["is_paid"]]

        grouped = (
            unpaid.groupby(["flat_number", "name"], as_index=False)
            .agg(months_pending=("month", lambda s: ", ".join(s.tolist())),
                 months_count=("month", "count"))
        )
        grouped["total_due"] = grouped["months_count"] * MAINTENANCE_RATE
        grouped = grouped.sort_values("flat_number").reset_index(drop=True)
        return grouped

    else:
        # No filter — return all unpaid rows flat-per-row
        pending = df[~df["is_paid"]][["month", "flat_number", "name", "amount", "late_charges"]]
        pending = pending.rename(columns={"amount": "amount_due"})
        return pending.reset_index(drop=True)


def get_collected_maintenance(month: str = None, year: int = None) -> pd.DataFrame:
    """Return flats that HAVE paid for the given month or year."""
    df = load_maintenance()
    df = df[~df["is_vacant"]]

    if month:
        month = _normalise_month(month)
        df = df[df["month"].str.lower() == month.lower()]
    elif year:
        df = df[df["year"] == int(year)]

    paid = df[df["is_paid"]][["month", "flat_number", "name", "amount", "late_charges", "date"]]
    return paid.reset_index(drop=True)


def get_expense_summary(month: str = None, year: int = None) -> pd.DataFrame:
    """
    Return expenses grouped by expense_type for the given month or year.
    Returns DataFrame with columns: expense_type, total_amount, transaction_count
    """
    df = load_expenses()

    if month:
        month = _normalise_month(month)
        df = df[df["month"].str.lower() == month.lower()]
    elif year:
        df = df[df["year"] == int(year)]

    summary = (
        df.groupby("expense_type")
          .agg(total_amount=("amount", "sum"), transaction_count=("amount", "count"))
          .reset_index()
          .sort_values("total_amount", ascending=False)
    )
    return summary


def get_flat_history(flat_number: int) -> pd.DataFrame:
    """Return full payment history for a specific flat, sorted in calendar order."""
    _month_order = ["Jan", "Feb", "March", "April", "May", "June",
                    "July", "Aug", "Sep", "Oct", "Nov", "Dec"]

    def _month_sort_key(m: str) -> tuple:
        parts = m.split("_")
        prefix = parts[0] if len(parts) == 2 else m
        yr     = parts[1] if len(parts) == 2 else "0"
        idx = next((i for i, x in enumerate(_month_order)
                    if x.lower() == prefix.lower()), 99)
        return (yr, idx)

    df = load_maintenance()
    history = df[df["flat_number"] == int(flat_number)][
        ["month", "year", "date", "name", "amount", "late_charges", "is_paid"]
    ].copy()
    history["_sort_key"] = history["month"].map(_month_sort_key)
    history = history.sort_values("_sort_key").drop(columns="_sort_key")
    return history.reset_index(drop=True)


def get_balance_sheet(month: str = None, year: int = None) -> dict:
    """
    Compute income vs expenses balance for a given month or year.

    Returns a dict with:
        period, total_collected, total_expenses,
        net_balance, expense_breakdown (list of dicts)
    """
    maint_df  = load_maintenance()
    expense_df = load_expenses()

    if month:
        month = _normalise_month(month)
        maint_df   = maint_df[maint_df["month"].str.lower()   == month.lower()]
        expense_df = expense_df[expense_df["month"].str.lower() == month.lower()]
        period = month
    elif year:
        maint_df   = maint_df[maint_df["year"]   == int(year)]
        expense_df = expense_df[expense_df["year"] == int(year)]
        period = str(year)
    else:
        period = "All Time"

    total_collected = float(maint_df["amount"].sum() + maint_df["late_charges"].sum())
    total_expenses  = float(expense_df["amount"].sum())
    net_balance     = total_collected - total_expenses

    expense_breakdown = (
        expense_df.groupby("expense_type")["amount"]
        .sum()
        .reset_index()
        .rename(columns={"amount": "total"})
        .sort_values("total", ascending=False)
        .to_dict(orient="records")
    )

    return {
        "period":            period,
        "total_collected":   total_collected,
        "total_expenses":    total_expenses,
        "net_balance":       net_balance,
        "expense_breakdown": expense_breakdown,
    }
