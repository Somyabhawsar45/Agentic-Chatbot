"""
Embedding provider choice and the PDF indexing path (offline: fake embeddings).
Why this exists: the hosted HuggingFace embeddings ran out of free credits and broke
Chat with PDF, so local embeddings are now the default.
"""
import importlib.util

import langchain_community.embeddings as lc_embeddings
import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from mcp_server.simple_pdf import write_pdf
from src.langgraphagenticai.database import db_utils
from src.langgraphagenticai.rag import pdf_rag_utils


@pytest.fixture(autouse=True)
def fresh_embeddings(monkeypatch):
    monkeypatch.setattr(pdf_rag_utils, "_embeddings_instance", None)
    monkeypatch.delenv("EMBEDDINGS_PROVIDER", raising=False)


# ---------------- which provider is used ----------------

def test_explicit_provider_wins(monkeypatch):
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", " HuggingFace ")
    assert pdf_rag_utils.embedding_provider() == "huggingface"
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "fastembed")
    assert pdf_rag_utils.embedding_provider() == "fastembed"


def test_local_embeddings_are_the_default_when_installed(monkeypatch):
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: object() if name == "fastembed" else None)
    assert pdf_rag_utils.embedding_provider() == "fastembed"


def test_falls_back_to_hosted_embeddings_when_fastembed_is_missing(monkeypatch):
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    assert pdf_rag_utils.embedding_provider() == "huggingface"


def test_label_names_provider_and_model(monkeypatch):
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "fastembed")
    assert pdf_rag_utils.embedding_label() == "fastembed:sentence-transformers/all-MiniLM-L6-v2"


def test_local_embeddings_use_the_memory_safe_settings(monkeypatch):
    """batch 8 / 256 tokens: measured at ~0.33 GB peak vs ~1.8 GB with the library defaults."""
    captured = {}

    class StubFastEmbed:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "fastembed")
    monkeypatch.setattr(lc_embeddings, "FastEmbedEmbeddings", StubFastEmbed, raising=False)
    embeddings = pdf_rag_utils.get_embeddings()
    assert isinstance(embeddings, StubFastEmbed)
    assert captured == {"model_name": "sentence-transformers/all-MiniLM-L6-v2", "batch_size": 8, "max_length": 256}
    assert pdf_rag_utils.get_embeddings() is embeddings        # one shared instance


# ---------------- indexing a real PDF through the app's own code ----------------

def _use_fake_embeddings(monkeypatch):
    monkeypatch.setattr(pdf_rag_utils, "_embeddings_instance", DeterministicFakeEmbedding(size=32))


def test_upload_flow_indexes_saves_to_db_and_reloads_after_restart(tmp_path, monkeypatch):
    _use_fake_embeddings(monkeypatch)
    pages = ["Meridian was founded in 2014 in Pune.", "Revenue was INR 4,820 crore.", "Audit chair is Meera Iyer."]
    pdf = write_pdf(tmp_path / "report.pdf", pages)
    user_id = db_utils.create_user("tester", "Tester", "t@example.com", "hash")
    convo = db_utils.create_conversation(user_id, "Netra Agent", "report")

    assert pdf_rag_utils.build_index(str(pdf), convo, filename="report.pdf") >= 3
    assert pdf_rag_utils.has_index(convo)

    pdf_rag_utils._cache.clear()                       # simulate an app restart: only the DB copy is left
    assert pdf_rag_utils.has_index(convo)
    hits = pdf_rag_utils.retrieve(convo, pages[2], k=2)
    assert hits[0]["page"] == 3 and "Meera Iyer" in hits[0]["text"] and hits[0]["source"] == "report.pdf"


def test_too_large_pdf_is_refused_with_a_clear_message(tmp_path, monkeypatch):
    _use_fake_embeddings(monkeypatch)
    pdf = write_pdf(tmp_path / "big.pdf", ["word " * 150] * 4)
    monkeypatch.setattr(pdf_rag_utils, "MAX_CHUNKS", 2)
    with pytest.raises(ValueError, match="too large to index"):
        pdf_rag_utils.build_index(str(pdf), 1)


def test_bad_chunk_limit_setting_does_not_crash(monkeypatch):
    monkeypatch.setenv("MAX_PDF_CHUNKS", "lots")
    assert pdf_rag_utils._max_chunks() == 1500
    monkeypatch.setenv("MAX_PDF_CHUNKS", "0")
    assert pdf_rag_utils._max_chunks() == 1
