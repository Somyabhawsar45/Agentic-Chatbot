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
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                usecase TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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


# ------------------------ USERS ------------------------

def create_user(username: str, name: str, email: str, password_hash: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
            (username, name, email, password_hash, datetime.now().isoformat())
        )
        return cur.lastrowid


def get_user_by_username(username: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        return dict(row) if row else None


def get_all_users():
    """Used to build the credentials dict streamlit-authenticator needs."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM users").fetchall()
        return [dict(r) for r in rows]


def username_exists(username: str) -> bool:
    return get_user_by_username(username) is not None


def email_exists(email: str) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
        return row is not None


# --------------------- CONVERSATIONS ---------------------

def create_conversation(user_id: int, usecase: str, title: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO conversations (user_id, usecase, title, created_at) VALUES (?, ?, ?, ?)",
            (user_id, usecase, title, datetime.now().isoformat())
        )
        return cur.lastrowid


def add_message(conversation_id: int, role: str, content: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (conversation_id, role, content, datetime.now().isoformat())
        )


def get_conversations(user_id: int, usecase: str):
    """Return list of conversations for a user+usecase, newest first."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at FROM conversations WHERE user_id = ? AND usecase = ? ORDER BY id DESC",
            (user_id, usecase)
        ).fetchall()
        return [dict(r) for r in rows]


def get_messages(conversation_id: int):
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