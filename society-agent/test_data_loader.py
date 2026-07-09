"""
test_data_loader.py
-------------------
Run this to verify the data layer is working correctly.
Usage:  python test_data_loader.py   (from inside society-agent/)
"""

import sys
sys.path.insert(0, "server")

from data_loader import (
    get_all_months,
    get_pending_maintenance,
    get_expense_summary,
    get_flat_history,
    get_balance_sheet,
    load_maintenance,
    load_expenses,
)

SEP = "-" * 55

def section(title):
    print(f"\n{SEP}\n  {title}\n{SEP}")

# ── 1. Raw load ────────────────────────────────────────────────
section("1. Raw data shape")
maint = load_maintenance()
exp   = load_expenses()
print(f"Maintenance rows : {len(maint)}")
print(f"Expenses rows    : {len(exp)}")
print(f"Maintenance cols : {list(maint.columns)}")
print(f"Expenses cols    : {list(exp.columns)}")

# ── 2. All months ──────────────────────────────────────────────
section("2. All months (sorted)")
months = get_all_months()
print(months)

# ── 3. Pending maintenance — specific month ────────────────────
section("3. Pending maintenance for Jan_2024")
pending = get_pending_maintenance(month="Jan_2024")
print(f"Pending count: {len(pending)}")
print(pending.head(10).to_string(index=False))

# ── 4. Expense summary — specific month ───────────────────────
section("4. Expense summary for Jan_2024")
expenses = get_expense_summary(month="Jan_2024")
print(expenses.to_string(index=False))

# ── 5. Balance sheet — month ───────────────────────────────────
section("5. Balance sheet for Jan_2024")
bs = get_balance_sheet(month="Jan_2024")
print(f"Period           : {bs['period']}")
print(f"Total Collected  : Rs.{bs['total_collected']:,.0f}")
print(f"Total Expenses   : Rs.{bs['total_expenses']:,.0f}")
print(f"Net Balance      : Rs.{bs['net_balance']:,.0f}")
print("Expense Breakdown:")
for item in bs["expense_breakdown"]:
    print(f"  {item['expense_type']:<25} Rs.{item['total']:,.0f}")

# ── 6. Balance sheet — full year ───────────────────────────────
section("6. Balance sheet for 2024")
bs2024 = get_balance_sheet(year=2024)
print(f"Period           : {bs2024['period']}")
print(f"Total Collected  : Rs.{bs2024['total_collected']:,.0f}")
print(f"Total Expenses   : Rs.{bs2024['total_expenses']:,.0f}")
print(f"Net Balance      : Rs.{bs2024['net_balance']:,.0f}")

# ── 7. Flat history ────────────────────────────────────────────
section("7. Payment history for flat 601 (Vilas Tade)")
history = get_flat_history(601)
print(f"Total months recorded: {len(history)}")
print(f"Total paid          : Rs.{history['amount'].sum():,.0f}")
print(history[["month", "date", "amount", "is_paid"]].to_string(index=False))

print(f"\n{SEP}\n  All tests passed!\n{SEP}\n")
