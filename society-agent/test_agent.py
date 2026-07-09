"""
test_agent.py
-------------
Test the LangGraph agent end-to-end with a few sample questions.
Run: python test_agent.py  (from inside society-agent/)

Make sure GROQ_API_KEY is set in .env before running.
"""

import sys
sys.path.insert(0, ".")

from agent.graph import chat, get_graph

SEP = "-" * 55

def ask(question: str, thread_id: str = "test-session"):
    print(f"\nYou : {question}")
    print(f"Bot : ", end="", flush=True)
    response = chat(question, thread_id=thread_id)
    print(response)
    print(SEP)

# ── Verify graph builds without error ─────────────────────────
print("Building agent graph...")
graph = get_graph()
print("Agent graph built OK")
print(SEP)

# ── Test conversations ─────────────────────────────────────────
# Each ask() in the same thread_id shares memory

ask("Hello! What can you help me with?")

ask("What months of data do we have?")

ask("How many flats did not pay maintenance in January 2024?")

ask("What was the total electricity expense in 2024?")

ask("Give me the balance sheet for January 2024")

# Test memory — refers to previous answer without restating context
ask("What about for the full year 2024?")

ask("Show me the payment history for flat 601")
