"""
Course indexes for Scholr's "Ask a Doubt": stored in the database so they survive
restarts, and replaced (never appended) when a course is re-indexed.
"""
import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from src.langgraphagenticai.database import db_utils
from src.langgraphagenticai.rag import pdf_rag_utils

COURSE_ID = "665f1c2ab4d1f2a9c8e7b123"  # MongoDB ObjectId, as Scholr sends it


@pytest.fixture(autouse=True)
def offline_embeddings(tmp_path, monkeypatch):
    # Same text -> same vector, so querying with a chunk's exact text finds that chunk
    monkeypatch.setattr(pdf_rag_utils, "get_embeddings", lambda: DeterministicFakeEmbedding(size=64))
    monkeypatch.setattr(pdf_rag_utils, "INDEX_ROOT", str(tmp_path / "pdf_indexes"))


def simulate_restart():
    """A restart (or a host wiping its disk) loses the in-memory cache."""
    pdf_rag_utils._cache.clear()


def test_index_is_stored_in_the_database():
    pdf_rag_utils.build_index_from_text("Closures remember outer variables.", COURSE_ID)
    assert db_utils.has_course_index(COURSE_ID)
    assert db_utils.get_course_index(COURSE_ID)


def test_index_survives_a_restart():
    pdf_rag_utils.build_index_from_text("Closures remember outer variables.", COURSE_ID)
    simulate_restart()
    assert pdf_rag_utils.has_index(COURSE_ID)
    assert pdf_rag_utils.retrieve_chunks(COURSE_ID, "Closures remember outer variables.") == [
        "Closures remember outer variables."
    ]


def test_reindexing_replaces_old_content():
    pdf_rag_utils.build_index_from_text("Old lecture about var hoisting.", COURSE_ID)
    pdf_rag_utils.build_index_from_text("New lecture about async await.", COURSE_ID)
    simulate_restart()
    passages = pdf_rag_utils.retrieve_chunks(COURSE_ID, "anything", k=10)
    assert passages == ["New lecture about async await."]


def test_courses_are_isolated():
    pdf_rag_utils.build_index_from_text("JavaScript course text.", COURSE_ID)
    pdf_rag_utils.build_index_from_text("Python course text.", "665f1c2ab4d1f2a9c8e7b999")
    simulate_restart()
    assert pdf_rag_utils.retrieve_chunks(COURSE_ID, "x", k=10) == ["JavaScript course text."]


def test_old_disk_index_is_moved_into_the_database(tmp_path):
    from langchain_community.vectorstores import FAISS

    # An index saved the old way, as files on disk
    legacy = FAISS.from_texts(["Legacy course content."], DeterministicFakeEmbedding(size=64))
    legacy.save_local(str(tmp_path / "pdf_indexes" / f"convo_{COURSE_ID}"))
    assert not db_utils.has_course_index(COURSE_ID)

    assert pdf_rag_utils.retrieve_chunks(COURSE_ID, "Legacy course content.") == ["Legacy course content."]
    assert db_utils.has_course_index(COURSE_ID)  # copied before the disk can be wiped


def test_reindexing_removes_the_old_disk_copy(tmp_path):
    from langchain_community.vectorstores import FAISS

    legacy_dir = tmp_path / "pdf_indexes" / f"convo_{COURSE_ID}"
    FAISS.from_texts(["Stale."], DeterministicFakeEmbedding(size=64)).save_local(str(legacy_dir))
    pdf_rag_utils.build_index_from_text("Fresh content.", COURSE_ID)
    assert not legacy_dir.exists()
    simulate_restart()
    assert pdf_rag_utils.retrieve_chunks(COURSE_ID, "x", k=10) == ["Fresh content."]


def test_empty_content_is_rejected():
    with pytest.raises(ValueError):
        pdf_rag_utils.build_index_from_text("   ", COURSE_ID)


def test_pdf_chat_indexes_are_unaffected():
    # Numeric ids are Netra's own PDF conversations and still use pdf_indexes
    assert not pdf_rag_utils.has_index(42)
    assert pdf_rag_utils.retrieve(42, "anything") == []
