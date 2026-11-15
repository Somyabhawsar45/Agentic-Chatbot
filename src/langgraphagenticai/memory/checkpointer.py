"""
LangGraph long-term memory (checkpointer).

The Netra Agent graph is compiled with a checkpointer. After every step LangGraph
saves the full graph state (all messages, including tool calls and tool results)
under a `thread_id`. On the next turn we send ONLY the new user message — LangGraph
loads the rest of the conversation from the checkpoint automatically.

Checkpoints live in the same database as users/conversations/messages:
  * Postgres (DATABASE_URL set)  -> PostgresSaver on the shared connection pool
  * local SQLite file            -> SqliteSaver
so the two can never get out of sync.
"""
import sqlite3
import threading

from src.langgraphagenticai.database import db_utils

_lock = threading.Lock()
_checkpointer = None


def get_checkpointer():
    """One shared saver per process (Streamlit reruns the script, not the process)."""
    global _checkpointer
    with _lock:
        if _checkpointer is None:
            if db_utils.use_postgres():
                from langgraph.checkpoint.postgres import PostgresSaver
                _checkpointer = PostgresSaver(db_utils.get_pg_pool())
            else:
                from langgraph.checkpoint.sqlite import SqliteSaver
                conn = sqlite3.connect(db_utils.DB_PATH, check_same_thread=False)
                _checkpointer = SqliteSaver(conn)
            _checkpointer.setup()  # creates checkpoint tables if missing
        return _checkpointer


def thread_id_for(conversation_id: int) -> str:
    return f"netra-convo-{conversation_id}"


def agent_config(conversation_id: int, user_id: int = None) -> dict:
    """
    RunnableConfig for one conversation: thread for short-term memory, the
    conversation id for the PDF tool, and the user id for long-term memory.
    """
    return {
        "configurable": {
            "thread_id": thread_id_for(conversation_id),
            "conversation_id": conversation_id,
            "user_id": user_id,
        },
        "recursion_limit": 16,  # hard safety net; tool_limits.py normally stops loops much earlier
    }


def delete_thread(conversation_id: int) -> None:
    """Forget the agent memory of a deleted conversation."""
    try:
        get_checkpointer().delete_thread(thread_id_for(conversation_id))
    except Exception:
        pass  # older checkpointer versions without delete_thread
