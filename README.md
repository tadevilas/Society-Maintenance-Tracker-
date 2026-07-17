# Society Maintenance Tracker

An interactive assistant that helps get quick answers based on society maintenance records and the balance sheet — built as an MCP-style agent so it can be queried directly from a chat interface.

## Repository Layout

- **society-agent/** – The core agent application: server, agent logic, tests, Docker setup, and its own detailed [README](society-agent/README.md)
- **society-maintenance-agent-readme.html** – Rendered documentation/overview of the agent
- **docker-files-explained-society-maintenance-agent.html** – Walkthrough explaining the Docker setup used to containerize the agent
- **society-maintenance-agent-test-report.html** – Test results and coverage report for the agent

## What it does

The agent connects to society maintenance data and can answer questions such as:

- Which flats have paid or are pending maintenance for a given month/year
- Income vs. expense balance sheet summaries
- Expense breakdowns by category (electricity, cleaning, water, etc.)
- Full payment history for a specific flat
- Generating downloadable balance and pending-maintenance reports

## Getting Started

See [`society-agent/README.md`](society-agent/README.md) for setup instructions, running the server, and Docker usage.
