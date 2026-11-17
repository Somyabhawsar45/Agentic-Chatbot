import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../../../.env'))
from langchain_groq import ChatGroq
from fastapi import APIRouter, HTTPException
from .schemas import ChatRequest, SearchRequest, RAGRequest, ChatResponse, CourseDoubtRequest,IndexCourseRequest
from ..graph.graph_builder import GraphBuilder

router = APIRouter()

def get_llm():
    api_key = os.getenv("GROQ_API_KEY")
    return ChatGroq(
        api_key=api_key,
        # Configurable because Groq retires models; gpt-oss-20b is also the app's default
        model=os.getenv("NETRA_API_MODEL", "openai/gpt-oss-20b"),
        streaming=False,
        max_retries=6,  # free tier: retry briefly on rate limits instead of failing
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

# Plain `def` (not async): retrieval and the LLM call block, so FastAPI runs these in a
# worker thread instead of freezing the server for other requests.
@router.post("/course-doubt", response_model=ChatResponse)
def course_doubt(req: CourseDoubtRequest):
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
def index_course(req: IndexCourseRequest):
    """Replaces the course's index with the full content Scholr sends (stored in the database)."""
    try:
        stored = build_index_from_text(req.content, req.course_id)
    except ValueError as e:  # empty or oversized content
        raise HTTPException(status_code=400, detail=str(e))
    return {"success": True, "message": "Course indexed successfully", "stored": stored}