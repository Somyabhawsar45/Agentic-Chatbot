"""
Storage for users, conversations, messages and PDF indexes.

Two backends, same functions:
  * DATABASE_URL set (postgres://...)  -> Postgres, e.g. a free Supabase project.
    Data survives Streamlit Cloud restarts/redeploys.
  * DATABASE_URL empty                 -> local SQLite file `chat_history.db`.

SQL is written once with `?` placeholders; `_run` converts them to `%s` for Postgres.
"""
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.path.join(os.getcwd(), "chat_history.db")

_pg_pool = None
_pool_lock = threading.Lock()
_initialized = False


_pg_error = None  # set when DATABASE_URL is configured but the database can't be reached


def use_postgres() -> bool:
    if _pg_error:
        return False  # fell back to SQLite for this process (see _probe_postgres)
    return os.environ.get("DATABASE_URL", "").startswith(("postgres://", "postgresql://"))


def postgres_error():
    """Why Postgres was skipped (None if it's working or not configured)."""
    return _pg_error


def _probe_postgres() -> None:
    """
    Try ONE connection before building the pool. A connection pool retries forever in the
    background, and repeated bad logins make Supabase block the app (ECIRCUITBREAKER).
    On failure remember the reason and fall back to SQLite until the app restarts.
    """
    global _pg_error
    import psycopg
    try:
        with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=8):
            pass
    except Exception as e:
        first_line = str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__
        _pg_error = f"{type(e).__name__}: {first_line}"


def get_pg_pool():
    """Shared Postgres connection pool (also used by the LangGraph checkpointer)."""
    global _pg_pool
    with _pool_lock:
        if _pg_pool is None:
            from psycopg.rows import dict_row
            from psycopg_pool import ConnectionPool

            _pg_pool = ConnectionPool(
                conninfo=os.environ["DATABASE_URL"],
                min_size=1,
                max_size=5,
                # autocommit + dict rows are required by langgraph's PostgresSaver;
                # prepare_threshold=None keeps it working behind Supabase's pooler
                kwargs={"autocommit": True, "prepare_threshold": None, "row_factory": dict_row},
                open=True,
            )
        return _pg_pool


@contextmanager
def get_connection():
    """SQLite connection (local mode)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _run(sql: str, params=(), fetch: str = None):
    """Execute one statement. fetch: None | 'one' | 'all'. Rows come back as dicts."""
    if use_postgres():
        with get_pg_pool().connection() as conn:
            cur = conn.execute(sql.replace("?", "%s"), params)
            if fetch == "one":
                row = cur.fetchone()
                return dict(row) if row else None
            if fetch == "all":
                return [dict(r) for r in cur.fetchall()]
            return None

    with get_connection() as conn:
        cur = conn.execute(sql, params)
        if fetch == "one":
            row = cur.fetchone()
            return dict(row) if row else None
        if fetch == "all":
            return [dict(r) for r in cur.fetchall()]
        return None


def _now() -> str:
    return datetime.now().isoformat()


# ------------------------ SCHEMA ------------------------

_SQLITE_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        usecase TEXT NOT NULL,
        title TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS pdf_indexes (
        conversation_id INTEGER PRIMARY KEY,
        filename TEXT,
        data BLOB NOT NULL,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS user_memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS feedback (
        conversation_id INTEGER NOT NULL,
        message_index INTEGER NOT NULL,
        score INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (conversation_id, message_index)
    )""",
    """CREATE TABLE IF NOT EXISTS course_indexes (
        course_id TEXT PRIMARY KEY,
        data BLOB NOT NULL,
        chunk_count INTEGER NOT NULL,
        updated_at TEXT NOT NULL
    )""",
]

_POSTGRES_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS conversations (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        usecase TEXT NOT NULL,
        title TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS messages (
        id SERIAL PRIMARY KEY,
        conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS pdf_indexes (
        conversation_id INTEGER PRIMARY KEY,
        filename TEXT,
        data BYTEA NOT NULL,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS user_memories (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS feedback (
        conversation_id INTEGER NOT NULL,
        message_index INTEGER NOT NULL,
        score INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (conversation_id, message_index)
    )""",
    """CREATE TABLE IF NOT EXISTS course_indexes (
        course_id TEXT PRIMARY KEY,
        data BYTEA NOT NULL,
        chunk_count INTEGER NOT NULL,
        updated_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_memories_user ON user_memories(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id)",
    "CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id, usecase)",
]


def init_db():
    """Create tables if they don't exist. Runs once per process (cheap to call on every rerun)."""
    global _initialized
    if _initialized:
        return
    if use_postgres():
        _probe_postgres()
    for stmt in (_POSTGRES_SCHEMA if use_postgres() else _SQLITE_SCHEMA):
        _run(stmt)
    _initialized = True


# ------------------------ USERS ------------------------

def create_user(username: str, name: str, email: str, password_hash: str) -> int:
    row = _run(
        "INSERT INTO users (username, name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?) RETURNING id",
        (username, name, email, password_hash, _now()),
        fetch="one",
    )
    return row["id"]


def get_user_by_username(username: str):
    return _run("SELECT * FROM users WHERE username = ?", (username,), fetch="one")


def username_exists(username: str) -> bool:
    return get_user_by_username(username) is not None


def email_exists(email: str) -> bool:
    return _run("SELECT 1 AS found FROM users WHERE email = ?", (email,), fetch="one") is not None


# --------------------- CONVERSATIONS ---------------------

def create_conversation(user_id: int, usecase: str, title: str) -> int:
    row = _run(
        "INSERT INTO conversations (user_id, usecase, title, created_at) VALUES (?, ?, ?, ?) RETURNING id",
        (user_id, usecase, title, _now()),
        fetch="one",
    )
    return row["id"]


def add_message(conversation_id: int, role: str, content: str):
    _run(
        "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (conversation_id, role, content, _now()),
    )


def get_conversations(user_id: int, usecase: str):
    """Return list of conversations for a user+usecase, newest first."""
    return _run(
        "SELECT id, title, created_at FROM conversations WHERE user_id = ? AND usecase = ? ORDER BY id DESC",
        (user_id, usecase),
        fetch="all",
    )


def get_messages(conversation_id: int):
    rows = _run(
        "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id ASC",
        (conversation_id,),
        fetch="all",
    )
    return [(r["role"], r["content"]) for r in rows]


def delete_conversation(conversation_id: int):
    _run("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
    _run("DELETE FROM pdf_indexes WHERE conversation_id = ?", (conversation_id,))
    _run("DELETE FROM feedback WHERE conversation_id = ?", (conversation_id,))
    _run("DELETE FROM conversations WHERE id = ?", (conversation_id,))


def count_user_messages_today(user_id: int) -> int:
    """How many messages this user sent today (for the built-in-key daily limit)."""
    today = datetime.now().date().isoformat()  # ISO strings compare correctly as text
    row = _run(
        """SELECT COUNT(*) AS n FROM messages m
           JOIN conversations c ON m.conversation_id = c.id
           WHERE c.user_id = ? AND m.role = 'user' AND m.created_at >= ?""",
        (user_id, today),
        fetch="one",
    )
    return int(row["n"]) if row else 0


def make_title(first_message: str, word_limit: int = 6) -> str:
    words = first_message.strip().split()
    title = " ".join(words[:word_limit])
    if len(words) > word_limit:
        title += "…"
    return title or "New Conversation"


# ------------------------ PDF INDEXES ------------------------
# The FAISS index of each conversation's PDF is stored in the database (as bytes),
# so "Chat with PDF" keeps working after the app restarts.

def save_pdf_index(conversation_id: int, filename: str, data: bytes):
    _run(
        """INSERT INTO pdf_indexes (conversation_id, filename, data, created_at) VALUES (?, ?, ?, ?)
           ON CONFLICT (conversation_id) DO UPDATE SET filename = excluded.filename,
           data = excluded.data, created_at = excluded.created_at""",
        (conversation_id, filename, data, _now()),
    )


def get_pdf_index(conversation_id: int):
    row = _run("SELECT data FROM pdf_indexes WHERE conversation_id = ?", (conversation_id,), fetch="one")
    return bytes(row["data"]) if row else None


def has_pdf_index(conversation_id: int) -> bool:
    return _run(
        "SELECT 1 AS found FROM pdf_indexes WHERE conversation_id = ?", (conversation_id,), fetch="one"
    ) is not None


def get_pdf_filename(conversation_id):
    if conversation_id is None:
        return None
    row = _run("SELECT filename FROM pdf_indexes WHERE conversation_id = ?", (conversation_id,), fetch="one")
    return row["filename"] if row else None


# ------------------------ COURSE INDEXES ------------------------
# FAISS index for each Scholr course (built by the FastAPI /index-course endpoint).
# Stored in the database, not on disk: free hosts wipe the disk on every restart or
# sleep, which used to silently erase every course's index. One row per course;
# re-indexing replaces the row, so content is never duplicated.
# init_db() is called here because the FastAPI process doesn't call it at startup.

def save_course_index(course_id: str, data: bytes, chunk_count: int):
    init_db()
    _run(
        """INSERT INTO course_indexes (course_id, data, chunk_count, updated_at) VALUES (?, ?, ?, ?)
           ON CONFLICT (course_id) DO UPDATE SET data = excluded.data,
           chunk_count = excluded.chunk_count, updated_at = excluded.updated_at""",
        (str(course_id), data, chunk_count, _now()),
    )


def get_course_index(course_id: str):
    init_db()
    row = _run("SELECT data FROM course_indexes WHERE course_id = ?", (str(course_id),), fetch="one")
    return bytes(row["data"]) if row else None


def has_course_index(course_id: str) -> bool:
    init_db()
    return _run(
        "SELECT 1 AS found FROM course_indexes WHERE course_id = ?", (str(course_id),), fetch="one"
    ) is not None


def delete_course_index(course_id: str):
    init_db()
    _run("DELETE FROM course_indexes WHERE course_id = ?", (str(course_id),))


def rename_conversation(conversation_id: int, title: str):
    _run("UPDATE conversations SET title = ? WHERE id = ?", (title.strip() or "Untitled", conversation_id))


# ------------------------ LONG-TERM MEMORY ------------------------
# Facts the Netra Agent learns about a user ("Name is Somya", "Prefers short answers").
# Unlike the checkpointer (memory of ONE conversation), these are shared by ALL of
# the user's conversations.

MAX_MEMORIES_PER_USER = 50


def add_memory(user_id: int, content: str) -> bool:
    """Save a fact. Returns False if it's empty or already known (case-insensitive)."""
    content = " ".join((content or "").split())
    if not content:
        return False
    existing = {m["content"].lower() for m in get_memories(user_id)}
    if content.lower() in existing:
        return False
    _run(
        "INSERT INTO user_memories (user_id, content, created_at) VALUES (?, ?, ?)",
        (user_id, content[:300], _now()),
    )
    # keep the store small: drop the oldest facts beyond the cap
    rows = _run("SELECT id FROM user_memories WHERE user_id = ? ORDER BY id DESC", (user_id,), fetch="all")
    for row in rows[MAX_MEMORIES_PER_USER:]:
        _run("DELETE FROM user_memories WHERE id = ?", (row["id"],))
    return True


def get_memories(user_id: int):
    """Oldest first: [{"id", "content", "created_at"}]."""
    if user_id is None:
        return []
    return _run(
        "SELECT id, content, created_at FROM user_memories WHERE user_id = ? ORDER BY id ASC",
        (user_id,),
        fetch="all",
    )


def delete_memory(user_id: int, memory_id: int):
    _run("DELETE FROM user_memories WHERE id = ? AND user_id = ?", (memory_id, user_id))


def clear_memories(user_id: int):
    _run("DELETE FROM user_memories WHERE user_id = ?", (user_id,))


# ------------------------ FEEDBACK ------------------------

def save_feedback(conversation_id: int, message_index: int, score: int):
    """score: 1 = thumbs up, 0 = thumbs down (one rating per answer, last click wins)."""
    _run(
        """INSERT INTO feedback (conversation_id, message_index, score, created_at) VALUES (?, ?, ?, ?)
           ON CONFLICT (conversation_id, message_index) DO UPDATE SET score = excluded.score,
           created_at = excluded.created_at""",
        (conversation_id, message_index, score, _now()),
    )


def get_feedback(conversation_id: int) -> dict:
    """{message_index: score} for one conversation."""
    if conversation_id is None:
        return {}
    rows = _run("SELECT message_index, score FROM feedback WHERE conversation_id = ?", (conversation_id,), fetch="all")
    return {r["message_index"]: r["score"] for r in rows}
