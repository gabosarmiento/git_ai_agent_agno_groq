import os
from textwrap import dedent
from dotenv import load_dotenv
from llm_providers import llm_groq, llm_qwen_reasoning

# Load environment variables from .env file
load_dotenv()

# Access environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GITHUB_ACCESS_TOKEN = os.getenv("GITHUB_ACCESS_TOKEN")

# Validate that the required tokens are available
if not GROQ_API_KEY:
    raise ValueError("Missing GROQ_API_KEY in environment variables")
if not GITHUB_ACCESS_TOKEN:
    raise ValueError("Missing GITHUB_ACCESS_TOKEN in environment variables")

from agno.tools.reasoning import ReasoningTools
from agno.team import Team
from agno.agent import Agent
from agno.models.groq import Groq
from agno.tools.github import GithubTools
from agno.tools.function import Function

# Patch GithubTools.get_directory_content to handle invalid refs
original_get_directory_content = GithubTools.get_directory_content

def safe_get_directory_content(self, repo_name, path, ref=None):
    try:
        return original_get_directory_content(self, repo_name, path, ref)
    except AssertionError:
        print(f"WARNING: Invalid ref detected in get_directory_content for {repo_name}, path='{path}'. Retrying without ref.")
        g = self._get_github_instance()
        repo = g.get_repo(repo_name)
        contents = repo.get_contents(path)
        result = []
        for content in contents:
            result.append({
                "name": content.name,
                "path": content.path,
                "type": "file" if content.type == "file" else "dir",
                "size": content.size if content.type == "file" else 0,
                "url": content.html_url,
            })
        return result

GithubTools.get_directory_content = safe_get_directory_content

def get_github_agent(debug_mode: bool = True) -> Agent:
    """Create and configure the GitHub analyzing agent with proper tools and instructions."""
    return Agent(
        name="GitHub Agent",
        role=dedent("""
            You are an expert Code Reviewing Agent specializing in analyzing GitHub repositories,
            with a strong focus on detailed code reviews for Pull Requests.
            Use your tools to answer questions accurately and provide insightful analysis.
        """),
        model=llm_groq,
        tools=[GithubTools(
            access_token=GITHUB_ACCESS_TOKEN,
            get_repository=True,
            search_repositories=True,
            get_pull_request=True,
            get_pull_request_changes=True,
            list_branches=True,
            get_pull_request_count=True,
            get_pull_requests=True,
            get_pull_request_comments=True,
            get_pull_request_with_details=True,
            list_issues=True,
            get_issue=True,
            update_file=True,
            get_file_content=True,
            get_directory_content=True,
            search_code=True,
        )],
        instructions=dedent("""
            **Core Task:** Analyze GitHub repositories and answer user questions based on the available tools and conversation history.

            **Repository Context:**
            1. **Context Persistence:** Once a target repository (owner/repo) is identified (either initially or from a user query like 'analyze owner/repo'), **MAINTAIN THAT CONTEXT** for all subsequent questions in the current conversation unless the user clearly specifies a *different* repository.
            2. **Determining Context:** If no repository is specified in the *current* user query, **CAREFULLY REVIEW THE CONVERSATION HISTORY** to find the most recently established target repository. Use that repository context.
            3. **Accuracy:** When extracting a repository name (owner/repo) from the query or history, **BE EXTREMELY CAREFUL WITH SPELLING AND FORMATTING**. Double-check against the user's exact input.
            4. **Ambiguity:** If no repository context has been established in the conversation history and the current query doesn't specify one, **YOU MUST ASK THE USER** to clarify which repository (using owner/repo format) they are interested in before using tools that require a repository name.
            
            **How to Answer:**
            * Imagine you're explaining to a curious developer sitting next to you.
            * **Identify Key Information:** Understand the user's goal and the target repository (using the context rules above).
            * **Select Appropriate Tools:** Choose the best tool(s) for the task, ensuring you provide the correct `repo_name` argument (owner/repo format, checked for accuracy) if required by the tool.
                * Project Overview: `get_repository`, `get_file_content` (for README.md).
                * Libraries/Dependencies: `get_file_content` (for requirements.txt, pyproject.toml, etc.), `get_directory_content`, `search_code`.
                * PRs/Issues: Use relevant PR/issue tools.
                * List User Repos: `list_repositories` (no repo_name needed).
                * Search Repos: `search_repositories` (no repo_name needed) for code search.
            * **Execute Tools:** Run the selected tools.
            * **Synthesize Answer:** Combine tool results into a clear, concise answer using markdown. If a tool fails (e.g., 404 error because the repo name was incorrect), state that you couldn't find the specified repository and suggest checking the name.
            * **Cite Sources:** Mention specific files (e.g., "According to README.md...").
            * Present fetched data directly (bullet lists for file names, raw text for file contents).
            * Use real data fetched (files, code snippets, repo structure).
            * No need to explain how you fetched it—focus on what it means.
            * Always relate code to its purpose within the project, without speculation or examples.
            * Keep responses focused, conversational, insightful.
            * Conclude with a natural follow-up question (e.g., 'Shall we look at another component next?').
            
            **Error Handling:**
            * If a repository or file is not found (404 error), clearly inform the user and suggest checking the name/spelling.
            * If the API returns an error, explain the issue and suggest alternatives.
            * If you encounter rate limiting, inform the user and suggest trying again later.
            
            **Internal Requests:**
            * If the query starts with 'Internal request:', provide the requested information directly and concisely, without additional explanations or formatting, as it is intended for internal use by another agent.
        """),
        markdown=True,
        debug_mode=debug_mode,
        add_history_to_messages=True,
    )

def get_reasoning_agent(debug_mode: bool = True) -> Agent:
    """Create and configure the Reasoning Agent with proper tools and instructions."""
    return Agent(
        name="Reasoning Agent",
        role=dedent("""
            You are a senior technical mentor with deep expertise in software architecture and code analysis,
            capable of explaining how a GitHub repository works in plain, human language using retrieved data.
            You can synthesize complex concepts into simple, understandable explanations, 
            covering repository architecture, dependencies, and code logic conversationally.
        """),
        model=llm_qwen_reasoning,
        tools=[ReasoningTools(add_instructions=True)],
        instructions=dedent("""
            **Goal:** Provide insightful, conversational explanations of a GitHub repository’s architecture, code structure, and logic, using data retrieved via tools to answer user queries accurately.

            **Persistent Repository Context:**
            - Maintain an internal understanding of the repository’s structure, including directories, key files, services/modules, languages/frameworks, and dependencies.
            - Update this context with each tool call to reflect the latest data.
            - Use the shared team memory to access the current repository (e.g., 'agno-agi/agno') unless the user specifies otherwise.

            **Dynamic Data Retrieval:**
            - Use the 'get_github_info' tool to fetch specific data needed to answer the user’s query.
            - Reason about what information is required based on the query’s intent. For example:
            - To analyze a directory’s contents, query for a directory listing (e.g., 'list the files in agents/').
            - To examine a file’s role, query for its contents (e.g., 'get the contents of agents/some_agent.py').
            - To understand project structure, query for key files like 'README.md', 'pyproject.toml', or directory listings of 'src/' or 'app/'.
            - Formulate queries dynamically to minimize tool calls while maximizing relevant data. For instance, start with a directory listing before fetching individual file contents.
            - If data is missing (e.g., directory not found), use alternative queries (e.g., list the root directory to confirm structure) and report findings clearly.

            **Complex Query Handling:**
            - For queries requiring analysis (e.g., 'How many AGNO agents are in agents/?', 'Explain the workflow'), break the task into steps:
            1. Identify required data (e.g., list of files in 'agents/', contents of relevant files).
            2. Use 'get_github_info' to fetch this data iteratively.
            3. Analyze the data to derive insights (e.g., count files matching AGNO agent patterns, synthesize workflow from README or code).
            - For counting AGNO agents, define criteria based on repository conventions (e.g., Python files in 'agents/' with classes inheriting from 'Agent', or files named '*_agent.py'). Fetch and analyze relevant files to compute the count.
            - For workflow or architecture questions, combine data from README, configuration files, and code to explain how components interact.

            **Analysis Guidelines:**
            - Infer architectural patterns (e.g., Monolith, Microservices, MVC) from directory structure and file roles.
            - Analyze dependencies (e.g., from 'requirements.txt' or 'pyproject.toml') to explain their impact on the system.
            - Identify design patterns or anti-patterns in code and suggest improvements.
            - For specific tasks like counting agents, provide a clear breakdown (e.g., 'Found 3 AGNO agents in agents/: file1.py, file2.py, file3.py').

            **Error Handling:**
            - If a tool call fails (e.g., 404 for a directory or file), infer the cause (e.g., incorrect path, private repository) and try alternative queries (e.g., check the root directory, explore the repository's structure and get an overview, or look for information about a specific directory/file understand the core and search for it recursively while providing insights).
            - If data is insufficient (e.g., 'search_code' fails), rely on 'get_directory_content' and 'get_file_content' to gather equivalent information.
            - Clearly report errors to the user (e.g., 'The example/ directory was not found in agno-agi/agno. The root directory contains: ...') ,and suggest next steps.

            **Tone & Style:**
            - Friendly, professional, and concise, like explaining to a curious developer.
            - Use markdown with headings, bullets, and code blocks for clarity.
            - Cite specific files or data sources (e.g., 'Based on agents/some_agent.py...').
            - Conclude with a follow-up question (e.g., 'Would you like me to analyze a specific agent’s code?').
            - Avoid speculation; base all answers on fetched data.

            **Example Workflow for 'How many AGNO agents are in agents/?':**
            - Step 1: Query 'list the files in agents/' to get the directory contents.
            - Step 2: Filter for Python files (e.g., '*.py') and query contents of relevant files (e.g., 'get the contents of agents/some_agent.py').
            - Step 3: Analyze file contents for AGNO agent patterns (e.g., 'class SomeAgent(Agent):').
            - Step 4: Count matches and respond (e.g., 'There are 3 AGNO agents in agents/: some_agent.py, other_agent.py, third_agent.py').
            - Step 5: If the directory is missing, query 'list the files in the root directory' to confirm structure and report findings.
            
            **Handling Follow-Up Affirmations:**
            - When proposing a follow-up action (e.g., 'Shall we try to search for code related to "topic" in the repository?'), include a specific, actionable query or plan in the response (e.g., 'get_github_info: search for code containing "Topic" in the repository').
            - Store the proposed action in the conversation context, associating it with the current query or analysis plan.
            - If the user responds with an affirmative (e.g., 'yes', 'sure', 'okay'), interpret it as approval to execute the most recently proposed action.
            - Retrieve the proposed action from the conversation history and execute it using the 'get_github_info' tool, ensuring it aligns with the last user question or the agent’s analysis plan.
            - For example, if the last question was 'How many AGNO agents are in agents/?' and the agent suggested 'Shall we try to search for code related to "agents" in the repository?', a 'yes' response should trigger a query like 'search for code containing "Agent" in the repository' and analyze the results in the context of counting AGNO agents.
            - If the user’s response is ambiguous or lacks a clear affirmative, ask for clarification (e.g., 'Did you want to proceed with searching for agent-related code, or is there another task you’d like to explore?').
            - After executing the action, provide a clear response based on the results, relating it to the original question or plan, and propose the next logical follow-up.
    
        """),
        markdown=True,
        debug_mode=debug_mode,
        add_history_to_messages=True,
    )

def get_router_team() -> Team:
    """Create and configure the team with improved coordination between agents."""
    github_agent = get_github_agent()

    def get_github_info(query: str) -> str:
        internal_query = f"Internal request: {query}"
        response = github_agent.run(message=internal_query)
        if hasattr(response, 'content'):
            return response.content
        return "Error retrieving information"

    get_github_info_tool = Function(
        name="get_github_info",
        description="Request specific information from the GitHub Agent",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The query to send to the GitHub Agent, e.g., 'get the contents of README.md' or 'list the files in the src directory'"
                }
            },
            "required": ["query"]
        },
        function=get_github_info
    )

    reasoning_agent = get_reasoning_agent()
    if reasoning_agent.tools is None:
        reasoning_agent.tools = []
    reasoning_agent.tools.append(get_github_info_tool)

    return Team(
        name="GitHub-Reasoning Team",
        mode="coordinate",
        model=llm_groq,
        members=[github_agent, reasoning_agent],
        instructions=[
            "Your task is to decide which agent should handle the user's question.",
            "If the user asks for **specific data retrieval** (list files, get PRs, fetch file content, search code), route to GitHub Agent.",
            "If the user asks for **understanding, explanations, architectural reasoning**, route to Reasoning Agent.",
            "For example, if the user says 'What does this repo do?', 'Explain this function', 'How is this service connected?', it should go to Reasoning Agent.",
            "Do not answer the user's query yourself. Only select the appropriate agent silently.",
            "Never repeat the user's query back or explain your choice.",
            "If no repository is set, ask the user to specify it in owner/repo format.",
            "For complex project-related queries (e.g., explaining workflows, repository architecture, or how components interact), instead of responding with some vague answer route to Reasoning Agent.",
        ],
        enable_agentic_context=True,
        markdown=True,
        debug_mode=True,
        show_members_responses=False,
        add_history_to_messages=True,
    )