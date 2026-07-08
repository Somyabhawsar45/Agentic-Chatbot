import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../../../.env'))
from langchain_groq import ChatGroq
from fastapi import APIRouter
from .schemas import ChatRequest, SearchRequest, RAGRequest, ChatResponse, CourseDoubtRequest,IndexCourseRequest
from ..graph.graph_builder import GraphBuilder

router = APIRouter()

def get_llm():
    api_key = os.getenv("GROQ_API_KEY")
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

from ..rag.pdf_rag_utils import retrieve_chunks

@router.post("/course-doubt", response_model=ChatResponse)
async def course_doubt(req: CourseDoubtRequest):
    chunks = retrieve_chunks(req.session_id, req.question, k=4)

    if not chunks:
        return ChatResponse(
            answer="I don't have course content indexed for this course yet.",
            session_id=req.session_id
        )

    context = "\n\n".join(chunks)
    prompt = f"""Answer the student's question using only the course content below. If the answer isn't in the content, say so honestly.

Course Content:
{context}

Question: {req.question}

Answer:"""

    llm = get_llm()
    response = llm.invoke(prompt)

    return ChatResponse(
        answer=response.content,
        session_id=req.session_id
    )

from ..rag.pdf_rag_utils import build_index_from_text

@router.post("/index-course")
async def index_course(req: IndexCourseRequest):
    build_index_from_text(req.content, req.course_id)
    return {"success": True, "message": "Course indexed successfully"}