from langchain_core.messages import HumanMessage, AIMessage
from src.langgraphagenticai.state.state import State
from src.langgraphagenticai.rag import pdf_rag_utils


class PdfRagNode:
    """
    Retrieval-Augmented Generation node for PDF Q&A.
    """
    def __init__(self, model, conversation_id):
        self.llm = model
        self.conversation_id = conversation_id

    def process(self, state: State) -> dict:
        last_message = state["messages"][-1]
        question = last_message.content if hasattr(last_message, "content") else str(last_message)

        chunks = pdf_rag_utils.retrieve_chunks(self.conversation_id, question, k=4)
        context = "\n\n---\n\n".join(chunks) if chunks else "No relevant context found in the document."

        prompt = (
            "You are a helpful assistant answering questions about an uploaded PDF document.\n"
            "Use ONLY the context below to answer. If the answer isn't in the context, say so clearly.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}"
        )

        response = self.llm.invoke([HumanMessage(content=prompt)])

        return {
            "messages": [AIMessage(content=response.content)],
            "context": context
        }