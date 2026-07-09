import sys
sys.path.insert(0, "server")
sys.path.insert(0, ".")

from server.main import tool_get_balance_sheet, tool_get_pending_maintenance, tool_get_all_months

print("=== All months ===")
r = tool_get_all_months()
print(r["months"])

print("\n=== Balance sheet Jan_2024 ===")
b = tool_get_balance_sheet(month="Jan_2024")
print(f"Collected : Rs.{b['total_collected']:,.0f}")
print(f"Expenses  : Rs.{b['total_expenses']:,.0f}")
print(f"Balance   : Rs.{b['net_balance']:,.0f}")

print("\n=== Pending for Jan_2024 ===")
p = tool_get_pending_maintenance(month="Jan_2024")
print(f"Pending count: {p['count']}")
print(p["pending"])

print("\n=== MCP tools registered ===")
from server.main import mcp
tools = mcp._tool_manager.list_tools()
for t in tools:
    print(f"  {t.name} — {t.description[:60]}")
