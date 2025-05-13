# GitHub Repository Analyzer with Agno and Groq

This project is a powerful GitHub Repository Analyzer built with the [Agno framework](https://github.com/agno-agi/agno) and Groq LLMs. It enables users to analyze GitHub repositories (e.g., `agno-agi/agno`) through a conversational interface, leveraging two specialized agents:

* **GitHub Agent** for data retrieval.
* **Reasoning Agent** for in-depth analysis and explanations.

The system supports queries ranging from simple data retrieval (e.g., listing files) to complex tasks like counting AGNO agents or explaining repository workflows, with seamless follow-up interactions.

## Features

### Dual-Agent Architecture

* **GitHub Agent**: Retrieves specific data from GitHub repositories using tools like `get_directory_content`, `get_file_content`, and `search_code`.
* **Reasoning Agent**: Analyzes retrieved data to provide human-readable explanations of repository structure, architecture, dependencies, and code logic.

### Context-Aware Conversations

Maintains repository context (e.g., `agno-agi/agno`) across queries.

### Dynamic Query Handling

Breaks down complex queries into steps for dynamic data fetching and analysis.

### Follow-Up Affirmations

Conversational follow-ups are supported with simple affirmations like “yes.”

### Error Resilience

Handles API errors, missing directories, and tool failures gracefully.

### Streamlit Interface

Interactive web app for querying repositories, displaying results, and debugging tool calls.

## Prerequisites

* Python 3.8+
* GitHub Personal Access Token (PAT)
* Groq API key
* `.env` file with:

```bash
GITHUB_ACCESS_TOKEN=your_github_personal_access_token
GROQ_API_KEY=your_groq_api_key
```

## Installation

1. Clone the repository.
2. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Project Structure

| File               | Description                                                    |
| ------------------ | -------------------------------------------------------------- |
| `agents.py`        | Defines GitHub Agent, Reasoning Agent, and coordination logic. |
| `app_groq.py`      | Streamlit interface.                                           |
| `llm_providers.py` | Configures Groq LLM models.                                    |
| `utils.py`         | Helper functions for UI and messaging.                         |
| `debug_github.py`  | Tests GitHub API and agent functionality.                      |
| `requirements.txt` | Lists dependencies.                                            |
| `README.md`        | Project documentation.                                         |

## Running the App

```bash
streamlit run app_groq.py
```

Access via `http://localhost:8501`.

## Usage Examples

### Simple Data Retrieval

* List directories
* Show README content
* List recent pull requests

### Complex Analysis

* Count AGNO agents
* Explain architecture
* Describe workflows

### Follow-Up Interactions

Affirm “yes” to trigger suggested actions.

## How It Works

### Query Routing

* GitHub Agent for data retrieval.
* Reasoning Agent for analysis.

### Data Retrieval

Robust use of `GithubTools` for data fetching.

### Analysis & Explanations

Reasoning Agent gathers and synthesizes insights dynamically.

### Follow-Up Handling

Tracks conversation history for seamless follow-ups.

## Troubleshooting

* Invalid Tokens: Check `.env` file.
* API Errors: Test with `debug_github.py`.
* Directory Not Found: Suggests alternatives.
* Tool Failures: Uses fallback strategies.
* Console Logs: Enable debug mode.

### Debugging

```bash
python debug_github.py
```

## What’s Improved

* Enhanced Agent Coordination
* Robust Error Handling
* Follow-Up Support
* Complex Query Breakdown

## Need Help?

* [Agno Documentation](https://github.com/agno-agi/agno)
* Community Support (Forum / Discord)
* GitHub Issues for bugs and requests
