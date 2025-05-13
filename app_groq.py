import os
import nest_asyncio
import streamlit as st
from agents import get_github_agent
from agno.agent import Agent
from agno.utils.log import logger
from dotenv import load_dotenv

load_dotenv() 
from utils import (
    CUSTOM_CSS,
    about_widget,
    add_message,
    display_tool_calls,
    sidebar_widget,
)

nest_asyncio.apply()
st.set_page_config(
    page_title="GitHub Repo Analyzer (Groq)",
    page_icon="👨‍💻",
    layout="wide",
)

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

def main() -> None:
    st.markdown("<h1 class='main-header'>👨‍💻 GitHub Repo Analyzer (Groq)</h1>", unsafe_allow_html=True)
    st.markdown("Analyze GitHub repositories using Groq LLMs")

    if "github_agent" not in st.session_state or st.session_state["github_agent"] is None:
        logger.info("---*--- Creating new Github agent (Groq) ---*---")
        github_agent = get_github_agent()
        st.session_state["github_agent"] = github_agent
        st.session_state["messages"] = []
        
        # Get GitHub token from environment
        github_token = os.getenv("GITHUB_ACCESS_TOKEN")
        if not github_token:
            st.error("GitHub token not found in environment! Please check your .env file.")
            return
            
        st.session_state["github_token"] = github_token
    else:
        github_agent = st.session_state["github_agent"]

    try:
        st.session_state["github_agent_session_id"] = github_agent.load_session()
    except Exception as e:
        st.warning(f"Could not create Agent session: {str(e)}")
        return

    if github_agent.memory is not None and not st.session_state.get("messages"):
        session_id = st.session_state.get("github_agent_session_id")
        agent_runs = github_agent.memory.get_runs(session_id)
        if agent_runs:
            st.session_state["messages"] = []
            for run_response in agent_runs:
                for msg in run_response.messages or []:
                    if msg.role in ["user", "assistant"] and msg.content is not None:
                        add_message(msg.role, msg.content, getattr(msg, "tool_calls", None))
        else:
            st.session_state["messages"] = []

    sidebar_widget()

    if prompt := st.chat_input("👋 Ask me about GitHub repositories!"):
        add_message("user", prompt)

    for message in st.session_state["messages"]:
        if message["role"] in ["user", "assistant"]:
            _content = message["content"]
            if _content is not None:
                with st.chat_message(message["role"]):
                    if "tool_calls" in message and message["tool_calls"]:
                        display_tool_calls(st.empty(), message["tool_calls"])
                    st.markdown(_content)

    last_message = st.session_state["messages"][-1] if st.session_state["messages"] else None
    if last_message and last_message.get("role") == "user":
        question = last_message["content"]
        with st.chat_message("assistant"):
            tool_calls_container = st.empty()
            resp_container = st.empty()
            with st.spinner("🤔 Thinking (Groq)..."):
                response = ""
                try:
                    run_response = github_agent.run(question, stream=True, stream_intermediate_steps=True)
                    for _resp_chunk in run_response:
                        if _resp_chunk.tools and len(_resp_chunk.tools) > 0:
                            display_tool_calls(tool_calls_container, _resp_chunk.tools)
                        if _resp_chunk.event == "RunResponse" and _resp_chunk.content is not None:
                            response += _resp_chunk.content
                            resp_container.markdown(response)

                    add_message("assistant", response, github_agent.run_response.tools)
                except Exception as e:
                    logger.exception(e)
                    error_message = f"Sorry, I encountered an error: {str(e)}"
                    add_message("assistant", error_message)
                    st.error(error_message)

    about_widget()

if __name__ == "__main__":
    main()