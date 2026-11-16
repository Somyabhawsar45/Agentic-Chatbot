# Netra MCP server

Exposes Netra's document search, web search and long-term memory to any
[MCP](https://modelcontextprotocol.io) client — Claude Desktop, Claude Code, or your own agent.

The server provides **tools only**; it makes no LLM calls. The client's own model decides when to
call them and writes the answer, so the server needs no model API key.

## What it exposes

| Kind | Name | What it does |
|---|---|---|
| tool | `list_documents` | PDFs available to search (size, indexed?, page count) |
| tool | `search_document(document, query, k=4)` | semantic search in one PDF → passages with **page numbers** |
| tool | `read_page(document, page)` | full text of one page, to check a hit in context |
| tool | `index_document(document, force=False)` | pre-build / rebuild the index (search does this automatically) |
| tool | `web_search(query, max_results=3)` | Tavily web search → title, url, snippet |
| tool | `save_memory(fact)` / `recall_memories()` / `forget_memory(memory_id)` | long-term facts about the user |
| resource | `netra://documents`, `netra://memories` | the same lists, as readable resources |
| resource | `netra://documents/{name}/pages/{page}` | one page of a PDF |
| prompt | `answer_from_document(document, question)` | a ready-made "answer only from this PDF, cite pages" instruction |

Tools carry honest hints (`read_only`, `destructive`, `open_world`) so clients can decide what
needs confirmation — e.g. `forget_memory` is marked destructive, `web_search` open-world.

## Setup

```bash
pip install -r requirements-mcp.txt
python -m mcp_server.make_sample        # optional: writes a demo PDF to ~/netra-docs
```

Put your PDFs in one folder (default `~/netra-docs`, or set `NETRA_DOCS_DIR`). Indexes and the
memory file are stored in that folder (`.index/`, `.netra-memory.json`).

Optional keys, in a `.env` in the project root or in the client's `env` block:

| Variable | Needed for |
|---|---|
| `TAVILY_API_KEY` | `web_search` |
| `NETRA_DOCS_DIR` | a documents folder other than `~/netra-docs` |
| `EMBEDDINGS_PROVIDER` | `fastembed` (default, local and free) or `huggingface` (hosted, needs a token and credits) |

## Connect a client

**stdio** (Claude Desktop / Claude Code launch the server themselves). Use the full path of the
Python that has the requirements installed, and set `PYTHONPATH` to this project so
`-m mcp_server` works from any folder.

Claude Desktop → `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "netra": {
      "command": "C:\\path\\to\\python.exe",
      "args": ["-m", "mcp_server"],
      "env": {
        "PYTHONPATH": "C:\\path\\to\\Agentic-Chatbot",
        "NETRA_DOCS_DIR": "C:\\Users\\you\\netra-docs",
        "TAVILY_API_KEY": "optional"
      }
    }
  }
}
```

Claude Code:
```bash
claude mcp add netra -e PYTHONPATH=/path/to/Agentic-Chatbot -e NETRA_DOCS_DIR=~/netra-docs -- /path/to/python -m mcp_server
```

**Streamable HTTP** (for remote-style clients, local only):
```bash
python -m mcp_server --transport streamable-http      # http://127.0.0.1:8000/mcp
```

Then try: *"List my documents, then find who chairs the audit committee in meridian_report.pdf and cite the page."*

## Security notes

The tools are called by an LLM, so every input is treated as untrusted:

- Documents are addressed by **plain file name only** — no paths, no `..`, no hidden files, `.pdf` only, 25 MB max. Error messages never contain absolute paths.
- Query, fact and result sizes are capped; memory holds at most 200 short facts.
- Unexpected errors are logged to **stderr** and summarised for the client (stdout is reserved for the protocol).
- **Prompt injection:** PDF text and web results can contain instructions aimed at the model. The server's instructions and the `answer_from_document` prompt tell the client to treat them as data, but that is advice, not a guarantee — keep confirmation prompts on for tools that change things.
- The **HTTP transport has no authentication.** It binds to `127.0.0.1` by default and warns if you change that. Don't expose it to a network.
- Indexes are loaded with pickle (FAISS). Only point `NETRA_DOCS_DIR` at a folder you trust and that only you can write to.
- `web_search` sends your query text to Tavily; memories are stored as plain JSON on disk, so don't save secrets.

## Tests

`tests/test_mcp_server.py` covers the storage layer and the whole server through a real in-process MCP client
(tool discovery, argument validation, error reporting, resources, prompt). It runs offline with fake embeddings.
