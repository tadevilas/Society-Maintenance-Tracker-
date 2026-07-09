# MCP Client–Server Pattern — Sample Files

These files demonstrate how to connect a LangGraph agent to MCP servers
using **`MultiServerMCPClient` with stdio transport** — the same pattern
used in the Expense Tracker project.

> ⚠️ These are **sample / demo files only**.  
> They do **not** modify any existing project files.

---

## File Overview

```
examples/mcp_client_server/
├── sample_tools.py    ← SERVERS dict + MultiServerMCPClient → LangChain tools
├── sample_graph.py    ← Async LangGraph agent using those tools
└── README.md          ← This file
```

> `sample_server.py` is no longer needed — `MultiServerMCPClient` spawns
> the server as a subprocess automatically via `uv run fastmcp run`.

---

## The SERVERS Dict Pattern

Defined in [`sample_tools.py`](sample_tools.py):

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

SERVERS = {
    "SocietyMaintenance": {
        "transport": "stdio",
        "command":   "uv",
        "args":      ["run", "fastmcp", "run", "server/main.py"],
    },
    # Add more servers here:
    # "AnotherServer": {
    #     "transport": "stdio",
    #     "command":   "uv",
    #     "args":      ["run", "fastmcp", "run", "server/other.py"],
    # },
}
```

Each key is a logical server name. The client spawns each one as a subprocess
running `uv run fastmcp run <file>` — exactly like the Expense Tracker pattern:

```python
# Expense Tracker (reference)
SERVERS = {
    "ExpenseTracker":  {"transport": "stdio", "command": "uv", "args": ["run", "fastmcp", "run", "main.py"]},
    "SentimentServer": {"transport": "stdio", "command": "uv", "args": ["run", "fastmcp", "run", "sentence_analysis.py"]},
}
```

---

## How Tools Are Loaded

```python
client = MultiServerMCPClient(SERVERS)
tools  = await client.get_tools()   # flat list of LangChain BaseTool objects
```

`get_tools()` launches all servers, calls `list_tools()` on each, and returns
a **merged flat list** of LangChain `BaseTool` objects across all servers —
ready for `llm.bind_tools(tools)` and `ToolNode(tools)`.

---

## Extra Dependency

```bash
pip install langchain-mcp-adapters
```

---

## How to Run

```bash
# From inside society-agent/
python examples/mcp_client_server/sample_graph.py
```

No separate server process needed — `MultiServerMCPClient` handles launching.

---

## Architecture

```
sample_graph.py
│
│  await get_langchain_tools()
│
▼
sample_tools.py  ──  MultiServerMCPClient(SERVERS)
                              │
              ┌───────────────┘
              │  stdio subprocess
              ▼
        server/main.py  (@mcp.tool() functions)
              │
              ▼
        data_loader.py  (reads Excel files)
```

---

## Comparison with Previous SSE Approach

| | Old sample (SSE) | New sample (stdio) |
|---|---|---|
| **Transport** | HTTP/SSE | stdio subprocess |
| **Separate server needed?** | ✅ Yes — must start manually | ❌ No — spawned automatically |
| **Multi-server support** | ❌ One server at a time | ✅ SERVERS dict handles N servers |
| **Client code** | `sse_client` + `ClientSession` | `MultiServerMCPClient(SERVERS)` |
| **Remote clients possible?** | ✅ Yes (any MCP client) | ❌ Local subprocess only |
