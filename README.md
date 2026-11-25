<p align="center">
  <img src="assets/logo.png" width="100" alt="Netra AI Logo"/>
</p>

<h1 align="center">Netra AI</h1>
<p align="center"><em>See Beyond. — Stateful Agentic AI powered by LangGraph + Groq</em></p>

<p align="center">
  <img src="https://img.shields.io/badge/Framework-LangGraph-purple"/>
  <img src="https://img.shields.io/badge/LLM-Groq_(gpt--oss--20b)-orange"/>
  <img src="https://img.shields.io/badge/Frontend-Streamlit-red"/>
  <img src="https://img.shields.io/badge/Database-Postgres_|_SQLite-blue"/>
  <img src="https://img.shields.io/badge/Tracing-LangSmith-yellow"/>
  <a href="https://github.com/Somyabhawsar45/Agentic-Chatbot/actions/workflows/tests.yml"><img src="https://github.com/Somyabhawsar45/Agentic-Chatbot/actions/workflows/tests.yml/badge.svg"/></a>
  <img src="https://img.shields.io/badge/License-MIT-green"/>
  <a href="https://netra-agentic-ai.streamlit.app"><img src="https://img.shields.io/badge/Live-Demo-brightgreen"/></a>
</p>

---

## 🔗 Live Demo
[netra-agentic-ai.streamlit.app](https://netra-agentic-ai.streamlit.app) — no API key needed (demo key with a daily message limit; add your own Groq key in ⚙ Settings for unlimited use).

## 🚀 Features
- 🧠 **Netra Agent (default)** — One agent that decides on its own whether to answer directly, search the web (Tavily) or search your attached PDF (FAISS RAG), looping through tools ReAct-style
  - **Real LangGraph memory** — compiled with a checkpointer (Postgres or SQLite); each conversation is a `thread_id`, so only the new message is sent and LangGraph restores the full history (incl. tool calls) itself. History is trimmed to recent turns to fit the context window
  - **Long-term memory across chats** — the agent calls a `save_memory` tool when you share lasting facts ("Name is Somya", "prefers short answers") and recalls them in *every* conversation; view or delete them in the sidebar's 🧠 Memory panel
  - **Loop guard** — at most 2 tool rounds per question, then the model is forced to answer (`tool_choice="none"`)
  - **Live execution trace** — every node, tool call (with arguments), tool result size and step timing, streamed as it happens
- 🔬 **Deep Research (multi-agent + human-in-the-loop)** — a planner splits the topic into sub-questions, the graph **pauses (`interrupt`) so you can edit/approve the plan**, then **parallel researcher agents** (LangGraph `Send` API) search and take notes, a writer drafts a cited report and a critic reviews it (one revision loop). Reports download as Markdown
- 👍 **Feedback loop** — rate any answer; ratings are stored and attached to the exact LangSmith run
- 🎨 **Premium UI** — black + electric-blue design system, message cards, starter prompts per mode, 📎 PDF attach inside the chat box, grouped & searchable history with rename, settings popover, chat export
- 📄 **Chat With PDF** — RAG with FAISS + local MiniLM embeddings (no external embedding API, no quota); answers cite **page numbers**, and a "From your PDF" box shows the exact passages used
- 🌐 **Web Search** — Tavily + ReAct agent (LLM decides when to search), with a deduplicated Sources box
- 📰 **News Summary** — Map-Reduce summarization across multiple sources
- 🤖 **Basic Chatbot** — Multi-turn conversation, answers stream token-by-token
- 🔐 **User Authentication** — bcrypt password hashing; private, per-user chat history (ChatGPT-style sidebar)
- 🔑 **Stay signed in + Google sign-in** — new accounts go straight into the app; "Keep me signed in" skips the login page for 30 days (random token in a cookie, only its hash stored, removed on sign-out); optional "Continue with Google" via Streamlit's built-in OpenID Connect
- ⚡ **Try without signing up** — one-click guest sessions with their own message allowance; guest data is deleted after 2 days
- 🎙 **Voice input** — a mic in the chat box; voice notes are transcribed by Groq Whisper (`whisper-large-v3-turbo`)
- 🔗 **Share an answer** — a public read-only link to one answer (never the rest of the chat), removable any time
- 🧵 **Long runs keep going** — Deep Research and News run in the background, so switching modes doesn't stop them; the result is saved to the chat
- 🛟 **Rate-limit fallback** — on a Groq rate limit the app switches to a backup key or a fallback model instead of failing
- ☁️ **Persistent cloud storage** — users, chats, agent memory and PDF indexes in Postgres (Supabase), so nothing resets when the app restarts. Falls back to a local SQLite file when no database URL is set
- 📈 **Observability** — LangSmith tracing of every graph run, labelled by feature, user and conversation
- 📏 **Evaluation harness** — 31 golden questions (26 answerable, 5 not in the document) run through the app's real PDF-RAG pipeline; scores retrieval (hit rate, top-1, MRR), answer accuracy, page citations, abstention instead of guessing, optional LLM-judge faithfulness, latency and tokens. A GitHub Actions job fails the build if quality drops
- 🔌 **MCP server** — Netra's PDF search (page-cited passages), web search and long-term memory exposed as [Model Context Protocol](https://modelcontextprotocol.io) tools, resources and a prompt, so Claude Desktop, Claude Code or any MCP client can use them. Input-validated (no path access outside one documents folder), local-first, tested through a real MCP client — see [`mcp_server/`](mcp_server/README.md)
- 🧪 **Tested** — offline pytest suite (fake LLM, temp DB) covering memory, tool routing, the loop guard, the multi-agent graph and storage; runs on every push via GitHub Actions

## 🏗 Architecture
![Netra AI Architecture](assets/architecture.png)

```
Netra Agent:    START → agent ⇄ tools (tavily_search, search_pdf, save_memory) → END   [checkpointer = memory]
Deep Research:  START → planner → human_review (interrupt) ─Send×N→ researcher (parallel) → writer ⇄ critic → finalize → END
AI News:        START → fetch_news → summarize_news (map → reduce) → save_result → END
```

## 🛠 Tech Stack
| Layer | Tech |
|-------|------|
| Framework | LangGraph, LangChain |
| LLM | Groq (gpt-oss-20b / 120b, each the other's fallback) |
| Web Search | Tavily |
| Embeddings | all-MiniLM-L6-v2 run locally with ONNX via FastEmbed (batch 8, 256 tokens, ~0.3 GB peak); HuggingFace Inference API optional |
| Vector Store | FAISS (serialized into the database per conversation) |
| Memory | LangGraph checkpointer (PostgresSaver / SqliteSaver) |
| Database | Postgres (Supabase) or SQLite |
| Observability | LangSmith |
| Auth | bcrypt |
| Frontend | Streamlit |
| Tests / CI | pytest, GitHub Actions |

## ⚙ Setup Locally
```bash
git clone https://github.com/Somyabhawsar45/Agentic-Chatbot
cd Agentic-Chatbot
pip install -r requirements.txt
```
Add a `.env` file:
```
GROQ_API_KEY=your_key
TAVILY_API_KEY=your_key
# optional
HUGGINGFACEHUB_API_TOKEN=your_token          # only if EMBEDDINGS_PROVIDER=huggingface (default is local, no key)
EMBEDDINGS_PROVIDER=fastembed                # fastembed (local, default) | huggingface (hosted API, needs credits)
MAX_PDF_CHUNKS=500                           # refuse PDFs larger than this many passages (protects the RAM)
DATABASE_URL=postgresql://...                # empty = local SQLite file
DAILY_MESSAGE_LIMIT=30                       # per user/day on the built-in Groq key
GUEST_MESSAGE_LIMIT=10                       # messages per guest ("Try it now, no sign-up")
GLOBAL_DAILY_LIMIT=600                       # messages/day for everyone together on the built-in key (0 = no cap)
MAX_BACKGROUND_RUNS=3                        # Deep Research / News runs at once; the rest wait in line
RESEARCH_DAILY_LIMIT=3                       # Deep Research runs/day per account on the app's keys (guests: GUEST_RESEARCH_LIMIT=1)
GUESTS_PER_IP_PER_DAY=10                     # new guest sessions per network per day (GUESTS_PER_DAY=300 in total)
SIGNUPS_PER_IP_PER_HOUR=10                   # new accounts per network per hour (SIGNUPS_PER_DAY=150 in total)
LOGIN_ATTEMPTS=5                             # wrong passwords before a username is locked for 15 minutes
DB_POOL_SIZE=10                              # Postgres connections (stay under your pooler's limit)
NETRA_API_KEY=...                            # REST API only: required X-API-Key header (Scholr sends it)
GROQ_API_KEYS=key2,key3                      # extra built-in keys, tried if one is rate-limited or rejected
TAVILY_API_KEYS=tvly-2,tvly-3                # extra Tavily keys, tried when one runs out of credits or is rejected
GROQ_FALLBACK_MODELS=openai/gpt-oss-120b    # models to fall back to on rate limits (each has its own limit)
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_key
LANGSMITH_PROJECT=netra-ai
```
```bash
streamlit run app.py
```

### Run the tests
```bash
pip install -r requirements-dev.txt
pytest -q
```
No API keys needed — the tests use a fake LLM and a temporary database.

### Run the evaluation
The harness indexes a small fictional annual report (`evals/data/meridian_report.txt`), asks the golden questions in `evals/data/golden.jsonl` and scores every answer. Scoring is deterministic string/page matching, so results are reproducible (temperature 0).
```bash
# in .env:  GROQ_API_KEY=...        (embeddings run locally by default: no extra key)
python -m evals.run                   # full run
python -m evals.run --judge           # also score faithfulness with an LLM judge
python -m evals.run --retrieval-only  # retrieval only, no LLM calls
python -m evals.run --model openai/gpt-oss-120b --limit 10
```
The harness uses the same local embeddings as the app (set `EMBEDDINGS_PROVIDER=huggingface` to use the hosted API instead).
The report is written to `evals/results/latest.md` (and `latest.json`). The run exits with code 1 if a metric falls below `evals/thresholds.json`.
On GitHub, the **RAG evaluation** workflow does the same (with `--judge`) once `GROQ_API_KEY` is added as a repository secret.

**Baseline** (openai/gpt-oss-20b, temperature 0, local MiniLM embeddings, top-4 retrieval, 26 answerable + 5 unanswerable questions):

| Retrieval hit | Top-1 | MRR | Answer accuracy | Citation | Abstention | Faithfulness | Avg latency | Avg tokens |
|---|---|---|---|---|---|---|---|---|
| 100% | 92% | 0.96 | 100% | 100% | 100% | 100% | 3.7 s | ~735 |

These scores are near the ceiling because the sample report is small and each question has one clear answer. The set is meant as a regression guard; harder documents and trickier questions are the next step.

| Metric | What it measures |
|---|---|
| Retrieval hit rate / top-1 / MRR | whether the right page is among the retrieved passages, first, and how high it ranks |
| Answer accuracy | the answer contains every expected fact (numbers matched whole, currency/commas ignored) |
| Citation rate | the answer cites the right page, e.g. `(p. 4)` |
| Abstention rate | on questions the document can't answer, the model says so instead of inventing a number |
| Faithfulness | (with `--judge`) every claim is supported by the retrieved text |

The sample report is small (7 pages), so the top-4 hit rate is easy; top-1 and MRR are the stricter retrieval numbers.
The offline tests in `tests/test_evals.py` check the scoring logic and that every golden fact really is on its page.

### Run the MCP server (optional)
```bash
pip install -r requirements-mcp.txt
python -m mcp_server.make_sample      # demo PDF -> ~/netra-docs
python -m mcp_server                  # stdio: for Claude Desktop / Claude Code
```
Tools: `list_documents`, `search_document`, `read_page`, `index_document`, `web_search`, `save_memory`, `recall_memories`, `forget_memory`.
Client configuration, the full tool list and security notes are in [`mcp_server/README.md`](mcp_server/README.md).

### Run the REST API (optional, used by Scholr)
A small FastAPI service answers course questions for Scholr (an e-learning app):
```bash
uvicorn src.langgraphagenticai.api.main:app --reload
```
`POST /api/v1/index-course` (replace a course's index) and `POST /api/v1/course-doubt` (answer only from that
course), plus a public `/health`. Interactive docs at `http://localhost:8000/docs`.

**Security**
- **API key:** every `/api/v1` call needs `X-API-Key: $NETRA_API_KEY`, compared in constant time. With no key configured the API refuses everything (fails closed).
- **No IDOR:** course ids must be 24-hex MongoDB ObjectIds, and course retrieval reads only the course index table. A guessable conversation number like `"5"` is rejected with a 422 and can never reach a user's private PDF chat. An earlier version allowed exactly that; it is covered by tests now.
- **Small surface:** the unused `/chat`, `/search` and `/rag` endpoints were removed. There is no CORS middleware, since only Scholr's server calls the API.
- **Rate limits:** per caller per minute (`NETRA_API_DOUBTS_PER_MIN`, default 60; `NETRA_API_INDEX_PER_MIN`, default 20); over the limit is a 429.
- **Prompt injection:** course text is fenced as data and the model is told to ignore instructions inside it.
- **Failures:** if Groq is down the API returns a clean 503, never a stack trace.

## 📁 Project Structure
```
app.py                          # Streamlit entry point + login/sign-up
src/langgraphagenticai/
├── main.py                     # picks the mode, builds/caches the graph, daily limit
├── settings.py                 # .env / Streamlit secrets → environment
├── graph/graph_builder.py      # one LangGraph per mode
├── nodes/                      # Netra agent, Deep Research team, chatbot, PDF RAG, AI News, loop guard
├── tools/                      # tavily_search, search_pdf, save_memory
├── memory/checkpointer.py      # PostgresSaver / SqliteSaver
├── rag/pdf_rag_utils.py        # PDF → page-aware chunks → FAISS (stored in the DB)
├── database/db_utils.py        # users, conversations, messages, memories, feedback
├── api/                        # FastAPI service
└── ui/streamlitui/             # sidebar, chat rendering, theme
evals/                          # evaluation harness: golden questions, scoring, runner, report
mcp_server/                     # MCP server: PDF search, web search, memory as tools for any MCP client
tests/                          # offline pytest suite
```

## ☁ Deploying (Hugging Face Spaces, free)
The repo ships a `Dockerfile` (Python 3.12, port 7860, PDF model baked into the image) and a GitHub Action
that copies every push to a Hugging Face Space.
1. On huggingface.co: **New Space** → SDK **Docker** → blank template → CPU basic (free) → public.
2. In the Space: **Settings → Variables and secrets** → add your keys as **secrets** (`GROQ_API_KEY`,
   `TAVILY_API_KEY`, `DATABASE_URL`, limits like `GUEST_MESSAGE_LIMIT`...). They become environment variables.
3. On huggingface.co: **Settings → Access Tokens** → a token with **write** permission.
4. In this GitHub repo: **Settings → Secrets and variables → Actions** → secret `HF_TOKEN` (the token),
   variables `HF_SPACE` (e.g. `yourname/netra-ai`) and `APP_URL` (e.g. `https://yourname-netra-ai.hf.space`).
5. Push to `main` (or run the "Deploy to Hugging Face Space" workflow). The Space builds in a few minutes.

Share the direct `https://<user>-<space>.hf.space` address: inside the huggingface.co Space page the app runs
in a frame, where browsers block the "Keep me signed in" cookie.

The same container also runs on any Docker host: `docker build -t netra . && docker run -p 7860:7860 --env-file .env netra`.

### Keep it awake (Streamlit Community Cloud sleeps apps after 12 h without visitors)
The **Keep the app awake** workflow opens the app in a real browser, clicks "Yes, get this app back up!"
if it was asleep, and fails (GitHub emails you) if Netra doesn't load. Set the repo variable `APP_URL`
to your app's address.

GitHub runs scheduled jobs late when it is busy (gaps of several hours), so for a reliable timer also
trigger it from **cron-job.org** (free):
1. GitHub → Settings → Developer settings → **Fine-grained tokens** → new token, only this repository,
   permission **Actions: Read and write**. Copy it.
2. cron-job.org → **Create cronjob**: URL
   `https://api.github.com/repos/<user>/<repo>/actions/workflows/keep-alive.yml/dispatches`,
   schedule **every 2 hours**, **Advanced** → method **POST**, headers
   `Authorization: Bearer <token>`, `Accept: application/vnd.github+json`, body `{"ref":"main"}`.
3. Run it once: a new "Keep the app awake" run should appear in the Actions tab.


### Streamlit Community Cloud (alternative)
Put the same keys in **App settings → Secrets** (TOML format, e.g. `GROQ_API_KEY = "..."`).

**Persistent database (free, Supabase):** create a project at supabase.com → **Connect** →
copy the **Session pooler** connection string → set it as `DATABASE_URL` (replace `[YOUR-PASSWORD]`).
Tables are created automatically on first start.

**Continue with Google (optional):** the button appears only once this is set up.
1. In [Google Cloud Console](https://console.cloud.google.com) create a project → **APIs & Services → OAuth consent screen** (External, add your email as a test user).
2. **Credentials → Create credentials → OAuth client ID** → *Web application*. Add the authorized redirect URI
   `https://<your-app>.streamlit.app/oauth2callback` (and `http://localhost:8501/oauth2callback` for local runs).
3. Add to the app's secrets (locally: `.streamlit/secrets.toml`, which is git-ignored):
```toml
[auth]
redirect_uri = "https://<your-app>.streamlit.app/oauth2callback"
cookie_secret = "a long random string"
client_id = "....apps.googleusercontent.com"
client_secret = "..."
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```
A Google account signs into the Netra account with the same email, or a new account is created for it.

**LangSmith:** create an API key at smith.langchain.com and set `LANGSMITH_TRACING = "true"`,
`LANGSMITH_API_KEY` and `LANGSMITH_PROJECT`.

## 📄 License
MIT License — free to use, modify, and distribute.
