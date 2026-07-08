from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    session_id: str

class SearchRequest(BaseModel):
    query: str
    session_id: str

class RAGRequest(BaseModel):
    question: str
    session_id: str

class ChatResponse(BaseModel):
    answer: str
    session_id: str

class CourseDoubtRequest(BaseModel):
    question: str
    session_id: str