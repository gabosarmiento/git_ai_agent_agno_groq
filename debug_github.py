# debug_github.py
import os
from dotenv import load_dotenv
from github import Github
from agno.tools.github import GithubTools
from agents import get_github_agent

# Load environment variables
load_dotenv()

# Get GitHub token
github_token = os.getenv("GITHUB_ACCESS_TOKEN")
if not github_token:
    print("ERROR: GitHub token not found in environment")
    exit(1)

print(f"Token available: {github_token[:4]}...{github_token[-4:]}")

# Test direct GitHub API access
try:
    g = Github(github_token)
    user = g.get_user()
    print(f"Successfully authenticated as: {user.login}")
    print(f"Rate limit: {g.get_rate_limit().core.remaining}/{g.get_rate_limit().core.limit}")
    
    # Test getting a repository
    repo_name = "agno-agi/agno"  # Example repository
    try:
        repo = g.get_repo(repo_name)
        print(f"Repository exists: {repo.full_name}")
        print(f"Description: {repo.description}")
        
        # Test getting repository contents
        contents = repo.get_contents("")
        print(f"Root directory contains {len(contents)} items")
        for content in contents[:5]:  # Show first 5 items
            print(f"- {content.path} ({content.type})")
    except Exception as e:
        print(f"Error accessing repository: {str(e)}")
    
except Exception as e:
    print(f"GitHub API Error: {str(e)}")

# Test Agno GithubTools
print("\nTesting Agno GithubTools...")
try:
    github_tools = GithubTools(access_token=github_token)
    
    # Test get_repository
    try:
        repo_info = github_tools.get_repository(repo_name=repo_name)
        print(f"Repository info retrieved successfully: {repo_name}")
    except Exception as e:
        print(f"Error retrieving repository info: {str(e)}")
    
    # Test get_directory_content
    try:
        dir_content = github_tools.get_directory_content(repo_name=repo_name, path="")
        print(f"Directory content retrieved successfully: {len(dir_content)} items")
    except Exception as e:
        print(f"Error retrieving directory content: {str(e)}")
        
except Exception as e:
    print(f"GithubTools Error: {str(e)}")

# Test GitHub Agent
print("\nTesting GitHub Agent...")
try:
    github_agent = get_github_agent()
    
    # Test simple query
    query = f"List the top-level directories in the repository {repo_name}"
    print(f"Running query: {query}")
    
    response = github_agent.run(query)
    print(f"Agent response: {response.content[:200]}...")
    
    if response.tools:
        print(f"Tool calls: {len(response.tools)}")
        for tool in response.tools[:2]:  # Show first 2 tool calls
            print(f"- {tool.get('tool_name')}: {tool.get('tool_args')}")
    
except Exception as e:
    print(f"GitHub Agent Error: {str(e)}")

print("\nDebug completed")