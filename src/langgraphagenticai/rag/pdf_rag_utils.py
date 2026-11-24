"""
PDF RAG utilities: extract -> chunk (with page numbers) -> embed -> FAISS.

Each conversation's FAISS index is serialized and stored in the database
(db_utils.pdf_indexes), so PDF chats survive app restarts. A small in-memory
cache avoids re-loading the index on every question.
"""
import importlib.util
import os
import threading
from collections import OrderedDict

from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.langgraphagenticai.database import db_utils

# Legacy on-disk indexes (older versions). Course indexes now live in the database;
# old on-disk ones are copied into it the first time they're loaded.
INDEX_ROOT = os.path.join(os.getcwd(), "pdf_indexes")

_embeddings_instance = None
_embeddings_lock = threading.Lock()
_warmup_started = False
_cache = OrderedDict()          # conversation_id -> FAISS vectorstore
_cache_lock = threading.Lock()
_CACHE_SIZE = 8


EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Local embedding settings, chosen by measurement (600 chunks of ~900 characters):
#   library default (batch 256, 512 tokens): peak 1.8 GB, 11 chunks/s
#   batch 8, 256 tokens (this setting):       peak 0.33 GB, 20 chunks/s (9.5 on one CPU core)
# 256 tokens is the model's own training limit, and our 1000-character chunks fit in it.
EMBED_BATCH_SIZE = 8
EMBED_MAX_TOKENS = 256

# Indexing runs synchronously on the (small, shared) app server. Refuse absurdly large PDFs
# instead of tying up the CPU for minutes; override with MAX_PDF_CHUNKS.
def _max_chunks() -> int:
    """Passages allowed per PDF (about 150-250 pages). Bigger documents could use up the small
    server's memory while embedding, so they get a clear "too large" message instead."""
    try:
        return max(1, int(os.getenv("MAX_PDF_CHUNKS", "500")))
    except ValueError:
        return 500


MAX_CHUNKS = _max_chunks()


def embedding_provider() -> str:
    """
    EMBEDDINGS_PROVIDER wins if set: 'fastembed' (free local ONNX, no API key) or
    'huggingface' (hosted Inference API: needs a token and available HF credits).
    Otherwise local embeddings are used when `fastembed` is installed, else the hosted API.
    """
    explicit = os.getenv("EMBEDDINGS_PROVIDER", "").strip().lower()
    if explicit:
        return explicit
    return "fastembed" if importlib.util.find_spec("fastembed") else "huggingface"


def embedding_label() -> str:
    return f"{embedding_provider()}:{EMBEDDING_MODEL}"


def get_embeddings():
    """
    Local (default when fastembed is installed): the MiniLM model run on CPU with ONNX. Free, no key,
    no hosted-API quota; the ~90 MB model is downloaded on first use and cached.
    Hosted (EMBEDDINGS_PROVIDER=huggingface, or fastembed missing): HuggingFace Inference API.
    Note: an index built with one provider should be queried with the same one.
    """
    with _embeddings_lock:       # one load even if several visitors arrive at once
        return _get_embeddings_locked()


def _get_embeddings_locked():
    global _embeddings_instance
    if _embeddings_instance is None:
        if embedding_provider() == "fastembed":
            from langchain_community.embeddings import FastEmbedEmbeddings
            # the Docker image downloads the model into FASTEMBED_CACHE_PATH at build time
            extra = {"cache_dir": os.environ["FASTEMBED_CACHE_PATH"]} if os.getenv("FASTEMBED_CACHE_PATH") else {}
            _embeddings_instance = FastEmbedEmbeddings(
                model_name=EMBEDDING_MODEL, batch_size=EMBED_BATCH_SIZE, max_length=EMBED_MAX_TOKENS, **extra,
            )
        else:
            from langchain_huggingface import HuggingFaceEndpointEmbeddings
            _embeddings_instance = HuggingFaceEndpointEmbeddings(
                model=EMBEDDING_MODEL,
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
    return build_index_from_pages(extract_pages(file_path), conversation_id,
                                  filename=filename or os.path.basename(file_path))


def build_index_from_pages(pages: list, conversation_id: int, filename: str) -> int:
    """Same as build_index, for text that is already split into pages (e.g. the built-in sample report)."""
    from langchain_community.vectorstores import FAISS

    texts, metadatas = chunk_pages(pages, source=filename)
    if not texts:
        raise ValueError("No extractable text found in this PDF (it may be scanned/image-only).")
    if len(texts) > MAX_CHUNKS:
        raise ValueError(
            f"This PDF is too large to index here ({len(texts)} passages, the limit is {MAX_CHUNKS}). "
            "Try a shorter document or split it."
        )

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
    if not _is_db_id(conversation_id) and db_utils.has_course_index(str(conversation_id)):
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
    else:
        # Scholr course ids (MongoDB ObjectIds) are not numeric
        data = db_utils.get_course_index(key)
    if data:
        # bytes were produced by our own build functions (trusted source)
        vectorstore = FAISS.deserialize_from_bytes(
            data, get_embeddings(), allow_dangerous_deserialization=True
        )

    if vectorstore is None:
        index_path = os.path.join(INDEX_ROOT, f"convo_{conversation_id}")
        if os.path.exists(index_path):
            vectorstore = FAISS.load_local(index_path, get_embeddings(), allow_dangerous_deserialization=True)
            if not _is_db_id(conversation_id):
                # Old course index on disk: copy it into the database before the next
                # restart wipes it
                db_utils.save_course_index(
                    key, vectorstore.serialize_to_bytes(), vectorstore.index.ntotal
                )

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
    Chunk -> embed -> save the FAISS index for a Scholr course (text, not PDF).
    Used by the FastAPI /index-course endpoint.

    Scholr sends the WHOLE course (description + every lecture's summary and
    transcript) each time anything changes, so this always REPLACES the course's
    previous index — content is never duplicated.

    The index is stored in the database (survives restarts on hosts that wipe the
    disk). Returns a short description of where it was stored.
    """
    from langchain_community.vectorstores import FAISS

    if not text.strip():
        raise ValueError("No content provided to index for this course.")

    key = str(course_id)
    chunks = chunk_text(text)
    if len(chunks) > MAX_CHUNKS:
        raise ValueError(
            f"This course is too large to index here ({len(chunks)} passages, the limit is {MAX_CHUNKS})."
        )
    vectorstore = FAISS.from_texts(chunks, get_embeddings())
    db_utils.save_course_index(key, vectorstore.serialize_to_bytes(), len(chunks))
    _cache_put(_COURSE_PREFIX + key, vectorstore)

    # Remove any old on-disk copy so it can never shadow the new index
    legacy_path = os.path.join(INDEX_ROOT, f"convo_{key}")
    if os.path.isdir(legacy_path):
        import shutil
        shutil.rmtree(legacy_path, ignore_errors=True)

    return f"course_indexes/{key} ({len(chunks)} chunks)"


# ------------------------ COURSES (Scholr API) ------------------------
# Course indexes live in their own table and their own cache keys. These functions never touch
# a user's PDF chat, even if someone sends an id that looks like a conversation number.
_COURSE_PREFIX = "course:"


def load_course_index(course_id: str):
    from langchain_community.vectorstores import FAISS

    key = _COURSE_PREFIX + str(course_id)
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
    data = db_utils.get_course_index(str(course_id))
    if not data:
        # an old course index saved on disk before courses moved to the database; load_index
        # handles that migration, and a non-numeric id can never reach a user's PDF chat there
        return None if str(course_id).isdigit() else load_index(course_id)
    # bytes were produced by build_index_from_text (trusted source)
    vectorstore = FAISS.deserialize_from_bytes(data, get_embeddings(), allow_dangerous_deserialization=True)
    _cache_put(key, vectorstore)
    return vectorstore


def retrieve_course_chunks(course_id: str, query: str, k: int = 4) -> list:
    """Plain-text passages from a course's index only (used by /course-doubt)."""
    vectorstore = load_course_index(course_id)
    if vectorstore is None:
        return []
    return [d.page_content for d in vectorstore.similarity_search(query, k=k)]


def warm_up_in_background() -> bool:
    """
    Load (and on a fresh server, download) the local embedding model in a background thread when
    the app starts, so the first visitor who tries a PDF doesn't wait ~30 s for a 90 MB download.
    Runs once per server process; never raises. Returns True if it started the warm-up now.
    """
    global _warmup_started
    if _warmup_started or embedding_provider() != "fastembed":
        return False
    _warmup_started = True

    def _warm():
        try:
            get_embeddings().embed_query("warm up")
        except Exception:
            pass   # the first real PDF will simply load it then

    threading.Thread(target=_warm, name="netra-embeddings-warmup", daemon=True).start()
    return True
