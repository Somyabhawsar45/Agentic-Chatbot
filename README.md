# 👁 Netra AI
> See Beyond. — Stateful Agentic AI powered by LangGraph + Groq

## 🔗 Live Demo
[netra-agentic-ai.streamlit.app](https://netra-agentic-ai.streamlit.app)

## 🚀 Features
- 🤖 **Basic Chatbot** — Multi-turn stateful conversation with memory
- 🌐 **Web Search** — Real-time lookup via Tavily + ReAct agent
- 📄 **Chat With PDF** — RAG pipeline with FAISS + HuggingFace embeddings
- 📰 **News Summary** — Map-Reduce summarization across multiple sources
- 💬 **Chat History** — ChatGPT-like persistent conversation history via SQLite

## 🏗 Architecture
![Netra AI Architecture](assets/architecture.png)

## 🛠 Tech Stack
| Layer | Tech |
|-------|------|
| Framework | LangGraph, LangChain |
| LLM | Groq (Llama 3.1) |
| Web Search | Tavily |
| Embeddings | HuggingFace sentence-transformers |
| Vector Store | FAISS |
| Frontend | Streamlit |
| Database | SQLite |

## ⚙ Setup Locally
```bash
git clone https://github.com/Somyabhawsar45/netra-ai
cd netra-ai
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