# 🏠 Society Maintenance AI Agent

An agentic AI system for housing society management — built with LangGraph, Groq LLM, FastAPI (MCP), and Streamlit.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Data](#data)
- [Setup & Installation](#setup--installation)
- [Running the App](#running-the-app)
- [How It Works](#how-it-works)
- [Available Tools](#available-tools)
- [Example Queries](#example-queries)
- [Test Results](#test-results)
- [Known Limitations](#known-limitations)

---

## Overview

The Society Maintenance AI Agent is a conversational assistant that lets housing society committee members:

- Chat naturally to query maintenance payment records and expenses
- Get pending maintenance lists by month or year
- View balance sheets with income vs expense breakdowns
- Download styled Excel reports on demand
- Look up payment history for any individual flat

Data is sourced from two Excel files (`Maintenance.xlsx`, `Expenses.xlsx`) covering **January 2024 – December 2025** across **88 occupied flats**.

---

## Features

| Feature | Description |
|---|---|
| 💬 **Natural language chat** | Ask questions in plain English — the agent understands context and memory |
| 📊 **Pending maintenance** | See which flats haven't paid for any month or year |
| 💰 **Balance sheet** | Income vs expenses with category-wise breakdown |
| 📥 **Excel downloads** | Styled, printable reports for pending list and balance sheet |
| 🧠 **Conversation memory** | Multi-turn chat — follow-up questions work without repeating context |
| ⚡ **Quick prompts** | One-click preset questions in the sidebar |
| 🔄 **New conversation** | Reset chat and start fresh anytime |

---

## Architecture

```
User (Browser)
     │
     ▼
┌─────────────────────────────────┐
│         Streamlit UI            │  ← Chat input, sidebar filters,
│         ui/app.py               │    download buttons
└────────────┬────────────────────┘
             │  calls
             ▼
┌─────────────────────────────────┐
│      LangGraph Agent            │  ← Stateful ReAct loop
│      agent/graph.py             │    START → llm_node ⇄ tool_node → END
│                                 │
│  ┌──────────┐  ┌─────────────┐  │
│  │ llm_node │  │  tool_node  │  │
│  │  Groq    │  │  (executes  │  │
│  │  LLM     │  │   tools)    │  │
│  └──────────┘  └─────────────┘  │
│         MemorySaver (memory)    │
└────────────┬────────────────────┘
             │  calls
             ▼
┌─────────────────────────────────┐
│    FastAPI + MCP Tool Server    │  ← 6 MCP tools + 8 REST endpoints
│    server/main.py               │    Swagger UI at /docs
└────────────┬────────────────────┘
             │  reads
             ▼
┌─────────────────────────────────┐
│       Data Layer                │  ← Pandas reads Excel files
│       server/data_loader.py     │    Normalises, filters, aggregates
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  data/Maintenance.xlsx          │  ← 2,848 rows, 88 flats, 24 months
│  data/Expenses.xlsx             │  ← 977 rows, 10 expense categories
└─────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| **UI** | Streamlit | 1.59.0 | Chat interface with download buttons |
| **Agent** | LangGraph | 1.2.8 | Stateful ReAct agent with memory |
| **LLM Framework** | LangChain | 1.3.11 | Tool binding, message handling |
| **LLM** | Groq (`llama-3.1-8b-instant`) | — | Fast free-tier inference |
| **Tool Server** | FastAPI + MCP | 0.111.0 / 1.27.0 | REST API + MCP protocol |
| **Data** | Pandas | 2.1.4 | Excel read, filter, aggregate |
| **Reports** | openpyxl | 3.1.5 | Styled Excel report generation |
| **Runtime** | Python | 3.11 | — |

---

## Project Structure

```
society-agent/
│
├── data/                          # Source Excel files (never modified by code)
│   ├── Maintenance.xlsx           # 2,848 rows — flat payment records
│   └── Expenses.xlsx              # 977 rows — society expense records
│
├── server/                        # Backend data + API layer
│   ├── __init__.py
│   ├── data_loader.py             # Pandas data helpers (read-only)
│   └── main.py                    # FastAPI app + MCP tool definitions
│
├── agent/                         # AI agent layer
│   ├── __init__.py
│   ├── prompts.py                 # System prompt with formatting rules
│   ├── tools.py                   # LangChain @tool wrappers
│   └── graph.py                   # LangGraph StateGraph + stream_chat
│
├── reports/                       # Excel report generator
│   ├── __init__.py
│   └── generator.py               # Styled pending + balance sheet reports
│
├── ui/                            # Frontend
│   └── app.py                     # Streamlit chat UI
│
├── test_data_loader.py            # Phase 1 tests
├── test_server.py                 # Phase 2 tests
├── test_agent.py                  # Phase 3 tests
├── test_e2e.py                    # Phase 6 full integration tests
├── test_notebook.ipynb            # Interactive Jupyter testing notebook
│
├── .env                           # GROQ_API_KEY (never commit this)
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

---

## Data

### Maintenance.xlsx
| Column | Type | Description |
|---|---|---|
| Maintenance Month | string | e.g. `Jan_2024` |
| Date | date | Payment date |
| Flat Number | int | e.g. 101, 205, 601 |
| Name | string | Resident name (`NA` = vacant) |
| Amount | float | Maintenance paid (Rs. 1,000 standard) |
| Late Charges | float | Late payment charges if any |

### Expenses.xlsx
| Column | Type | Description |
|---|---|---|
| Month | string | e.g. `Jan_2024` |
| Date | date | Expense date |
| Expence Type | string | Category (Cleaning, Electricity, etc.) |
| Details | string | Expense description |
| Amount | float | Amount spent |
| Spend By | string | Who spent |

### Key Facts
- **88 occupied flats** across floors 1–10 (101–1008)
- **11 vacant flats**: 103, 205, 303, 401, 502, 504, 808, 906, 1002, 1007, 1008
- **24 months of data**: January 2024 – December 2025
- **Standard maintenance**: Rs. 1,000 per flat per month
- **Expense categories**: Cleaning, Electricity, Water Bill, Water Tanker, Security Guard, CCTV Maintenance, Solar, Stationary, Name Board, A1/A2/A3 Common

---

## Setup & Installation

### Prerequisites
- Python 3.11+
- A [Groq API key](https://console.groq.com) (free)

### 1. Clone / open the project
```powershell
cd society-agent
```

### 2. Create virtual environment
```powershell
# Using uv (recommended)
uv venv --python 3.11
.venv\Scripts\activate
uv pip install -r requirements.txt

# Or using pip
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Set your Groq API key
Open `.env` and add your key:
```
GROQ_API_KEY=gsk_your_actual_key_here
```

> Get a free key at [console.groq.com](https://console.groq.com) → API Keys → Create API Key

### 4. Verify setup
```powershell
python test_data_loader.py   # test data layer
python test_server.py        # test tools layer
python test_agent.py         # test agent (requires API key)
python test_e2e.py           # full integration test
```

---

## Running the App

```powershell
# From inside society-agent/ folder
streamlit run ui/app.py
```

Opens automatically at **http://localhost:8501**

> To also run the FastAPI server separately (optional — for Swagger UI testing):
> ```powershell
> uvicorn server.main:app --reload --port 8000
> # Then open http://localhost:8000/docs
> ```

---

## How It Works

### Agent Flow

```
User message
     │
     ▼
llm_node  ──── decides which tool to call ───►  tool_node
     ▲                                               │
     │         loops until final answer              │ executes tool
     └───────────────────────────────────────────────┘
     │
     ▼
Final formatted response → Streamlit UI
```

1. **User sends a message** via the Streamlit chat input
2. **LangGraph `llm_node`** — Groq LLM receives the message + system prompt + conversation history. It decides whether to call a tool or respond directly.
3. **LangGraph `tool_node`** — If a tool call is needed, the tool is executed against the data layer. The result is returned to `llm_node`.
4. **`llm_node` again** — LLM receives the tool result and formats a clean, human-readable response.
5. **Streamlit renders** the streamed response with a live typing effect.

### Memory
Each chat session has a unique `thread_id`. LangGraph's `MemorySaver` persists the full message history for that thread, enabling natural follow-up questions like:
- *"What about for the full year?"* (after asking about a month)
- *"How much did they pay in total?"* (after asking about a specific flat)

---

## Available Tools

| Tool | Parameters | Description |
|---|---|---|
| `get_all_months` | — | List all 24 available months |
| `get_pending_maintenance` | `month` or `year` | Flats that have NOT paid |
| `get_collected_maintenance` | `month` or `year` | Flats that HAVE paid |
| `get_balance_sheet` | `month` or `year` | Income vs expenses summary |
| `get_expense_summary` | `month` or `year` | Expenses grouped by category |
| `get_flat_history` | `flat_number` | Full payment history for one flat |
| `download_pending_report` | `month` or `year` | Generate pending Excel file |
| `download_balance_report` | `month` or `year` | Generate balance sheet Excel file |

All tools are registered as both **LangChain tools** (for the agent) and **MCP tools** (for the FastAPI server).

---

## Example Queries

| User Query | Tool Called | Sample Response |
|---|---|---|
| "What months do we have?" | `get_all_months` | Lists all 24 months grouped by year |
| "Who hasn't paid for March 2025?" | `get_pending_maintenance` | 9 flats listed with names |
| "Balance sheet for January 2024" | `get_balance_sheet` | Rs. 76,000 collected · Rs. 56,626 spent · Rs. 19,374 net |
| "Total electricity in 2024?" | `get_expense_summary` | Rs. 3,29,630 |
| "Show history for flat 601" | `get_flat_history` | 24 months, Rs. 23,000 total paid |
| "Download pending list for 2025" | `download_pending_report` | Excel file ready for download |
| "What about the whole year?" | `get_balance_sheet` | Uses memory — no need to repeat year |

---

## Test Results

```
==========================================================
  RESULTS:  34/34 passed   |   0 failed
==========================================================

  Layer                    Tests   Result
  ─────────────────────────────────────────
  1. Data Layer            14      All passed
  2. Tools Layer            8      All passed
  3. Report Generation      4      All passed
  4. Agent (LangGraph)      8      All passed
```

Run the full test suite:
```powershell
python test_e2e.py
```

---

## Known Limitations

| Issue | Detail | Impact |
|---|---|---|
| **Groq rate limits** | Free tier: ~20,000 tokens/min. SDK auto-retries with backoff | Occasional slow responses |
| **In-memory sessions** | `MemorySaver` stores history in RAM — lost on server restart | Restart = new conversation |
| **Excel file locked** | If Maintenance.xlsx is open in Excel, Pandas cannot read it | Close Excel before running |
| **Month name typos** | Raw data has `Jun_2024` / `july_2025` inconsistencies | Handled by `_normalise_month()` in data_loader |
| **No authentication** | Streamlit app has no login — anyone on the network can access | Add auth for production use |

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | ✅ Yes | Your Groq API key — get it at [console.groq.com](https://console.groq.com) |

---

*Built with LangGraph · LangChain · Groq · FastAPI · MCP · Streamlit · Pandas · openpyxl*
