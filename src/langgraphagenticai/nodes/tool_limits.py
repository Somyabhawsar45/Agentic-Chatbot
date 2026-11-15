from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# Max tool-calling rounds per user question. Some models (e.g. gpt-oss on Groq)
# keep re-searching forever; after this many rounds the LLM must answer.
MAX_TOOL_ROUNDS = 2

ANSWER_NOW = SystemMessage(content=(
    "You have already searched enough. Do NOT call any more tools. "
    "Answer the user's question now using the tool results above. "
    "If they don't contain the answer, say what you found and what's missing."
))


def tool_rounds_this_turn(messages: list) -> int:
    """Count AI tool-call messages since the user's latest message."""
    rounds = 0
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            break
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            rounds += 1
    return rounds


def tools_exhausted(messages: list) -> bool:
    return tool_rounds_this_turn(messages) >= MAX_TOOL_ROUNDS
