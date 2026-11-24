from fastapi import Depends, FastAPI

from .routes import router
from .security import require_api_key

app = FastAPI(
    title="Netra AI API",
    description="Course Q&A backend for Scholr: LangGraph + Groq, course-only retrieval",
    version="1.1.0",
)

# No CORS middleware on purpose: only Scholr's server calls this API, never a browser, so
# browsers keep their default same-origin protection.
# Every /api/v1 route needs the X-API-Key header (see security.py). /health stays public.
app.include_router(router, prefix="/api/v1", dependencies=[Depends(require_api_key)])


@app.get("/health")
def health():
    return {"status": "ok", "service": "Netra AI"}
