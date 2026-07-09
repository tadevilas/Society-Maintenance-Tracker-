"""
examples/mcp_client_server/sample_graph.py
--------------------------------------------
Sample: Async LangGraph agent that loads tools via MultiServerMCPClient
(stdio transport) — no separate server process needed.

MultiServerMCPClient spawns each MCP server as a subprocess automatically
using the SERVERS config declared in sample_tools.py.

Pre-requisites:
    pip install langchain-mcp-adapters
    uv must be installed and available in PATH

Run this demo:
    cd society-agent
    python examples/mcp_client_server/sample_graph.py
"""

import os
import sys
import sqlite3
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# ── Path setup ─────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from typing import Annotated
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.sqlite import SqliteSaver
from typing_extensions import TypedDict

from agent.prompts import SYSTEM_PROMPT
from examples.mcp_client_server.sample_tools import get_langchain_tools


# ── Agent State ────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# ── Build async graph ──────────────────────────────────────────────────────────

async def build_async_graph():
    """
    Build the LangGraph agent.
    Tools are loaded from MCP servers via MultiServerMCPClient (stdio).
    """
    # 1. Fetch tools — MultiServerMCPClient spawns servers as subprocesses
    tools = await get_langchain_tools()

    # 2. Build LLM and bind tools
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key or api_key == "your_groq_api_key_here":
        raise ValueError("GROQ_API_KEY is not set in .env")

    llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0, api_key=api_key)
    llm_with_tools = llm.bind_tools(tools)

    # 3. LLM node (async)
    async def llm_node(state: AgentState) -> AgentState:
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    # 4. Wire the graph
    tool_node = ToolNode(tools)

    graph = StateGraph(AgentState)
    graph.add_node("chat",  llm_node)
    graph.add_node("tools", tool_node)

    graph.add_edge(START, "chat")
    graph.add_conditional_edges("chat", tools_condition)
    graph.add_edge("tools", "chat")
    graph.add_edge("chat", END)

    # 5. SQLite checkpointer (separate DB to avoid conflicts with agent/memory.db)
    db_path = Path(__file__).parent / "sample_memory.db"
    conn = sqlite3.connect(str(db_path), check_same_thread=False)

    return graph.compile(checkpointer=SqliteSaver(conn))


# ── Public async interface ─────────────────────────────────────────────────────

async def chat(message: str, thread_id: str = "demo") -> str:
    """Send a message and get the agent's full text response."""
    graph = await build_async_graph()
    config = {"configurable": {"thread_id": thread_id}}
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content=message)]},
        config=config,
    )
    return result["messages"][-1].content


async def stream_chat(message: str, thread_id: str = "demo"):
    """
    Async generator — yields LLM text chunks as they arrive.
    Usage:
        async for chunk in stream_chat("Which flats are pending?"):
            print(chunk, end="", flush=True)
    """
    graph = await build_async_graph()
    config = {"configurable": {"thread_id": thread_id}}

    async for chunk, metadata in graph.astream(
        {"messages": [HumanMessage(content=message)]},
        config=config,
        stream_mode="messages",
    ):
        if metadata.get("langgraph_node") != "chat":
            continue
        if getattr(chunk, "tool_calls", None):
            continue
        if chunk.__class__.__name__ == "ToolMessage":
            continue
        if hasattr(chunk, "content") and chunk.content:
            yield chunk.content


# ── Demo entry point ───────────────────────────────────────────────────────────

async def _demo():
    print("=" * 60)
    print("MCP Client-Server Agent Demo  (stdio transport)")
    print("=" * 60)

    question = "What months of data do we have?"
    print(f"Question: {question}")
    print("Answer:   ", end="", flush=True)

    async for chunk in stream_chat(question, thread_id="demo-001"):
        print(chunk, end="", flush=True)

    print("\n")


if __name__ == "__main__":
    asyncio.run(_demo())
