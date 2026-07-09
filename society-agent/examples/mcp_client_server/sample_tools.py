"""
examples/mcp_client_server/sample_tools.py
--------------------------------------------
Sample: Load tools from multiple MCP servers using MultiServerMCPClient
with stdio transport (uv run fastmcp run <file>).

SERVERS dict declares each MCP server — the client spawns them as
subprocesses automatically; no separate server process needed.

Usage (called from sample_graph.py):
    tools = await get_langchain_tools()
"""

from langchain_mcp_adapters.client import MultiServerMCPClient  # pip install langchain-mcp-adapters

from pathlib import Path

# Absolute path to sample_server.py — works regardless of cwd when running
_SERVER_FILE = str(Path(__file__).parent / "sample_server.py")

# ── MCP Server declarations ────────────────────────────────────────────────────
# Each entry tells MultiServerMCPClient how to launch that server.
# transport="stdio" → client spawns the file as a subprocess via uv.
# "command"/"args"  → equivalent to: uv run fastmcp run <file>
#
# IMPORTANT: point at sample_server.py (clean FastMCP-only file), NOT
# server/main.py — that file also creates a FastAPI app which binds port 8000
# and crashes when fastmcp tries to start it as a subprocess.

SERVERS = {
    "SocietyMaintenance": {
        "transport": "stdio",
        "command":   "uv",
        "args":      ["run", "fastmcp", "run", "--transport", "stdio", _SERVER_FILE],
    },
    # Add more servers here if needed, e.g.:
    # "ReportServer": {
    #     "transport": "stdio",
    #     "command":   "uv",
    #     "args":      ["run", "fastmcp", "run", "--transport", "stdio", str(Path(__file__).parent / "report_server.py")],
    # },
}


async def get_langchain_tools() -> list:
    """
    Launch all declared MCP servers as subprocesses and return a flat list
    of LangChain BaseTool objects — one per @mcp.tool() across all servers.

    Returns:
        List of LangChain BaseTool objects ready for llm.bind_tools() and ToolNode.
    """
    client = MultiServerMCPClient(SERVERS)
    tools = await client.get_tools()

    print(f"[MCP Client] Loaded {len(tools)} tools from {list(SERVERS.keys())}:")
    for t in tools:
        print(f"  • {t.name}: {t.description[:70]}...")

    return tools


# ── Quick sanity check ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import asyncio

    async def _main():
        tools = await get_langchain_tools()
        print(f"\nTotal tools loaded: {len(tools)}")

        # Call get_all_months to verify the round-trip works
        months_tool = next((t for t in tools if "month" in t.name.lower()), tools[0])
        print(f"\nCalling: {months_tool.name}")
        result = await months_tool.ainvoke({})
        print(f"Result:  {result}")

    asyncio.run(_main())
