from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from src.langgraphagenticai.state.state import State
from src.langgraphagenticai.rag import pdf_rag_utils


class PdfRagNode:
    """
    Retrieval-Augmented Generation node for PDF Q&A with multi-turn memory.
    Answers cite page numbers, and the retrieved passages are returned as
    `citations` so the UI can show the exact quotes under the answer.
    """
    def __init__(self, model, conversation_id):
        self.llm = model
        self.conversation_id = conversation_id

    def process(self, state: State) -> dict:
        # Get current question from last message
        last_message = state["messages"][-1]
        question = last_message.content if hasattr(last_message, "content") else str(last_message)

        # Retrieve relevant passages (with page numbers) from FAISS
        passages = pdf_rag_utils.retrieve(self.conversation_id, question, k=4)
        context = pdf_rag_utils.format_passages(passages) if passages else "No relevant context found in the document."

        system_prompt = (
            "You are Netra, a helpful assistant answering questions about an uploaded PDF document.\n"
            "Use ONLY the context below to answer. If the answer isn't in the context, say so clearly.\n"
            "Cite the page for each fact like this: (p. 4). Use the page numbers given in the passage labels.\n\n"
            f"Context from PDF:\n{context}"
        )

        # System prompt + previous turns + current question
        messages = [SystemMessage(content=system_prompt)]
        messages.extend(state["messages"][:-1])
        messages.append(HumanMessage(content=question))

        response = self.llm.invoke(messages)

        return {
            "messages": [AIMessage(content=response.content)],
            "context": context,
            "citations": passages,
        }
