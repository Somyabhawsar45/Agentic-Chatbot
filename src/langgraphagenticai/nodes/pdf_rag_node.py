from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from src.langgraphagenticai.state.state import State
from src.langgraphagenticai.rag import pdf_rag_utils


class PdfRagNode:
    """
    Retrieval-Augmented Generation node for PDF Q&A with multi-turn memory.
    """
    def __init__(self, model, conversation_id):
        self.llm = model
        self.conversation_id = conversation_id

    def process(self, state: State) -> dict:
        # Get current question from last message
        last_message = state["messages"][-1]
        question = last_message.content if hasattr(last_message, "content") else str(last_message)

        # Retrieve relevant chunks from FAISS
        chunks = pdf_rag_utils.retrieve_chunks(self.conversation_id, question, k=4)
        context = "\n\n---\n\n".join(chunks) if chunks else "No relevant context found in the document."

        # Build message history with system prompt + context
        system_prompt = (
            "You are Netra, a helpful assistant answering questions about an uploaded PDF document.\n"
            "Use ONLY the context below to answer. If the answer isn't in the context, say so clearly.\n\n"
            f"Context from PDF:\n{context}"
        )

        # Build full conversation history
        messages = [SystemMessage(content=system_prompt)]

        # Add all previous messages except the last one (current question)
        for msg in state["messages"][:-1]:
            messages.append(msg)

        # Add current question
        messages.append(HumanMessage(content=question))

        response = self.llm.invoke(messages)

        return {
            "messages": [AIMessage(content=response.content)],
            "context": context
        }