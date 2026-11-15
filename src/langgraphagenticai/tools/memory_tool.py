from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from src.langgraphagenticai.database import db_utils


@tool
def save_memory(fact: str, config: RunnableConfig) -> str:
    """Save a lasting fact about the user so you remember it in ALL future conversations.
    Use it when the user shares their name, job, goals, preferences or other stable
    personal details, or explicitly asks you to remember something.
    Write the fact as a short third-person sentence, e.g. "Name is Somya" or
    "Prefers concise bullet-point answers". Do not save temporary or trivial things."""
    # `config` is injected by LangGraph (hidden from the LLM)
    user_id = config.get("configurable", {}).get("user_id")
    if user_id is None:
        return "Memory is not available (no signed-in user)."
    if db_utils.add_memory(user_id, fact):
        return f"Saved to long-term memory: {fact}"
    return "Already remembered."
