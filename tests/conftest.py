"""
Shared test setup. Tests never call real APIs (Groq/Tavily/HuggingFace) and use a
fresh temporary SQLite database, so they run offline in seconds (also in CI).
"""
import pytest

from src.langgraphagenticai.database import db_utils
from src.langgraphagenticai.memory import checkpointer
from src.langgraphagenticai.rag import pdf_rag_utils


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(db_utils, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(db_utils, "_initialized", False)
    monkeypatch.setattr(checkpointer, "_checkpointer", None)
    pdf_rag_utils._cache.clear()
    db_utils.init_db()
    yield


class FakeLLM:
    """
    Stand-in for ChatGroq. `responder(messages, bound)` decides the reply, where
    `bound` describes the last bind_tools() call ({"tools": [...], **kwargs}).
    Every call is recorded in `calls` for assertions.
    """

    def __init__(self, responder):
        self.responder = responder
        self.calls = []
        self.bound = {}

    def bind_tools(self, tools, **kwargs):
        clone = FakeLLM(self.responder)
        clone.calls = self.calls          # share the call log
        clone.bound = {"tools": [t.name for t in tools], **kwargs}
        return clone

    def invoke(self, messages, *args, **kwargs):
        self.calls.append((messages, self.bound))
        return self.responder(messages, self.bound)


@pytest.fixture
def fake_llm_factory():
    return FakeLLM
