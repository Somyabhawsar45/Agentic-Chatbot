import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.getcwd(), "chat_history.db")


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist. Call once on app startup."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usecase TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)


def create_conversation(usecase: str, title: str) -> int:
    """Create a new conversation row, return its id."""
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO conversations (usecase, title, created_at) VALUES (?, ?, ?)",
            (usecase, title, datetime.now().isoformat())
        )
        return cur.lastrowid


def add_message(conversation_id: int, role: str, content: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (conversation_id, role, content, datetime.now().isoformat())
        )


def get_conversations(usecase: str):
    """Return list of conversations for a usecase, newest first."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at FROM conversations WHERE usecase = ? ORDER BY id DESC",
            (usecase,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_messages(conversation_id: int):
    """Return list of (role, content) tuples for a conversation, in order."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id ASC",
            (conversation_id,)
        ).fetchall()
        return [(r["role"], r["content"]) for r in rows]


def delete_conversation(conversation_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))


def make_title(first_message: str, word_limit: int = 6) -> str:
    words = first_message.strip().split()
    title = " ".join(words[:word_limit])
    if len(words) > word_limit:
        title += "…"
    return title or "New Conversation"