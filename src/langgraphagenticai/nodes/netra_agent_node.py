from datetime import date

from langchain_core.messages import SystemMessage, trim_messages
from langchain_core.runnables import RunnableConfig

from src.langgraphagenticai.database import db_utils
from src.langgraphagenticai.rag import pdf_rag_utils
from src.langgraphagenticai.state.state import State
from src.langgraphagenticai.nodes.tool_limits import answer_without_tools, tools_exhausted

SYSTEM_PROMPT = """You are Netra, an agentic AI assistant. Today's date is {today}.

What you know about this user (long-term memory, from earlier conversations):
{memories}

You decide for yourself how to answer each message:
{tool_guide}
- Otherwise (greetings, general knowledge, writing, coding, maths) answer directly without tools.

Rules:
- Use the conversation history and the long-term memory; personalise answers when relevant.
- When you use web results, cite them as markdown links.
- When you use the PDF, cite the page for each fact like this: (p. 4).
- Be helpful and concise."""

WEB_GUIDE = (
    "- Use `tavily_search` for current events, recent facts or prices. "
    "One search is usually enough; then answer from the results instead of searching again."
)
PDF_GUIDE = (
    "- A document is attached to this conversation{name}. For any question that could be about it, "
    "including the company, people or figures it describes, call `search_pdf` FIRST and answer from it. "
    "Only search the web if the document doesn't cover the question, and say so."
)


def pdf_guide(filename) -> str:
    return PDF_GUIDE.format(name=f': "{filename}"' if filename else "")
MEMORY_GUIDE = (
    "- When the user shares a lasting personal fact or preference (name, role, goals, how they like "
    "answers) or asks you to remember something, call `save_memory` once, then reply normally. "
    "Don't save facts that are already in your long-term memory."
)

# How many recent messages the LLM sees. The checkpointer keeps the full history;
# trimming keeps long conversations inside the model's context window.
MAX_HISTORY_MESSAGES = 24


def format_memories(memories: list) -> str:
    if not memories:
        return "- (nothing yet)"
    return "\n".join(f"- {m['content']}" for m in memories)


class NetraAgentNode:
    """
    The 'brain' of the Netra Agent: one LLM that routes between tools itself.
    Tools offered on each turn depend on what's available (web key, attached PDF,
    signed-in user for long-term memory).
    """

    def __init__(self, llm, web_tools: list, pdf_tools: list, memory_tools: list = None):
        self.llm = llm
        self.web_tools = web_tools
        self.pdf_tools = pdf_tools
        self.memory_tools = memory_tools or []

    def process(self, state: State, config: RunnableConfig) -> dict:
        configurable = config.get("configurable", {})
        conversation_id = configurable.get("conversation_id")
        user_id = configurable.get("user_id")
        has_pdf = pdf_rag_utils.has_index(conversation_id)
        has_user = user_id is not None

        tools = (
            list(self.web_tools)
            + (list(self.pdf_tools) if has_pdf else [])
            + (list(self.memory_tools) if has_user else [])
        )
        guides = (
            ([WEB_GUIDE] if self.web_tools else [])
            + ([pdf_guide(db_utils.get_pdf_filename(conversation_id))] if has_pdf else [])
            + ([MEMORY_GUIDE] if has_user and self.memory_tools else [])
        )

        system = SystemMessage(content=SYSTEM_PROMPT.format(
            today=date.today().isoformat(),
            memories=format_memories(db_utils.get_memories(user_id)) if has_user else "- (not signed in)",
            tool_guide="\n".join(guides) or "- No tools are available right now.",
        ))

        history = trim_messages(
            state["messages"],
            strategy="last",
            token_counter=len,          # count messages, not tokens
            max_tokens=MAX_HISTORY_MESSAGES,
            start_on="human",           # never start mid tool-call
        )

        if tools and tools_exhausted(state["messages"]):
            # enough tool use for this question: answer from a plain-text copy of the
            # conversation with no tools declared (nothing left to call, nothing to reject)
            response = answer_without_tools(self.llm, [system] + history)
        else:
            llm = self.llm.bind_tools(tools) if tools else self.llm
            response = llm.invoke([system] + history)
        return {"messages": [response]}
