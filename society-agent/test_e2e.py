"""
test_e2e.py
-----------
Phase 6 — Full end-to-end integration test.
Tests every layer: data → tools → agent → reports.

Run: python test_e2e.py   (from inside society-agent/)
"""

import sys, os, re
sys.path.insert(0, ".")

SEP  = "=" * 58
PASS = "[PASS]"
FAIL = "[FAIL]"
results = []

def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((status, label))
    icon = "OK" if condition else "!!"
    suffix = f"  ({detail})" if detail else ""
    print(f"  {icon}  {label}{suffix}")
    return condition

def section(title):
    print(f"\n{SEP}\n  {title}\n{SEP}")

# ════════════════════════════════════════════════════════════
#  1. DATA LAYER
# ════════════════════════════════════════════════════════════
section("1. Data Layer (data_loader.py)")

from server.data_loader import (
    load_maintenance, load_expenses,
    get_all_months, get_pending_maintenance,
    get_collected_maintenance, get_expense_summary,
    get_balance_sheet, get_flat_history,
)

maint = load_maintenance()
exp   = load_expenses()
check("Maintenance rows > 2000",  len(maint) > 2000, f"{len(maint)} rows")
check("Expenses rows > 200",      len(exp)   > 200,   f"{len(exp)} rows")
check("Maintenance has 9 cols",   len(maint.columns) == 9)
check("Expenses has 7 cols",      len(exp.columns)   == 7)

months = get_all_months()
check("24 months available",      len(months) == 24, f"{len(months)} found")
check("Jan_2024 in months",       "Jan_2024"  in months)
check("Dec_2025 in months",       "Dec_2025"  in months)
check("Months sorted correctly",  months[0] == "Jan_2024" and months[-1] == "Dec_2025")

pending = get_pending_maintenance(month="March_2025")
check("Pending query returns df", hasattr(pending, "columns"))
check("Pending excludes vacant",  "NA" not in pending["name"].values)

bs = get_balance_sheet(month="Jan_2024")
check("Balance sheet has keys",   all(k in bs for k in
      ["total_collected", "total_expenses", "net_balance", "expense_breakdown"]))
check("Jan_2024 collected=76000", bs["total_collected"] == 76000.0,
      f"got {bs['total_collected']}")

history = get_flat_history(601)
check("Flat 601 has 24 months",   len(history) == 24, f"{len(history)} rows")
check("Flat 601 total >= 23000",  history["amount"].sum() >= 23000)

# ════════════════════════════════════════════════════════════
#  2. TOOLS LAYER
# ════════════════════════════════════════════════════════════
section("2. Tools Layer (server/main.py MCP tools)")

from server.main import (
    tool_get_all_months, tool_get_pending_maintenance,
    tool_get_balance_sheet, tool_get_expense_summary,
    tool_get_flat_history, tool_get_collected_maintenance,
    mcp,
)

r = tool_get_all_months()
check("tool_get_all_months returns dict",    "months" in r)
check("tool_get_all_months has 24 months",   len(r["months"]) == 24)

r = tool_get_pending_maintenance(month="Jan_2024")
check("tool_get_pending has count key",      "count" in r)
check("tool_get_pending has pending key",    "pending" in r)

r = tool_get_balance_sheet(month="Jan_2024")
check("tool_get_balance_sheet net correct",  r["net_balance"] == 19374.0,
      f"got {r.get('net_balance')}")

r = tool_get_expense_summary(year=2024)
check("tool_get_expense_summary not empty",  len(r["expenses"]) > 0)

r = tool_get_flat_history(flat_number=101)
check("tool_get_flat_history returns data",  "history" in r)

tools_list = mcp._tool_manager.list_tools()
check("6 MCP tools registered",              len(tools_list) == 6,
      f"{len(tools_list)} found")

# ════════════════════════════════════════════════════════════
#  3. REPORT GENERATION
# ════════════════════════════════════════════════════════════
section("3. Report Generation (reports/generator.py)")

from reports.generator import generate_pending_excel, generate_balance_excel

b = generate_pending_excel(month="Jan_2024")
check("Pending Excel (month) > 5KB",   len(b) > 5000, f"{len(b):,} bytes")

b = generate_pending_excel(year=2024)
check("Pending Excel (year) > 20KB",   len(b) > 20000, f"{len(b):,} bytes")

b = generate_balance_excel(month="Jan_2024")
check("Balance Excel (month) > 4KB",   len(b) > 4000, f"{len(b):,} bytes")

b = generate_balance_excel(year=2024)
check("Balance Excel (year) > 4KB",    len(b) > 4000, f"{len(b):,} bytes")

# ════════════════════════════════════════════════════════════
#  4. AGENT LAYER  (requires GROQ_API_KEY)
# ════════════════════════════════════════════════════════════
section("4. Agent Layer (LangGraph + Groq)")

from agent.graph import get_graph, chat

graph = get_graph()
check("Graph builds successfully",     graph is not None)
check("Graph has llm_node",            "llm_node"  in graph.get_graph().nodes)
check("Graph has tool_node",           "tool_node" in graph.get_graph().nodes)

# Only run LLM tests if API key is set
api_key = os.getenv("GROQ_API_KEY", "")
if not api_key or api_key == "your_groq_api_key_here":
    print("  --  Skipping LLM tests (GROQ_API_KEY not set)")
else:
    def _clean(text):
        return re.sub(r'[^\x00-\x7F]+', '', text)  # strip emoji for Windows terminal

    r1 = chat("What months of data do we have?", thread_id="e2e-1")
    check("Agent answers month query",     "2024" in r1 and "2025" in r1, _clean(r1[:60]))

    r2 = chat("Balance sheet for January 2024", thread_id="e2e-2")
    check("Agent returns balance numbers", "76,000" in r2 or "76000" in r2, _clean(r2[:80]))

    r3 = chat("How many flats pending for March 2025?", thread_id="e2e-3")
    check("Agent answers pending query",   any(c.isdigit() for c in r3), _clean(r3[:80]))

    r4 = chat("What was the electricity expense in 2024?", thread_id="e2e-4")
    check("Agent answers expense query",   any(x in r4 for x in
          ["329", "3,29", "330", "32,9", "32963"]), _clean(r4[:80]))

    # Memory test — follow-up without restating context
    chat("Show me the balance sheet for January 2024", thread_id="e2e-mem")
    r5 = chat("What about for the whole year?", thread_id="e2e-mem")
    check("Agent memory works (follow-up)", "2024" in r5 and any(
          x in r5 for x in ["868", "8,68", "186"]), _clean(r5[:80]))

# ════════════════════════════════════════════════════════════
#  5. FINAL SUMMARY
# ════════════════════════════════════════════════════════════
print(f"\n{SEP}")
passed = sum(1 for s, _ in results if s == PASS)
failed = sum(1 for s, _ in results if s == FAIL)
total  = len(results)
print(f"  RESULTS:  {passed}/{total} passed   |   {failed} failed")
print(SEP)

if failed > 0:
    print("\n  Failed tests:")
    for status, label in results:
        if status == FAIL:
            print(f"    {label}")

print()
