"""
ui/app.py
---------
Streamlit Chat UI for the Society Maintenance AI Agent.

Run with:
    streamlit run ui/app.py   (from inside society-agent/)
"""

import sys
import os
import time
from pathlib import Path

# ── Path setup ─────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import streamlit as st
from agent.graph import stream_chat, chat
from server.data_loader import get_all_months
from reports.generator import generate_pending_excel, generate_balance_excel

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Society Maintenance Assistant",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main header */
    .main-header {
        background: linear-gradient(90deg, #1e3a5f 0%, #2d6a9f 100%);
        padding: 1rem 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        color: white;
    }
    /* Quick action chips */
    .stButton > button {
        border-radius: 20px;
        font-size: 12px;
        padding: 4px 12px;
        height: auto;
    }
    /* Sidebar section headers */
    .sidebar-section {
        font-size: 12px;
        font-weight: 700;
        color: #57606a;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin: 12px 0 6px 0;
    }
    /* Download button styling */
    .download-btn { margin-top: 8px; }
</style>
""", unsafe_allow_html=True)


# ── Session state init ─────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []          # chat history for display

if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"session-{int(time.time())}"  # unique per session

if "download_store" not in st.session_state:
    st.session_state.download_store = {}    # stores file bytes keyed by filename

if "quick_prompt" not in st.session_state:
    st.session_state.quick_prompt = None


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏠 Society Assistant")
    st.markdown("---")

    # ── Filter section ─────────────────────────────────────────────────────────
    st.markdown('<p class="sidebar-section">📅 Filter by Period</p>', unsafe_allow_html=True)

    filter_type = st.radio(
        "Filter by",
        ["Month", "Year"],
        horizontal=True,
        label_visibility="collapsed",
    )

    selected_month = None
    selected_year  = None

    if filter_type == "Month":
        try:
            all_months = get_all_months()
        except Exception:
            all_months = []
        selected_month = st.selectbox(
            "Select Month",
            options=[""] + all_months,
            format_func=lambda x: "-- Select month --" if x == "" else x,
        )
    else:
        try:
            all_years = sorted({int(m.split("_")[1]) for m in get_all_months()})
        except Exception:
            all_years = []
        selected_year = st.selectbox(
            "Select Year",
            options=[""] + all_years,
            format_func=lambda x: "-- Select year --" if x == "" else str(x),
        )
        selected_year = int(selected_year) if selected_year else None

    st.markdown("---")

    # ── Download section ───────────────────────────────────────────────────────
    st.markdown('<p class="sidebar-section">📥 Download Reports</p>', unsafe_allow_html=True)

    period_label = selected_month or (str(selected_year) if selected_year else None)

    if not period_label:
        st.info("Select a month or year above to enable downloads.")
    else:
        col1, col2 = st.columns(2)

        with col1:
            if st.button("📋 Pending List", use_container_width=True):
                with st.spinner("Generating..."):
                    file_bytes = generate_pending_excel(
                        month=selected_month or None,
                        year=selected_year or None,
                    )
                    fname = f"pending_{period_label}.xlsx"
                    st.session_state.download_store[fname] = file_bytes
                st.success("Ready!")

        with col2:
            if st.button("📊 Balance Sheet", use_container_width=True):
                with st.spinner("Generating..."):
                    file_bytes = generate_balance_excel(
                        month=selected_month or None,
                        year=selected_year or None,
                    )
                    fname = f"balance_{period_label}.xlsx"
                    st.session_state.download_store[fname] = file_bytes
                st.success("Ready!")

        # Show download buttons for any generated files
        for fname, fbytes in st.session_state.download_store.items():
            st.download_button(
                label=f"⬇️ {fname}",
                data=fbytes,
                file_name=fname,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

    st.markdown("---")

    # ── Quick prompts ──────────────────────────────────────────────────────────
    st.markdown('<p class="sidebar-section">⚡ Quick Questions</p>', unsafe_allow_html=True)

    quick_prompts = [
        "What months of data do we have?",
        "Show pending maintenance for Jan 2024",
        "Balance sheet for full year 2024",
        "Total electricity expense in 2024",
        "Which flats have not paid for March 2025?",
        "Show payment history for flat 601",
        "How many vacant flats are there?",
        "What is the net balance for 2025?",
    ]

    for prompt in quick_prompts:
        if st.button(prompt, use_container_width=True, key=f"qp_{prompt}"):
            st.session_state.quick_prompt = prompt

    st.markdown("---")

    # ── New conversation ───────────────────────────────────────────────────────
    if st.button("🔄 New Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.thread_id = f"session-{int(time.time())}"
        st.session_state.download_store = {}
        st.rerun()

    st.markdown(
        "<p style='font-size:11px;color:#57606a;text-align:center;margin-top:8px'>"
        "Powered by Groq · LangGraph · Streamlit</p>",
        unsafe_allow_html=True,
    )


# ── Main panel ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h2 style="margin:0;font-size:22px">🏠 Society Maintenance Assistant</h2>
    <p style="margin:4px 0 0 0;font-size:13px;opacity:0.85">
        Ask anything about maintenance payments, expenses, and balance sheets.
    </p>
</div>
""", unsafe_allow_html=True)

# ── Display chat history ───────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Handle quick prompt click ──────────────────────────────────────────────────
if st.session_state.quick_prompt:
    user_input = st.session_state.quick_prompt
    st.session_state.quick_prompt = None
else:
    user_input = st.chat_input("Ask about maintenance, expenses, balance sheet...")

# ── Process input ──────────────────────────────────────────────────────────────
if user_input:
    # Add user message to history and display it
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Stream assistant response
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""

        try:
            for chunk in stream_chat(user_input, thread_id=st.session_state.thread_id):
                full_response += chunk
                response_placeholder.markdown(full_response + "▌")

            response_placeholder.markdown(full_response)

        except Exception as e:
            error_msg = f"⚠️ Error: {str(e)}\n\nPlease check your GROQ_API_KEY in `.env`."
            response_placeholder.markdown(error_msg)
            full_response = error_msg

    # Save assistant response to history
    st.session_state.messages.append({"role": "assistant", "content": full_response})
