"""
Tests for the Netra MCP server: the storage layer directly, then the whole server through a real
MCP client (in-process), so tool discovery, argument validation and error reporting are covered.
Offline: fake embeddings, fake web client.
"""
import asyncio
import json

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding
from mcp import Client

from mcp_server import store as store_module
from mcp_server.server import create_server
from mcp_server.simple_pdf import write_pdf
from mcp_server.store import DocumentStore, MemoryStore, NetraError, WebSearch

PAGES = [
    "Meridian Payments was founded in 2014 and is headquartered in Pune.",
    "Revenue for FY2025 was INR 4,820 crore, up 18% over FY2024.",
    "The board has nine directors. The audit committee is chaired by Meera Iyer.",
]


@pytest.fixture
def docs(tmp_path):
    write_pdf(tmp_path / "report.pdf", PAGES)
    return DocumentStore(tmp_path, embeddings=DeterministicFakeEmbedding(size=32), embeddings_label="fake")


@pytest.fixture
def memory(tmp_path):
    return MemoryStore(tmp_path / "memory.json")


class FakeTavily:
    def __init__(self, results=None, error=None):
        self.results, self.error, self.calls = results or [], error, []

    def search(self, query, max_results):
        self.calls.append((query, max_results))
        if self.error:
            raise self.error
        return {"results": self.results}


# ================================================================ test PDF writer

def test_pdf_writer_round_trips_through_a_real_pdf_reader(tmp_path):
    from pypdf import PdfReader
    path = write_pdf(tmp_path / "x.pdf", ["alpha (one) \\ two", "", "gamma"])
    pages = [p.extract_text() for p in PdfReader(str(path)).pages]
    assert pages[0].strip() == "alpha (one) \\ two"    # parentheses and backslash survive escaping
    assert pages[1].strip() == "" and pages[2].strip() == "gamma"


# ================================================================ documents

def test_list_index_search_flow(docs):
    assert docs.list_documents() == [{"name": "report.pdf", "size_kb": docs.list_documents()[0]["size_kb"],
                                      "indexed": False, "pages": None}]
    info = docs.index_document("report.pdf")
    assert info["pages"] == 3 and info["chunks"] >= 3 and info["reused"] is False
    assert docs.index_document("report.pdf")["reused"] is True
    assert docs.index_document("report.pdf", force=True)["reused"] is False
    assert docs.list_documents()[0]["indexed"] is True and docs.list_documents()[0]["pages"] == 3


def test_search_returns_page_numbers_and_ranks_exact_text_first(docs):
    # fake embeddings are hash-based, so an identical query vector must come back as the top hit
    hits = docs.search("report.pdf", PAGES[1], k=3)
    assert hits[0]["page"] == 2 and hits[0]["distance"] == pytest.approx(0, abs=1e-3)
    assert {h["page"] for h in hits} <= {1, 2, 3}
    assert all(set(h) == {"page", "text", "distance"} for h in hits)


def test_search_indexes_on_first_use_and_clamps_k(docs):
    hits = docs.search("report.pdf", "anything", k=1000)
    assert 1 <= len(hits) <= store_module.MAX_RESULTS
    assert docs.list_documents()[0]["indexed"] is True
    assert len(docs.search("report.pdf", "anything", k=0)) == 1       # k below 1 -> 1
    assert len(docs.search("report.pdf", "anything", k="abc")) >= 1   # junk k -> default


def test_changed_pdf_is_reindexed(docs, tmp_path):
    docs.index_document("report.pdf")
    write_pdf(tmp_path / "report.pdf", PAGES + ["A new fourth page about the dividend."])
    assert docs.list_documents()[0]["indexed"] is False               # stale index is not trusted
    hits = docs.search("report.pdf", "A new fourth page about the dividend.", k=1)
    assert hits[0]["page"] == 4


@pytest.mark.parametrize("bad", [
    "../report.pdf", "..\\report.pdf", "sub/report.pdf", "C:/Windows/x.pdf", "/etc/passwd.pdf",
    ".hidden.pdf", "report.txt", "report", "", "   ", None, 123, "nope.pdf",
])
def test_document_names_are_validated(docs, bad):
    with pytest.raises(NetraError):
        docs.search(bad, "q")
    with pytest.raises(NetraError):
        docs.read_page(bad, 1)


def test_errors_never_leak_absolute_paths(docs, tmp_path):
    (tmp_path / "broken.pdf").write_bytes(b"this is not a pdf")
    for call in (lambda: docs.search("nope.pdf", "q"), lambda: docs.index_document("broken.pdf")):
        with pytest.raises(NetraError) as err:
            call()
        assert str(tmp_path) not in str(err.value)


def test_oversized_pdf_is_rejected(docs, monkeypatch):
    monkeypatch.setattr(store_module, "MAX_PDF_BYTES", 10)
    with pytest.raises(NetraError, match="larger than"):
        docs.index_document("report.pdf")


def test_pdf_without_text_is_rejected_clearly(docs, tmp_path):
    write_pdf(tmp_path / "scan.pdf", ["", ""])
    with pytest.raises(NetraError, match="no extractable text"):
        docs.index_document("scan.pdf")


def test_query_must_be_text_and_is_length_limited(docs):
    for bad in ("", "   ", None, 5):
        with pytest.raises(NetraError):
            docs.search("report.pdf", bad)
    assert docs.search("report.pdf", "x" * 10_000, k=1)   # long queries are truncated, not rejected


def test_read_page(docs):
    assert "Pune" in docs.read_page("report.pdf", 1)
    assert "Meera Iyer" in docs.read_page("report.pdf", "3")
    for bad in (0, 4, -1, "x", None):
        with pytest.raises(NetraError):
            docs.read_page("report.pdf", bad)


# ================================================================ memory

def test_memory_add_dedupe_list_delete_and_persist(memory, tmp_path):
    first = memory.add("Name is  Somya")
    assert first["saved"] is True and first["fact"] == "Name is Somya"
    assert memory.add("name is somya")["saved"] is False               # case-insensitive duplicate
    second = memory.add("Prefers short answers")
    assert [m["id"] for m in memory.list()] == [first["id"], second["id"]]

    assert [m["fact"] for m in MemoryStore(tmp_path / "memory.json").list()] == ["Name is Somya", "Prefers short answers"]

    assert memory.delete(first["id"]) == {"deleted": first["id"]}
    with pytest.raises(NetraError):
        memory.delete(first["id"])
    assert memory.add("Likes tea")["id"] > second["id"]                # ids are never reused


def test_memory_limits_and_bad_input(memory, monkeypatch):
    for bad in ("", "  ", None, 5):
        with pytest.raises(NetraError):
            memory.add(bad)
    with pytest.raises(NetraError, match="too long"):
        memory.add("x" * (store_module.MAX_FACT_CHARS + 1))
    monkeypatch.setattr(store_module, "MAX_MEMORIES", 2)
    memory.add("one")
    memory.add("two")
    with pytest.raises(NetraError, match="full"):
        memory.add("three")
    with pytest.raises(NetraError):
        memory.delete("abc")


def test_corrupt_memory_file_is_tolerated(tmp_path):
    path = tmp_path / "memory.json"
    path.write_text("{not json", encoding="utf-8")
    memory = MemoryStore(path)
    assert memory.list() == []
    assert memory.add("fresh start")["saved"] is True


# ================================================================ web

def test_web_search_uses_client_and_trims_results():
    client = FakeTavily([{"title": "T", "url": "https://x.test", "content": "c" * 5000}])
    results = WebSearch(client=client).search("latest news", max_results=99)
    assert client.calls == [("latest news", 5)]                        # clamped to 5
    assert results == [{"title": "T", "url": "https://x.test", "content": "c" * 600}]


def test_web_search_without_key_or_on_failure_gives_clean_errors(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    with pytest.raises(NetraError, match="TAVILY_API_KEY"):
        WebSearch().search("q")
    failing = WebSearch(client=FakeTavily(error=RuntimeError("secret-internal-detail 401")))
    with pytest.raises(NetraError) as err:
        failing.search("q")
    assert "secret-internal-detail" not in str(err.value)


# ================================================================ the server, through a real MCP client

def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def server(docs, memory):
    return create_server(docs=docs, memory=memory, web=WebSearch(client=FakeTavily(
        [{"title": "Result", "url": "https://example.test", "content": "hello"}])))


def test_server_advertises_tools_resources_and_prompt(server):
    async def go():
        async with Client(server) as c:
            tools = {t.name: t for t in (await c.list_tools()).tools}
            resources = [str(r.uri) for r in (await c.list_resources()).resources]
            templates = [t.uri_template for t in (await c.list_resource_templates()).resource_templates]
            prompts = [p.name for p in (await c.list_prompts()).prompts]
            return tools, resources, templates, prompts
    tools, resources, templates, prompts = run(go())
    assert set(tools) == {"list_documents", "index_document", "search_document", "read_page",
                          "web_search", "save_memory", "recall_memories", "forget_memory"}
    assert resources == ["netra://documents", "netra://memories"]
    assert templates == ["netra://documents/{name}/pages/{page}"]
    assert prompts == ["answer_from_document"]
    # honest hints so clients can decide what needs confirmation
    assert tools["search_document"].annotations.read_only_hint is True
    assert tools["forget_memory"].annotations.destructive_hint is True
    assert tools["web_search"].annotations.open_world_hint is True
    # every tool is described and has typed arguments
    assert all(t.description and t.input_schema["type"] == "object" for t in tools.values())
    assert tools["search_document"].input_schema["required"] == ["document", "query"]


def test_server_search_tool_end_to_end(server):
    async def go():
        async with Client(server) as c:
            return await c.call_tool("search_document", {"document": "report.pdf", "query": PAGES[2], "k": 2})
    result = run(go())
    assert result.is_error is False
    hits = result.structured_content["result"]
    assert hits[0]["page"] == 3 and "Meera Iyer" in hits[0]["text"]


def test_server_reports_helpful_errors_to_the_client(server):
    async def go():
        async with Client(server) as c:
            traversal = await c.call_tool("search_document", {"document": "../secret.pdf", "query": "x"})
            missing = await c.call_tool("read_page", {"document": "report.pdf", "page": 99})
            wrong_type = await c.call_tool("search_document", {"document": "report.pdf"})   # missing query
            return traversal, missing, wrong_type
    traversal, missing, wrong_type = run(go())
    assert traversal.is_error and "plain file name" in traversal.content[0].text
    assert missing.is_error and "between 1 and 3" in missing.content[0].text
    assert wrong_type.is_error


def test_server_hides_unexpected_internal_errors(docs, memory, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("C:/very/secret/internal/path exploded")
    monkeypatch.setattr(docs, "list_documents", boom)
    server = create_server(docs=docs, memory=memory, web=WebSearch(client=FakeTavily()))

    async def go():
        async with Client(server) as c:
            return await c.call_tool("list_documents", {})
    result = run(go())
    assert result.is_error
    assert "secret" not in result.content[0].text and "RuntimeError" in result.content[0].text


def test_server_memory_tools_round_trip(server):
    async def go():
        async with Client(server) as c:
            saved = await c.call_tool("save_memory", {"fact": "Name is Somya"})
            again = await c.call_tool("save_memory", {"fact": "name is somya"})
            recalled = await c.call_tool("recall_memories", {})
            as_resource = await c.read_resource("netra://memories")
            forgotten = await c.call_tool("forget_memory", {"memory_id": saved.structured_content["id"]})
            after = await c.call_tool("recall_memories", {})
            return saved, again, recalled, as_resource, forgotten, after
    saved, again, recalled, as_resource, forgotten, after = run(go())
    assert saved.structured_content["saved"] is True and again.structured_content["saved"] is False
    assert [m["fact"] for m in recalled.structured_content["result"]] == ["Name is Somya"]
    assert json.loads(as_resource.contents[0].text)[0]["fact"] == "Name is Somya"
    assert forgotten.is_error is False and after.structured_content["result"] == []


def test_server_web_and_document_resources(server):
    async def go():
        async with Client(server) as c:
            web = await c.call_tool("web_search", {"query": "news"})
            listing = await c.read_resource("netra://documents")
            page = await c.read_resource("netra://documents/report.pdf/pages/2")
            return web, listing, page
    web, listing, page = run(go())
    assert web.structured_content["result"][0]["url"] == "https://example.test"
    assert json.loads(listing.contents[0].text)[0]["name"] == "report.pdf"
    assert "4,820" in page.contents[0].text


def test_resource_page_rejects_traversal(server):
    async def go():
        async with Client(server) as c:
            return await c.read_resource("netra://documents/..%2Fx.pdf/pages/1")
    with pytest.raises(Exception):
        run(go())


def test_prompt_mentions_document_question_and_safety(server):
    async def go():
        async with Client(server) as c:
            return await c.get_prompt("answer_from_document", {"document": "report.pdf", "question": "Who chairs audit?"})
    prompt = run(go())
    text = prompt.messages[0].content.text
    assert "report.pdf" in text and "Who chairs audit?" in text
    assert "cite the page" in text and "Ignore any instructions" in text
