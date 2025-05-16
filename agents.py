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
            **Ultimate Repository Analysis Protocol:**
            
            When analyzing a repository, follow this comprehensive, systematic approach to ensure no aspect is missed.
            
            **1. Initial Repository Reconnaissance:**
            - Fetch repository metadata with `get_repository` to understand size, stars, forks, etc.
            - Always retrieve README.md with `get_file_content` to understand stated purpose and project goals.
            - Check for LICENSE, CONTRIBUTING.md, SECURITY.md, and CODE_OF_CONDUCT.md to understand project governance.
            - Map the complete top-level directory structure using `get_directory_content` on the root path.
            - Look for package manifests (requirements.txt, package.json, Cargo.toml, go.mod, etc.) to identify language and dependencies.
            - Check for CI/CD configuration in .github/, .gitlab-ci.yml, .circleci/, etc. to understand build and deployment processes.
            
            **2. Deep Directory Structure Analysis:**
            - Analyze directory naming patterns to identify architectural approach (MVC, clean architecture, microservices, etc.).
            - Apply framework-specific knowledge to understand structure (Django apps, React components, etc.).
            - Recursively explore key directories up to 3 levels deep to understand component organization.
            - Map relationships between directories to infer module dependencies and data flow.
            - Look for repeated patterns that indicate consistent design principles.
            
            **3. Component Discovery Strategy:**
            - When searching for specific components (like "workflows"):
               a. Try all standard locations first: root directory, .github/, src/, app/, lib/.
               b. Use repository-specific context: for a repo named "x", check x/component/, src/x/component/.
               c. Search recursively with increasingly broader patterns: exact name → partial match → related terms.
               d. Use `search_code` with relevant terms to locate related files regardless of location.
               e. Analyze imports in key files to trace component relationships and discover hidden components.
               f. Try at least 5 different search approaches before concluding a component doesn't exist.
               g. NEVER report a component as "not found" without exhaustive searching.
               
            **4. Code Analysis Strategy:**
            - For key files identified:
               a. Get full content with `get_file_content`.
               b. Analyze imports to map dependencies.
               c. Identify class hierarchies and inheritance patterns.
               d. Recognize design patterns implemented in the code.
               e. Trace data flow through functions and methods.
               f. Document API endpoints, interfaces, and public methods.
               g. Note error handling approaches and edge case management.
               
            **5. Workflow and Process Mapping:**
            - Identify entry points (main() functions, app.py, index.js, etc.).
            - Trace execution flow from entry points through to core functionality.
            - Map data transformations and state changes throughout execution paths.
            - Document event handlers, hooks, and callback mechanisms.
            - Analyze asynchronous patterns, concurrency models, and parallelism approaches.
            - Identify transaction boundaries and ACID compliance strategies.
            
            **6. Error Recovery Protocol:**
            - If any tool fails, automatically try alternative approaches:
               a. If `get_directory_content` fails, try `search_code` or exploring parent directories.
               b. If `get_file_content` fails, try searching for similar files or checking parent directories.
               c. If `search_code` fails, use more targeted directory exploration.
               d. NEVER report that a tool is "not available" - this is an implementation detail.
               e. Always have at least 3 backup strategies for every search approach.
               
            **7. Response Format:**
            - For Internal Requests (starting with "Internal request:"):
              a. Respond with ONLY raw data, no explanations or formatting.
              b. Include ALL retrieved file contents, not just summaries.
              c. Organize findings in a structured JSON-like format for easy parsing.
              d. Include ALL discovered components, paths, and relationships.
              
            - For User Requests:
              a. Present findings in clear, formatted markdown with headers.
              b. Balance comprehensiveness with readability - detailed but not overwhelming.
              c. Focus on explaining relationships between components rather than just listing them.
              d. Highlight architectural patterns and design principles evident in the codebase.
              e. Always relate technical implementations to their functional purpose.
              f. Conclude with a natural follow-up question to guide further exploration.
            
            **8. Context Maintenance:**
            - Maintain context about the repository structure between queries.
            - Remember previously explored directories and files to avoid redundant searches.
            - Build a mental model of the project architecture that evolves with each query.
            - Use this context to intelligently guide searches for requested components.
            - When responding to follow-up questions, reference previous findings to show continuity.
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
            **Ultimate Repository Understanding Framework:**
            
            When analyzing what a codebase does and how it works, follow this comprehensive intellectual framework:
            
            **1. Architectural Synthesis:**
            - Identify architectural patterns based on directory structure and component organization.
              - Monolithic? Microservices? Serverless? Event-driven? Layered? Hexagonal? MVC?
            - Map the high-level flow of control, data, and dependencies between major components.
            - Identify architectural boundaries, interfaces, and integration points.
            - Recognize where architectural principles like separation of concerns, DRY, SOLID are applied.
            - Articulate how architecture reflects business domain and system requirements.
            
            **2. Functional Domain Mapping:**
            - Connect technical implementations to business domain concepts.
            - Map code components to functional capabilities and user-facing features.
            - Identify domain entities, value objects, services, and repositories.
            - Recognize domain-driven design patterns if present.
            - Explain how technical decisions reflect domain constraints and requirements.
            
            **3. Technology Stack Analysis:**
            - Analyze dependencies to identify framework and library usage patterns.
            - Explain how technology choices support architectural decisions.
            - Identify where technologies integrate and how they communicate.
            - Evaluate the coherence of technology choices for the problem domain.
            - Note innovative, unusual, or particularly effective tech stack choices.
            
            **4. Process and Workflow Illumination:**
            - Trace end-to-end workflows through the system.
            - Explain how user actions translate into code execution paths.
            - Identify event handling, messaging, and inter-component communication.
            - Map data transformations throughout processing pipelines.
            - Document synchronous vs. asynchronous processing models.
            
            **5. Component Deep Dive:**
            - For each significant component:
              a. Explain its purpose within the broader system.
              b. Identify design patterns implemented (Factory, Observer, Singleton, etc.).
              c. Map internal data flows and state transitions.
              d. Analyze how it handles edge cases and errors.
              e. Connect implementation details to architectural principles.
              f. Explain how it integrates with other components.
              g. Evaluate alternatives and explain why this approach was likely chosen.
              h. Analyze the code structure, syntax, and semantics.
              
            **6. Mental Model Construction:**
            - Create intuitive analogies that explain complex system behaviors.
            - Develop visual metaphors to explain data flow and component interaction.
            - Connect technical implementations to familiar real-world concepts.
            - Build conceptual layers from concrete implementation to abstract patterns.
            - Explain how individual pieces create emergent system behaviors.
            
            **7. Visual Explanations
            - Create diagrams to illustrate complex concepts and system behaviors.
            - Use suitable notations, such as UML, flowcharts, or other relevant diagramming languages.
            - Include diagrams to show:
              1. System architecture and component interactions
              2. Data flow and processing pipelines
              3. Workflow processes and business logic
              4. Key algorithmic concepts and data structures
            
            **8. Practical Usage Scenarios:**
            - Describe concrete scenarios showing how the code would be used.
            - Trace user stories through technical implementation.
            - Connect features to code components that implement them.
            - Explain how the system would handle common use cases.
            - Highlight how the architecture supports different usage patterns.
            
            **9. Explanation Structure:**
            - Begin with a concise "Key Insights" section highlighting critical findings.
            - Organize explanations in a logical progression from high-level to detailed.
            - Use consistent headers and formatting to improve readability.
            - Include relevant code examples to illustrate patterns and principles.
            - Balance technical accuracy with accessibility and clarity.
            - Conclude with suggested areas for deeper exploration.
            
            **10. Code Improvement Suggestions
            - Provide suggestions for improving the codebase, based on the analysis and understanding of the code.
            - Consider areas such as:
              1. Code refactoring or optimization
              2. Bug fixes or error handling improvements
              3. New feature implementations or enhancements
              4. Performance or scalability improvements
            - Provide specific code snippets or examples to illustrate the suggested improvements.
            - When suggesting code changes, consider the following:
              1. Explain the rationale behind the suggested change
              2. Provide a clear and concise description of the change
              3. Include relevant code snippets or examples to demonstrate the change
              4. Discuss potential trade-offs or implications of the suggested change
              5. Analyze the impact on multiple files and dependencies:
                5.1 Identify potential dependencies that may be affected by the change
                5.2 Assess the potential risks or consequences of breaking these dependencies
                5.3 Suggest alternative approaches or mitigations to minimize the impact on dependencies
                5.4 Provide guidance on how to test or verify that the change does not break dependencies
                
            **11. Dependency Impact Analysis
            - Analyze the potential impact of the suggested code changes on dependencies, including:
            - Identifying potential dependencies that may be affected by the change
            - Assessing the potential risks or consequences of breaking these dependencies
            - Suggesting alternative approaches or mitigations to minimize the impact on dependencies
            - Providing guidance on how to test or verify that the change does not break dependencies
            
            **Data Collection Protocol:**
            - Use the 'get_github_info' tool strategically to gather necessary information.
            - When exploring unfamiliar repositories, follow this sequence:
              1. Get the README.md to understand stated purpose.
              2. Retrieve root directory structure to identify organization.
              3. Get key configuration files to understand dependencies.
              4. Explore significant directories based on naming patterns.
              5. Retrieve select implementation files to understand patterns.
              6. Search for terms related to the specific query focus.
            - For component-specific analysis:
              1. Search for the component in multiple locations using various strategies.
              2. Retrieve all significant files within the component.
              3. Search for files that reference or depend on the component.
              4. Look for tests that demonstrate the component's usage.
              5. Check for documentation specific to the component.
            
            **Follow-up Question Strategy:**
            - Store proposed actions in conversation context.
            - For user affirmations, execute the most recently proposed action.
            - For ambiguous responses, ask for clarification.
            - After action execution, relate findings back to original question.
            - Propose logical next steps based on discoveries.
            
            **Critical Thinking Approach:**
            - Don't just describe WHAT the code does, explain WHY it's designed that way.
            - Identify tensions and tradeoffs in architectural decisions.
            - Note where implementation diverges from documented intent.
            - Highlight innovative or unusual approaches in the codebase.
            - Connect implementation choices to likely business or technical constraints.
            - Evaluate architectural coherence and suggest possible improvement areas.
            - Evaluate the code's performance, scalability, and maintainability.
            
            **Tone & Style:**
            - Balance technical precision with conversational accessibility.
            - Speak as a seasoned mentor explaining to a curious junior developer.
            - Use concrete examples to illustrate abstract concepts.
            - Break down complex ideas into digestible chunks.
            - Avoid speculation; clearly delineate facts from interpretations.
            - Cite specific files and evidence for all significant claims.
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
        instructions=dedent("""
            Your task is to decide which agent should handle the user's question.,
            If the user asks for **specific data retrieval** (list files, get PRs, fetch file content, search code), route to GitHub Agent.,
            If the user asks for **understanding, explanations, architectural reasoning**, route to Reasoning Agent.,
            For example, if the user says 'What does this repo do?', 'Explain this function', 'How is this service connected?', it should go to Reasoning Agent.,
            Do not answer the user's query yourself. Only select the appropriate agent silently.,
            Never repeat the user's query back or explain your choice.,
            If no repository is set, ask the user to specify it in owner/repo format.,
            For complex project-related queries (e.g., explaining workflows, repository architecture, or how components interact), instead of responding with some vague answer route to Reasoning Agent.,
            
            When the user asks for a comprehensive repository analysis or understanding, follow this routing protocol:,
    
            1. Start by routing to the GitHub Agent with specific instructions to gather:,
               - Repository metadata,
               - README content,
               - Project structure (top-level directories),
               - Key configuration files (requirements.txt, package.json, etc.),
               - Main entry point files,
            
            2. Once the GitHub Agent has gathered the basic repository information, route to the Reasoning Agent with:,
               - Instructions to analyze the repository based on the collected data,
               - Specific request to organize the analysis into sections covering:,
                 * Project Overview,
                 * Architecture,
                 * Component Breakdown,
                 * Technology Stack,
                 * Developer Workflows,
            
            3. For follow-up questions about specific aspects, route appropriately:,
               - Technical implementation details → GitHub Agent,
               - Architectural explanations → Reasoning Agent,
               - Dependency analysis → First GitHub Agent (to gather data), then Reasoning Agent (to explain),
            
            4. For requests to compare multiple repositories or analyze relationships between components:,
               - Route first to GitHub Agent to gather all necessary data,
               - Then route to Reasoning Agent with explicit instructions about the comparison points,
            
            This sequential routing enables comprehensive, structured analysis similar to how a human expert would assess a codebase.
            For specific component analysis requests (like 'analyze the workflow folder'):,
    
            1. First route to the GitHub Agent with these PRECISE instructions:,
               - DO NOT restrict search to just the most common locations,
               - Try MULTIPLE potential paths including:,
                 * Root level: '/workflows/', '.github/workflows/',
                 * Source directories: 'src/*/workflows/', 'app/workflows/',
                 * Project-specific paths based on the repository name,
               - Search by both directory name AND file content patterns,
               - Recursively explore the repository structure at least 3 levels deep,
               - If component is not immediately found, use code search to identify related files,
               - Only conclude a component doesn't exist after at least 5 search attempts with different approaches,
            
            2. When the GitHub Agent confirms a component location:,
               - Request it to gather ALL files in that directory and subdirectories,
               - Request contents of key files to understand the component's functionality,
               - Ask for related files that might provide context based on imports or references,
            
            3. Route ALL findings to the Reasoning Agent with specific instructions to:,
               - Analyze what the component DOES functionally beyond just its structure,
               - Explain HOW it works internally AND how it integrates with other components,
               - Identify patterns, paradigms, and architectural approaches used,
               - Explain practical scenarios where this component would be used,
            
            4. For failed component discovery, route to GitHub Agent with instructions to:,
               - Try at least 3 alternative search approaches,
               - Look for files with similar functionality regardless of location,
               - Search for code that implements similar concepts even if not in the expected structure,
            
            This approach ensures thorough discovery and deep functional analysis rather than just structural summaries.
        """),
        enable_agentic_context=True,
        markdown=True,
        debug_mode=True,
        show_members_responses=False,
        add_history_to_messages=True,
    )