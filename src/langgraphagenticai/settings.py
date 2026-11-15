"""
One place to load configuration.

Locally, values come from `.env`. On Streamlit Cloud they come from App settings ->
Secrets. Both are copied into `os.environ` so every module (and LangChain's
LangSmith tracing, which only reads env vars) sees the same values.
"""
import os

from dotenv import load_dotenv

KNOWN_KEYS = [
    "GROQ_API_KEY",
    "TAVILY_API_KEY",
    "HUGGINGFACEHUB_API_TOKEN",
    "DATABASE_URL",            # Postgres (e.g. Supabase). Empty -> local SQLite file
    "DAILY_MESSAGE_LIMIT",     # messages/user/day when using the built-in Groq key
    "LANGSMITH_TRACING",
    "LANGSMITH_API_KEY",
    "LANGSMITH_PROJECT",
    "LANGSMITH_ENDPOINT",
]


def load_settings() -> None:
    """Call once, first thing in app.py, before importing the rest of the app."""
    load_dotenv()
    try:
        import streamlit as st
        for key in KNOWN_KEYS:
            if not os.environ.get(key) and key in st.secrets:
                os.environ[key] = str(st.secrets[key])
    except Exception:
        pass  # no secrets.toml (normal for local runs)


def daily_message_limit() -> int:
    try:
        return int(os.environ.get("DAILY_MESSAGE_LIMIT", "30"))
    except ValueError:
        return 30


def tracing_enabled() -> bool:
    return os.environ.get("LANGSMITH_TRACING", "").lower() == "true" and bool(os.environ.get("LANGSMITH_API_KEY"))
