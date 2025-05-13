import os
from dotenv import load_dotenv
from agno.models.groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env file.")

llm_groq = Groq(
    id="meta-llama/llama-4-maverick-17b-128e-instruct",
    api_key=GROQ_API_KEY,
    temperature=0.5
)

llm_qwen_reasoning = Groq(
    id="qwen-qwq-32b",
    api_key=GROQ_API_KEY,
    temperature=0.3
)
