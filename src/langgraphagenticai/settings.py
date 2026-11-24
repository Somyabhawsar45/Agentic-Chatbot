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
    "GROQ_API_KEYS",           # optional extra built-in keys, comma-separated (used if the first is rate-limited)
    "GROQ_FALLBACK_MODELS",    # optional: models to fall back to on rate limits (default: the other gpt-oss model)
    "TAVILY_API_KEY",
    "TAVILY_API_KEYS",         # optional extra Tavily keys, comma-separated (used when one runs out)
    "HUGGINGFACEHUB_API_TOKEN",   # only for EMBEDDINGS_PROVIDER=huggingface
    "EMBEDDINGS_PROVIDER",        # fastembed (local, default if installed) | huggingface
    "MAX_PDF_CHUNKS",
    "DATABASE_URL",            # Postgres (e.g. Supabase). Empty -> local SQLite file
    "DB_POOL_SIZE",            # Postgres connections kept open (default 10)
    "DAILY_MESSAGE_LIMIT",     # messages/user/day when using the built-in Groq key
    "GUEST_MESSAGE_LIMIT",     # messages per guest account (try-without-sign-up)
    "GLOBAL_DAILY_LIMIT",      # messages/day for EVERYONE together on the built-in key (0 = no cap)
    "MAX_BACKGROUND_RUNS",     # Deep Research / News runs allowed at the same time
    "RESEARCH_DAILY_LIMIT",    # Deep Research runs/day per account on the built-in key (default 3)
    "GUEST_RESEARCH_LIMIT",    # Deep Research runs/day per guest (default 1)
    "GUESTS_PER_IP_PER_DAY",   # new guest sessions per network per day (default 10)
    "GUESTS_PER_DAY",          # new guest sessions per day for the whole app (default 300)
    "SIGNUPS_PER_IP_PER_HOUR", # new accounts per network per hour (default 10)
    "SIGNUPS_PER_DAY",         # new accounts per day for the whole app (default 150)
    "LOGIN_ATTEMPTS",          # wrong passwords before a username is locked for 15 minutes (default 5)
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


def _int_env(name: str, default: int, minimum: int = 0) -> int:
    try:
        return max(minimum, int(os.environ.get(name, str(default))))
    except ValueError:
        return default


def global_daily_limit() -> int:
    """Messages per day across all visitors on the app's built-in Groq key (0 = unlimited)."""
    return _int_env("GLOBAL_DAILY_LIMIT", 600)


def research_daily_limit(guest: bool = False) -> int:
    """Deep Research runs per day on the built-in keys. A run costs ~8 model calls and ~4 web
    searches (Tavily's free tier is small), so it gets its own, lower, limit."""
    return _int_env("GUEST_RESEARCH_LIMIT", 1) if guest else _int_env("RESEARCH_DAILY_LIMIT", 3)


def max_background_runs() -> int:
    """How many Deep Research / News runs may work at the same time; the rest wait in line."""
    return _int_env("MAX_BACKGROUND_RUNS", 3, minimum=1)


def guest_message_limit() -> int:
    try:
        return max(1, int(os.environ.get("GUEST_MESSAGE_LIMIT", "10")))
    except ValueError:
        return 10


def tracing_enabled() -> bool:
    return os.environ.get("LANGSMITH_TRACING", "").lower() == "true" and bool(os.environ.get("LANGSMITH_API_KEY"))
