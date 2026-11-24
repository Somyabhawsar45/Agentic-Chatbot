from pydantic import BaseModel, Field

# Scholr's course ids are MongoDB ObjectIds: exactly 24 hex characters. Anything else (for example
# "5", a conversation number) is rejected with a 422 before it gets near the database.
OBJECT_ID = r"^[a-f0-9]{24}$"


class ChatResponse(BaseModel):
    answer: str
    session_id: str


class CourseDoubtRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    session_id: str = Field(pattern=OBJECT_ID)       # the course id (Scholr's field name)


class IndexCourseRequest(BaseModel):
    course_id: str = Field(pattern=OBJECT_ID)
    content: str = Field(max_length=2_000_000)       # empty content is answered with a clear 400
