import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../../../.env'))
from langchain_groq import ChatGroq
from fastapi import APIRouter
from .schemas import ChatRequest, SearchRequest, RAGRequest, ChatResponse
from ..graph.graph_builder import GraphBuilder

router = APIRouter()

def get_llm():
    from dotenv import dotenv_values
    config = dotenv_values(r"C:\Users\mahen\OneDrive\Documents\Visual Studio 2022\Agenitc Chatbot\.env")
    api_key = config.get("GROQ_API_KEY", "")
    return ChatGroq(
        api_key=api_key,
        model="llama-3.1-8b-instant",
        streaming=False
    )
@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    llm = get_llm()
    builder = GraphBuilder(llm)
    graph = builder.setup_graph("Basic Chatbot")
    result = graph.invoke({
        "messages": [{"role": "user", "content": req.message}]
    })
    return ChatResponse(
        answer=result["messages"][-1].content,
        session_id=req.session_id
    )

@router.post("/search", response_model=ChatResponse)
async def search(req: SearchRequest):
    llm = get_llm()
    builder = GraphBuilder(llm)
    graph = builder.setup_graph("Chatbot With Web")
    result = graph.invoke({
        "messages": [{"role": "user", "content": req.query}]
    })
    return ChatResponse(
        answer=result["messages"][-1].content,
        session_id=req.session_id
    )

@router.post("/rag", response_model=ChatResponse)
async def rag(req: RAGRequest):
    llm = get_llm()
    builder = GraphBuilder(llm)
    graph = builder.setup_graph("Chat with PDF", conversation_id=req.session_id)
    result = graph.invoke({
        "messages": [{"role": "user", "content": req.question}]
    })
    return ChatResponse(
        answer=result["messages"][-1].content,
        session_id=req.session_id
    )