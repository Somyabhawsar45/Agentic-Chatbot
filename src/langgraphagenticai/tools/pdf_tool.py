from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from src.langgraphagenticai.rag import pdf_rag_utils


@tool(response_format="content_and_artifact")
def search_pdf(query: str, config: RunnableConfig):
    """Search the PDF document the user uploaded in this conversation.
    Use it for any question about the document's contents. Returns the most relevant
    passages, each labelled with its page number."""
    # `config` is injected by LangGraph (hidden from the LLM); it tells us which conversation's index to use
    conversation_id = config.get("configurable", {}).get("conversation_id")
    passages = pdf_rag_utils.retrieve(conversation_id, query, k=4)
    if not passages:
        return "No PDF is attached to this conversation, or nothing relevant was found.", []
    # content -> the LLM sees the text; artifact -> the UI shows page + quote citations
    return pdf_rag_utils.format_passages(passages), passages
