"""
The FastAPI endpoints Scholr calls: /api/v1/index-course and /api/v1/course-doubt.
No real Groq or embedding calls — both are replaced with fakes.
"""
import pytest
from fastapi.testclient import TestClient
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.messages import AIMessage

from src.langgraphagenticai.api import routes
from src.langgraphagenticai.api.main import app
from src.langgraphagenticai.rag import pdf_rag_utils

COURSE_ID = "665f1c2ab4d1f2a9c8e7b123"


class RecordingLLM:
    def __init__(self):
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return AIMessage(content="A closure remembers its outer variables.")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(pdf_rag_utils, "get_embeddings", lambda: DeterministicFakeEmbedding(size=64))
    monkeypatch.setattr(pdf_rag_utils, "INDEX_ROOT", str(tmp_path / "pdf_indexes"))
    llm = RecordingLLM()
    monkeypatch.setattr(routes, "get_llm", lambda: llm)
    test_client = TestClient(app)
    test_client.llm = llm
    return test_client


def test_index_then_ask_uses_course_content(client):
    res = client.post("/api/v1/index-course", json={
        "course_id": COURSE_ID, "content": "A closure is a function that remembers its outer variables.",
    })
    assert res.status_code == 200
    assert res.json()["success"] is True

    pdf_rag_utils._cache.clear()  # answer must come from the database, as after a restart
    res = client.post("/api/v1/course-doubt", json={"question": "What is a closure?", "session_id": COURSE_ID})
    assert res.status_code == 200
    assert res.json()["answer"] == "A closure remembers its outer variables."
    assert "remembers its outer variables" in client.llm.prompts[0]


def test_reindex_replaces_content_seen_by_doubts(client):
    client.post("/api/v1/index-course", json={"course_id": COURSE_ID, "content": "Old: var hoisting."})
    client.post("/api/v1/index-course", json={"course_id": COURSE_ID, "content": "New: async await."})
    client.post("/api/v1/course-doubt", json={"question": "q", "session_id": COURSE_ID})
    prompt = client.llm.prompts[-1]
    assert "New: async await." in prompt
    assert "Old: var hoisting." not in prompt


def test_empty_content_is_a_400_not_a_crash(client):
    res = client.post("/api/v1/index-course", json={"course_id": COURSE_ID, "content": "   "})
    assert res.status_code == 400


def test_unindexed_course_gets_a_clear_message_without_calling_the_llm(client):
    res = client.post("/api/v1/course-doubt", json={"question": "q", "session_id": "000000000000000000000000"})
    assert res.status_code == 200
    assert "don't have course content" in res.json()["answer"]
    assert client.llm.prompts == []


def test_api_model_is_configurable(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("NETRA_API_MODEL", "openai/gpt-oss-120b")
    assert routes.get_llm().model_name == "openai/gpt-oss-120b"
    monkeypatch.delenv("NETRA_API_MODEL")
    assert routes.get_llm().model_name == "openai/gpt-oss-20b"
