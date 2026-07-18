<p align="center">
  <img src="assets/logo.png" width="100" alt="Netra AI Logo"/>
</p>

<h1 align="center">Netra AI</h1>
<p align="center"><em>See Beyond. — Stateful Agentic AI powered by LangGraph + Groq</em></p>

<p align="center">
  <img src="https://img.shields.io/badge/Framework-LangGraph-purple"/>
  <img src="https://img.shields.io/badge/LLM-Groq_(gpt--oss--20b)-orange"/>
  <img src="https://img.shields.io/badge/Frontend-Streamlit-red"/>
  <img src="https://img.shields.io/badge/Database-SQLite-blue"/>
  <img src="https://img.shields.io/badge/License-MIT-green"/>
  <a href="https://netra-agentic-ai.streamlit.app"><img src="https://img.shields.io/badge/Live-Demo-brightgreen"/></a>
</p>

---

## 🔗 Live Demo
[netra-agentic-ai.streamlit.app](https://netra-agentic-ai.streamlit.app)

> **Note:** This demo runs on Streamlit Community Cloud with a local SQLite database. Since the free tier's filesystem is ephemeral, accounts and chat history may reset if the app restarts after a period of inactivity.

## 🚀 Features
- 🔐 **User Authentication** — Secure login/signup with bcrypt password hashing; private, per-user chat history
- 🤖 **Basic Chatbot** — Multi-turn stateful conversation with memory
- 🌐 **Web Search** — Real-time lookup via Tavily + ReAct agent
- 📄 **Chat With PDF** — RAG pipeline with FAISS + HuggingFace embeddings
- 📰 **News Summary** — Map-Reduce summarization across multiple sources
- 💬 **Chat History** — Persistent conversation history via a custom SQLite schema (users, conversations, messages), loaded per user/conversation and injected into context on each invocation — enables ChatGPT-like multi-conversation history per user

## 🏗 Architecture
![Netra AI Architecture](assets/architecture.png)

## 🛠 Tech Stack
| Layer | Tech |
|-------|------|
| Framework | LangGraph, LangChain |
| LLM | Groq (gpt-oss-20b) |
| Web Search | Tavily |
| Embeddings | HuggingFace sentence-transformers |re
| Vector Store | FAISS |
| Auth | bcrypt (password hashing) |
| Frontend | Streamlit |
| Database | SQLite |

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
```
```bash
streamlit run app.py
```

## 📄 License
MIT License — free to use, modify, and distribute.