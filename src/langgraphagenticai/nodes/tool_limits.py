import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

# Max tool-calling rounds per user question. Some models (e.g. gpt-oss on Groq)
# keep re-searching forever; after this many rounds the LLM must answer.
MAX_TOOL_ROUNDS = 2

ANSWER_NOW = SystemMessage(content=(
    "You have already searched enough. Do NOT call any more tools. "
    "Answer the user's question now using the tool results above. "
    "If they don't contain the answer, say what you found and what's missing."
))

PLAIN_TEXT_ONLY = SystemMessage(content=(
    "Reply with plain text only. Do not call, request or mention any tool or function."
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


# ---------------------------------------------------------------------------
# Forcing a final answer
#
# The first version bound the tools with tool_choice="none". Groq then rejects the whole run with
# "Tool choice is none, but model called a tool" whenever the model ignores that instruction,
# which gpt-oss occasionally does. So instead the final answer is requested from a model with NO
# tools declared, over a plain-text copy of the conversation: it has nothing to call, and nothing
# in the history that looks like a tool call.
# ---------------------------------------------------------------------------

def _text(content) -> str:
    return content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, default=str)


def without_tool_calls(messages: list) -> list:
    """Copy of the conversation where tool calls and tool results are plain text (same information)."""
    plain = []
    for m in messages:
        if isinstance(m, ToolMessage):
            plain.append(HumanMessage(content=f"[Result from {getattr(m, 'name', None) or 'tool'}]\n{_text(m.content)}"))
        elif isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            calls = "; ".join(
                f"{c.get('name', 'tool')}({json.dumps(c.get('args', {}), ensure_ascii=False)})" for c in m.tool_calls
            )
            said = _text(m.content).strip() if m.content else ""
            plain.append(AIMessage(content=(said + " " if said else "") + f"[I called: {calls}]"))
        else:
            plain.append(m)
    return plain


def answer_without_tools(llm, messages: list):
    """
    Ask `llm` (an unbound model) for the final answer. If the provider still complains about a tool,
    retry once with an explicit plain-text instruction before giving up.
    """
    plain = without_tool_calls(messages) + [ANSWER_NOW]
    try:
        return llm.invoke(plain)
    except Exception as e:
        if "tool" not in str(e).lower():
            raise
        return llm.invoke(plain + [PLAIN_TEXT_ONLY])


def _tool_refusal(error: Exception) -> bool:
    """Groq's error when gpt-oss tries a (built-in) tool on a request that has none."""
    text = str(error).lower()
    return "tool choice is none" in text or "tool_use_failed" in text or "called a tool" in text


def invoke_plain(llm, messages, retries: int = 2, **kwargs):
    """
    llm.invoke for steps that must answer in plain text (news summaries, research notes, the report).
    gpt-oss on Groq sometimes reaches for a built-in tool anyway and Groq rejects the whole request
    ("Tool choice is none, but model called a tool"). Then: ask again, with a firm plain-text rule.
    """
    if isinstance(messages, str):
        messages = [HumanMessage(content=messages)]
    try:
        return llm.invoke(messages, **kwargs)
    except Exception as e:
        if not _tool_refusal(e):
            raise
        last = e
    for _ in range(retries):
        try:
            return llm.invoke([PLAIN_TEXT_ONLY] + list(messages), **kwargs)
        except Exception as e:
            if not _tool_refusal(e):
                raise
            last = e
    raise last
