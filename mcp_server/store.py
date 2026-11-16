"""
Storage and search behind the Netra MCP server.

Deliberately free of any MCP imports so it can be unit-tested directly:
  * DocumentStore - PDFs in one folder -> page-aware FAISS indexes -> passages with page numbers
  * MemoryStore   - small JSON file of long-term facts
  * WebSearch     - Tavily web search (key from TAVILY_API_KEY)

Safety rules enforced here (the server exposes these to an LLM-driven client, so inputs are untrusted):
  * documents are addressed by plain file name only - no paths, no '..', no hidden files, PDFs only
  * size / length / result-count limits on everything
  * errors are NetraError with a short message that never contains absolute paths or keys
"""
import hashlib
import json
import os
import re
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

MAX_PDF_BYTES = 25 * 1024 * 1024
MAX_QUERY_CHARS = 500
MAX_PASSAGE_CHARS = 1500
MAX_RESULTS = 10
MAX_FACT_CHARS = 300
MAX_MEMORIES = 200
INDEX_DIRNAME = ".index"
MEMORY_FILENAME = ".netra-memory.json"


class NetraError(ValueError):
    """A problem the caller can fix (bad name, missing key, ...). Safe to show to the client."""


def default_docs_dir() -> Path:
    return Path(os.environ.get("NETRA_DOCS_DIR") or (Path.home() / "netra-docs"))


def _clean_query(query) -> str:
    if not isinstance(query, str) or not query.strip():
        raise NetraError("query must be a non-empty string.")
    return query.strip()[:MAX_QUERY_CHARS]


def _clamp(value, low: int, high: int, default: int) -> int:
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return default


# ====================================================================== documents

class DocumentStore:
    def __init__(self, docs_dir=None, embeddings=None, embeddings_label: str = None):
        """`embeddings` may be an Embeddings object; by default Netra's configured provider is used."""
        self.docs_dir = Path(docs_dir) if docs_dir else default_docs_dir()
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self._embeddings = embeddings
        self._label = embeddings_label
        self._lock = threading.Lock()
        self._cache = {}   # (name, mtime_ns, size) -> FAISS

    # ---- helpers
    def _get_embeddings(self):
        if self._embeddings is None:
            from src.langgraphagenticai.rag import pdf_rag_utils
            self._embeddings = pdf_rag_utils.get_embeddings()
            self._label = pdf_rag_utils.embedding_label()
        return self._embeddings

    def _embedding_label(self) -> str:
        if self._label is None:
            self._label = type(self._embeddings).__name__ if self._embeddings is not None else "default"
        return self._label

    def resolve(self, filename) -> Path:
        """Validate a document name and return its path inside the docs folder."""
        if not isinstance(filename, str) or not filename.strip():
            raise NetraError("document must be a file name such as 'report.pdf'.")
        name = filename.strip()
        if name != Path(name).name or "/" in name or "\\" in name or name.startswith("."):
            raise NetraError("document must be a plain file name inside the documents folder (no paths).")
        if not name.lower().endswith(".pdf"):
            raise NetraError("only .pdf documents are supported.")
        path = self.docs_dir / name
        if not path.is_file():
            raise NetraError(f"document '{name}' was not found. Use list_documents to see what is available.")
        if path.stat().st_size > MAX_PDF_BYTES:
            raise NetraError(f"document '{name}' is larger than {MAX_PDF_BYTES // (1024 * 1024)} MB.")
        return path

    def _index_dir(self, name: str) -> Path:
        # name -> stable folder (hash avoids odd characters and collisions)
        digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:12]
        return self.docs_dir / INDEX_DIRNAME / f"{Path(name).stem[:40]}-{digest}"

    def _fingerprint(self, path: Path) -> dict:
        stat = path.stat()
        return {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns, "embeddings": self._embedding_label()}

    def _read_meta(self, name: str):
        meta_path = self._index_dir(name) / "meta.json"
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def _is_fresh(self, path: Path) -> bool:
        meta = self._read_meta(path.name)
        if not meta or not (self._index_dir(path.name) / "index.faiss").exists():
            return False
        return all(meta.get(k) == v for k, v in self._fingerprint(path).items())

    # ---- public operations
    def list_documents(self) -> list:
        docs = []
        for path in sorted(self.docs_dir.glob("*.pdf"), key=lambda p: p.name.lower()):
            if path.name.startswith(".") or not path.is_file():
                continue
            fresh = self._is_fresh(path)
            meta = self._read_meta(path.name) if fresh else None
            docs.append({
                "name": path.name,
                "size_kb": round(path.stat().st_size / 1024, 1),
                "indexed": fresh,
                "pages": meta.get("pages") if meta else None,
            })
        return docs

    def index_document(self, filename, force: bool = False) -> dict:
        """Build (or reuse) the page-aware index for one PDF."""
        from pypdf import PdfReader
        from langchain_community.vectorstores import FAISS
        from src.langgraphagenticai.rag import pdf_rag_utils

        path = self.resolve(filename)
        with self._lock:
            if not force and self._is_fresh(path):
                meta = self._read_meta(path.name)
                return {"document": path.name, "pages": meta["pages"], "chunks": meta["chunks"], "reused": True}

            try:
                pages = [(p.extract_text() or "") for p in PdfReader(str(path)).pages]
            except Exception:
                raise NetraError(f"could not read '{path.name}' as a PDF.") from None
            texts, metadatas = pdf_rag_utils.chunk_pages(pages, source=path.name)
            if not texts:
                raise NetraError(f"'{path.name}' has no extractable text (it may be a scanned, image-only PDF).")

            vectorstore = FAISS.from_texts(texts, self._get_embeddings(), metadatas=metadatas)
            index_dir = self._index_dir(path.name)
            index_dir.mkdir(parents=True, exist_ok=True)
            vectorstore.save_local(str(index_dir))
            meta = {**self._fingerprint(path), "pages": len(pages), "chunks": len(texts),
                    "indexed_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            (index_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
            self._cache = {k: v for k, v in self._cache.items() if k[0] != path.name}
            return {"document": path.name, "pages": len(pages), "chunks": len(texts), "reused": False,
                    "pages_without_text": [i for i, t in enumerate(pages, 1) if not t.strip()]}

    def _load(self, path: Path):
        from langchain_community.vectorstores import FAISS
        stat = path.stat()
        key = (path.name, stat.st_mtime_ns, stat.st_size, self._embedding_label())
        with self._lock:
            if key not in self._cache:
                # The index folder is created by index_document() above, in the user's own docs
                # folder. Loading uses pickle, so only point NETRA_DOCS_DIR at a folder you trust.
                self._cache[key] = FAISS.load_local(
                    str(self._index_dir(path.name)), self._get_embeddings(), allow_dangerous_deserialization=True)
            return self._cache[key]

    def search(self, filename, query, k: int = 4) -> list:
        """Top-k passages: [{page, text, distance}] (lower distance = closer match). Indexes on first use."""
        query = _clean_query(query)
        k = _clamp(k, 1, MAX_RESULTS, 4)
        path = self.resolve(filename)
        if not self._is_fresh(path):
            self.index_document(path.name)
        hits = self._load(path).similarity_search_with_score(query, k=k)
        return [
            {"page": doc.metadata.get("page"), "text": doc.page_content[:MAX_PASSAGE_CHARS], "distance": round(float(score), 4)}
            for doc, score in hits
        ]

    def read_page(self, filename, page) -> str:
        """Full text of one page (1-based)."""
        from pypdf import PdfReader
        path = self.resolve(filename)
        try:
            reader = PdfReader(str(path))
            total = len(reader.pages)
        except Exception:
            raise NetraError(f"could not read '{path.name}' as a PDF.") from None
        try:
            number = int(page)
        except (TypeError, ValueError):
            raise NetraError("page must be a whole number starting at 1.") from None
        if not 1 <= number <= total:
            raise NetraError(f"page must be between 1 and {total}.")
        return (reader.pages[number - 1].extract_text() or "").strip()[:20000]


# ====================================================================== memory

class MemoryStore:
    """Long-term facts the assistant should remember, kept in one small JSON file."""

    def __init__(self, path=None):
        self.path = Path(path) if path else default_docs_dir() / MEMORY_FILENAME
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _read(self) -> list:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, ValueError):
            return []

    def _write(self, items: list) -> None:
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)   # atomic: a crash can't leave a half-written file
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def list(self) -> list:
        with self._lock:
            return self._read()

    def add(self, fact) -> dict:
        if not isinstance(fact, str) or not fact.strip():
            raise NetraError("fact must be a non-empty sentence.")
        fact = re.sub(r"\s+", " ", fact).strip()
        if len(fact) > MAX_FACT_CHARS:
            raise NetraError(f"fact is too long (max {MAX_FACT_CHARS} characters). Save one short fact at a time.")
        with self._lock:
            items = self._read()
            for item in items:
                if item["fact"].lower() == fact.lower():
                    return {"saved": False, "reason": "already remembered", "id": item["id"], "fact": item["fact"]}
            if len(items) >= MAX_MEMORIES:
                raise NetraError(f"memory is full ({MAX_MEMORIES} facts). Forget some first.")
            entry = {"id": max((i["id"] for i in items), default=0) + 1, "fact": fact,
                     "created": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            self._write(items + [entry])
            return {"saved": True, **entry}

    def delete(self, memory_id) -> dict:
        try:
            memory_id = int(memory_id)
        except (TypeError, ValueError):
            raise NetraError("memory_id must be a whole number.") from None
        with self._lock:
            items = self._read()
            kept = [i for i in items if i["id"] != memory_id]
            if len(kept) == len(items):
                raise NetraError(f"no memory with id {memory_id}.")
            self._write(kept)
            return {"deleted": memory_id}


# ====================================================================== web

class WebSearch:
    """Tavily web search. `client` can be injected for tests."""

    def __init__(self, api_key=None, client=None):
        self._api_key = api_key
        self._client = client

    def search(self, query, max_results: int = 3) -> list:
        query = _clean_query(query)
        max_results = _clamp(max_results, 1, 5, 3)
        if self._client is None:
            key = self._api_key or os.environ.get("TAVILY_API_KEY")
            if not key:
                raise NetraError("web search is not configured: set TAVILY_API_KEY for the server.")
            from tavily import TavilyClient
            self._client = TavilyClient(api_key=key)
        try:
            results = self._client.search(query=query, max_results=max_results).get("results", [])
        except Exception as e:
            raise NetraError(f"web search failed ({type(e).__name__}).") from None
        return [
            {"title": r.get("title", ""), "url": r.get("url", ""), "content": (r.get("content") or "")[:600]}
            for r in results
        ]
