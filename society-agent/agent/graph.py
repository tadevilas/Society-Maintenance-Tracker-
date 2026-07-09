"""
agent/graph.py
--------------
LangGraph StateGraph for the Society Maintenance AI Agent.

Flow:
    START → llm_node → (tool_node → llm_node)* → END

The agent loops between the LLM and tool calls until the LLM
decides it has enough information to give a final answer.
"""

import os
import sys
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

# Load .env for GROQ_API_KEY
load_dotenv(Path(__file__).parent.parent / ".env")

# Ensure packages are importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Annotated
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.sqlite import SqliteSaver
from typing_extensions import TypedDict

from agent.prompts import SYSTEM_PROMPT
from agent.tools import ALL_TOOLS


# ── Agent State ────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    """
    State passed between graph nodes.
    `messages` uses add_messages reducer — new messages are appended,
    never overwritten, giving us full conversation history automatically.
    """
    messages: Annotated[list, add_messages]


# ── LLM setup — built once at import time ─────────────────────────────────────

def _build_llm():
    """
    Instantiate the Groq LLM with tools bound.
    Called once at module level; the result is reused for every graph step.
    """
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key or api_key == "your_groq_api_key_here":
        raise ValueError(
            "GROQ_API_KEY is not set. "
            "Add it to society-agent/.env as: GROQ_API_KEY=gsk_..."
        )
    llm = ChatGroq(
        model="openai/gpt-oss-120b",
        temperature=0,
        api_key=api_key,
    )
    return llm.bind_tools(ALL_TOOLS)

# Singleton — created once when this module is first imported.
_llm_with_tools = _build_llm()


# ── Graph nodes ────────────────────────────────────────────────────────────────

def llm_node(state: AgentState) -> AgentState:
    """
    Call the LLM with the current message history.
    Prepends the system prompt on every call so the LLM always has context.
    """
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = _llm_with_tools.invoke(messages)
    return {"messages": [response]}


# ── SQLite checkpointer ────────────────────────────────────────────────────────

# DB file lives next to this file: agent/memory.db
# It is created automatically on first run.
_DB_PATH = Path(__file__).parent / "memory.db"


def _make_checkpointer() -> SqliteSaver:
    """
    Open (or create) the SQLite database and return a SqliteSaver checkpointer.
    Uses check_same_thread=False so the connection is safe to share across
    Streamlit's threading model.
    """
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    return SqliteSaver(conn)


# ── Build the graph ────────────────────────────────────────────────────────────

def build_graph():
    """
    Build and compile the LangGraph agent.
    Returns a compiled graph with SQLite-backed conversation checkpointing.
    Conversation history survives server restarts; each thread_id is its
    own isolated session stored as rows in agent/memory.db.
    """
    tool_node = ToolNode(tools=ALL_TOOLS)

    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("llm_node",  llm_node)
    graph.add_node("tool_node", tool_node)

    # Add edges
    graph.add_edge(START, "llm_node")

    # After LLM: if it called a tool → go to tool_node, else → END
    graph.add_conditional_edges(
        "llm_node",
        tools_condition,           # built-in: checks if AIMessage has tool_calls
        {
            "tools": "tool_node",  # has tool calls → execute them
            END:     END,          # no tool calls  → final answer, stop
        },
    )

    # After tool execution → always go back to LLM to process the result
    graph.add_edge("tool_node", "llm_node")

    # Compile with SQLite checkpointer — durable, bounded, restart-safe
    return graph.compile(checkpointer=_make_checkpointer())


# ── Public interface ───────────────────────────────────────────────────────────

# Singleton — compiled once, reused by Streamlit across reruns
_graph = None

def get_graph():
    """Return the singleton compiled graph."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def chat(message: str, thread_id: str = "default") -> str:
    """
    Send a message to the agent and get a response string.

    Args:
        message:   The user's message text.
        thread_id: Conversation ID — same ID = same memory thread.
                   Use different IDs for different users/sessions.

    Returns:
        The agent's final text response.
    """
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(
        {"messages": [HumanMessage(content=message)]},
        config=config,
    )
    # The last message in state is the final AI response
    return result["messages"][-1].content


def stream_chat(message: str, thread_id: str = "default"):
    """
    Stream the agent's response token by token.
    Yields text chunks as they arrive from the LLM.
    Used by Streamlit for a live typing effect.

    Only yields chunks from the final AIMessage (not tool call messages
    or tool result messages which contain raw JSON).
    """
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}

    for chunk, metadata in graph.stream(
        {"messages": [HumanMessage(content=message)]},
        config=config,
        stream_mode="messages",
    ):
        # Only stream tokens from the LLM node (not tool_node results)
        if metadata.get("langgraph_node") != "llm_node":
            continue
        # Skip tool-call request messages (AIMessage with tool_calls)
        if getattr(chunk, "tool_calls", None):
            continue
        # Skip ToolMessage (raw JSON tool results)
        if chunk.__class__.__name__ == "ToolMessage":
            continue
        # Only yield actual text content from AIMessage
        if hasattr(chunk, "content") and chunk.content:
            yield chunk.content
