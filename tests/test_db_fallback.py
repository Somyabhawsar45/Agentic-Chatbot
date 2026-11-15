"""A bad DATABASE_URL must not crash or hammer the database: fall back to SQLite once."""
import psycopg

from src.langgraphagenticai.database import db_utils


def test_bad_database_url_falls_back_to_sqlite(monkeypatch):
    attempts = []

    def failing_connect(*args, **kwargs):
        attempts.append(1)
        raise psycopg.OperationalError("password authentication failed for user \"postgres\"")

    monkeypatch.setenv("DATABASE_URL", "postgresql://user:wrong@localhost:5432/db")
    monkeypatch.setattr(db_utils, "_initialized", False)
    monkeypatch.setattr(psycopg, "connect", failing_connect)

    db_utils.init_db()
    db_utils.init_db()  # second call must not try again

    assert len(attempts) == 1
    assert "password authentication failed" in db_utils.postgres_error()
    assert db_utils.use_postgres() is False

    # the app still works on SQLite
    user_id = db_utils.create_user("fallback", "Fall Back", "fb@example.com", "hash")
    assert db_utils.get_user_by_username("fallback")["id"] == user_id
