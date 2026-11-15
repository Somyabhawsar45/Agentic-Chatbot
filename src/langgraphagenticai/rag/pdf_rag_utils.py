"""
PDF RAG utilities: extract -> chunk (with page numbers) -> embed -> FAISS.

Each conversation's FAISS index is serialized and stored in the database
(db_utils.pdf_indexes), so PDF chats survive app restarts. A small in-memory
cache avoids re-loading the index on every question.
"""
import os
import threading
from collections import OrderedDict

from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.langgraphagenticai.database import db_utils

# Legacy on-disk indexes (older versions / the FastAPI course endpoints)
INDEX_ROOT = os.path.join(os.getcwd(), "pdf_indexes")

_embeddings_instance = None
_cache = OrderedDict()          # conversation_id -> FAISS vectorstore
_cache_lock = threading.Lock()
_CACHE_SIZE = 8


def get_embeddings():
    """Uses HuggingFace's hosted Inference Endpoint (current, non-deprecated API)
    instead of a local model, so no heavy torch/transformers download is needed."""
    global _embeddings_instance
    if _embeddings_instance is None:
        from langchain_huggingface import HuggingFaceEndpointEmbeddings
        _embeddings_instance = HuggingFaceEndpointEmbeddings(
            model="sentence-transformers/all-MiniLM-L6-v2",
            huggingfacehub_api_token=os.getenv("HUGGINGFACEHUB_API_TOKEN"),
        )
    return _embeddings_instance


def _splitter():
    return RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)


def extract_pages(file_path: str) -> list:
    """Text of each page (index 0 = page 1). Empty string for image-only pages."""
    reader = PdfReader(file_path)
    return [(page.extract_text() or "") for page in reader.pages]


def extract_text_from_pdf(file_path: str) -> str:
    return "\n".join(p for p in extract_pages(file_path) if p)


def chunk_text(text: str):
    return _splitter().split_text(text)


def chunk_pages(pages: list, source: str = "document.pdf"):
    """
    Split page by page so every chunk knows its page number (for citations).
    Returns (texts, metadatas).
    """
    splitter = _splitter()
    texts, metadatas = [], []
    for page_number, page_text in enumerate(pages, start=1):
        if not page_text.strip():
            continue
        for chunk in splitter.split_text(page_text):
            texts.append(chunk)
            metadatas.append({"page": page_number, "source": source})
    return texts, metadatas


def _cache_put(key, vectorstore):
    with _cache_lock:
        _cache[key] = vectorstore
        _cache.move_to_end(key)
        while len(_cache) > _CACHE_SIZE:
            _cache.popitem(last=False)


def build_index(file_path: str, conversation_id: int, filename: str = None) -> int:
    """
    Extract -> chunk per page -> embed -> FAISS -> save to the database.
    Returns the number of chunks indexed.
    """
    from langchain_community.vectorstores import FAISS

    filename = filename or os.path.basename(file_path)
    texts, metadatas = chunk_pages(extract_pages(file_path), source=filename)
    if not texts:
        raise ValueError("No extractable text found in this PDF (it may be scanned/image-only).")

    vectorstore = FAISS.from_texts(texts, get_embeddings(), metadatas=metadatas)
    db_utils.save_pdf_index(conversation_id, filename, vectorstore.serialize_to_bytes())
    _cache_put(str(conversation_id), vectorstore)
    return len(texts)


def _is_db_id(conversation_id) -> bool:
    return conversation_id is not None and str(conversation_id).isdigit()


def has_index(conversation_id) -> bool:
    """True if a PDF has been indexed for this conversation."""
    if conversation_id is None:
        return False
    if str(conversation_id) in _cache:
        return True
    if _is_db_id(conversation_id) and db_utils.has_pdf_index(int(conversation_id)):
        return True
    return os.path.exists(os.path.join(INDEX_ROOT, f"convo_{conversation_id}"))


def load_index(conversation_id):
    from langchain_community.vectorstores import FAISS

    key = str(conversation_id)
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]

    vectorstore = None
    if _is_db_id(conversation_id):
        data = db_utils.get_pdf_index(int(conversation_id))
        if data:
            # bytes were produced by our own build_index (trusted source)
            vectorstore = FAISS.deserialize_from_bytes(
                data, get_embeddings(), allow_dangerous_deserialization=True
            )
    if vectorstore is None:
        index_path = os.path.join(INDEX_ROOT, f"convo_{conversation_id}")
        if os.path.exists(index_path):
            vectorstore = FAISS.load_local(index_path, get_embeddings(), allow_dangerous_deserialization=True)

    if vectorstore is not None:
        _cache_put(key, vectorstore)
    return vectorstore


def retrieve(conversation_id, query: str, k: int = 4) -> list:
    """Top-k passages as dicts: {"text", "page", "source"} (page is None for old indexes)."""
    vectorstore = load_index(conversation_id)
    if vectorstore is None:
        return []
    docs = vectorstore.similarity_search(query, k=k)
    return [
        {"text": d.page_content, "page": d.metadata.get("page"), "source": d.metadata.get("source")}
        for d in docs
    ]


def retrieve_chunks(conversation_id, query: str, k: int = 4):
    """Plain-text passages (used by the FastAPI endpoints)."""
    return [r["text"] for r in retrieve(conversation_id, query, k=k)]


def format_passages(passages: list) -> str:
    """Context block for the LLM, each passage labelled with its page."""
    blocks = []
    for i, p in enumerate(passages, 1):
        label = f"Passage {i}" + (f", page {p['page']}" if p.get("page") else "")
        blocks.append(f"[{label}]\n{p['text']}")
    return "\n\n---\n\n".join(blocks)


def build_index_from_text(text: str, course_id: str) -> str:
    """
    Chunk -> embed -> save FAISS index for a course (text-based, not PDF).
    Used by the FastAPI /index-course endpoint; stored on disk.
    """
    from langchain_community.vectorstores import FAISS

    if not text.strip():
        raise ValueError("No content provided to index for this course.")

    os.makedirs(INDEX_ROOT, exist_ok=True)
    vectorstore = FAISS.from_texts(chunk_text(text), get_embeddings())
    index_path = os.path.join(INDEX_ROOT, f"convo_{course_id}")
    vectorstore.save_local(index_path)
    with _cache_lock:
        _cache.pop(str(course_id), None)
    return index_path
