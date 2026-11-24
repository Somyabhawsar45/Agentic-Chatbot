import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

from src.langgraphagenticai.nodes.chatbot_with_Tool_node import ChatbotWithToolNode
from src.langgraphagenticai.nodes.tool_limits import (
    ANSWER_NOW, MAX_TOOL_ROUNDS, PLAIN_TEXT_ONLY, answer_without_tools, tool_rounds_this_turn,
    tools_exhausted, without_tool_calls,
)


def _tool_call(i):
    return AIMessage(content="", tool_calls=[{"name": "tavily_search", "args": {"query": "q"}, "id": f"c{i}"}])


def test_counts_only_rounds_after_latest_question():
    messages = [
        HumanMessage(content="old question"), _tool_call(1), ToolMessage(content="r", tool_call_id="c1"),
        AIMessage(content="old answer"),
        HumanMessage(content="new question"), _tool_call(2), ToolMessage(content="r", tool_call_id="c2"),
    ]
    assert tool_rounds_this_turn(messages) == 1
    assert not tools_exhausted(messages)


def _exhausted_history():
    messages = [HumanMessage(content="What is the news?")]
    for i in range(MAX_TOOL_ROUNDS):
        messages += [_tool_call(i), ToolMessage(content=f"result {i}", tool_call_id=f"c{i}", name="tavily_search")]
    return messages


def test_exhausted_after_max_rounds():
    assert tools_exhausted(_exhausted_history())


# ---------------- forcing a final answer without tools ----------------

def test_tool_calls_and_results_become_plain_text_with_the_same_information():
    plain = without_tool_calls(_exhausted_history())
    assert not any(isinstance(m, ToolMessage) or getattr(m, "tool_calls", None) for m in plain)
    texts = [str(m.content) for m in plain]
    assert any("[Result from tavily_search]\nresult 0" in t for t in texts)      # the data survives
    assert any("[I called: tavily_search(" in t and '"query": "q"' in t for t in texts)
    assert texts[0] == "What is the news?"                                       # normal messages untouched


def test_final_answer_is_requested_with_no_tools_and_the_answer_now_instruction(fake_llm_factory):
    llm = fake_llm_factory(lambda messages, bound: AIMessage(content="final"))
    assert answer_without_tools(llm, _exhausted_history()).content == "final"
    messages, bound = llm.calls[0]
    assert not bound                                  # no bind_tools(...), so no tool_choice either
    assert messages[-1] is ANSWER_NOW
    assert not any(isinstance(m, ToolMessage) for m in messages)


def test_retries_once_with_plain_text_instruction_if_the_provider_complains_about_a_tool(fake_llm_factory):
    attempts = []

    def responder(messages, bound):
        attempts.append(messages)
        if len(attempts) == 1:
            raise RuntimeError("Error code: 400 - tool call validation failed: attempted to call tool 'x'")
        return AIMessage(content="plain answer")

    llm = fake_llm_factory(responder)
    assert answer_without_tools(llm, _exhausted_history()).content == "plain answer"
    assert len(attempts) == 2 and attempts[1][-1] is PLAIN_TEXT_ONLY


def test_unrelated_errors_are_not_swallowed(fake_llm_factory):
    def responder(messages, bound):
        raise RuntimeError("Error code: 429 - rate limit reached")
    with pytest.raises(RuntimeError, match="429"):
        answer_without_tools(fake_llm_factory(responder), _exhausted_history())


def test_web_chatbot_node_answers_without_tools_once_searches_are_used_up(fake_llm_factory):
    @tool
    def tavily_search(query: str) -> str:
        """Search the web."""
        return "unused"

    llm = fake_llm_factory(lambda messages, bound: AIMessage(content="answer" if not bound else "STILL SEARCHING"))
    node = ChatbotWithToolNode(llm).create_chatbot([tavily_search])
    out = node({"messages": [SystemMessage(content="sys")] + _exhausted_history()})
    assert out["messages"][0].content == "answer"
    # and before the limit it still offers the tool
    fresh = node({"messages": [HumanMessage(content="hi")]})
    assert fresh["messages"][0].content == "STILL SEARCHING"


def test_invoke_plain_retries_when_groq_says_the_model_called_a_tool():
    from langchain_core.messages import AIMessage, SystemMessage
    from src.langgraphagenticai.nodes.tool_limits import invoke_plain

    class Flaky:
        def __init__(self, fails):
            self.fails, self.calls = fails, []

        def invoke(self, messages, **kwargs):
            self.calls.append((messages, kwargs))
            if len(self.calls) <= self.fails:
                raise RuntimeError("Error code: 400 - Tool choice is none, but model called a tool")
            return AIMessage(content="summary")

    llm = Flaky(fails=1)
    assert invoke_plain(llm, "Summarise this", max_tokens=100).content == "summary"
    first, second = llm.calls
    assert isinstance(second[0][0], SystemMessage) and "plain text" in second[0][0].content.lower()
    assert second[1] == {"max_tokens": 100}                         # settings are kept on the retry

    import pytest
    with pytest.raises(RuntimeError):
        invoke_plain(Flaky(fails=5), "x")                           # gives up after a few tries

    class Other:
        def invoke(self, messages, **kwargs):
            raise ValueError("network down")
    with pytest.raises(ValueError):
        invoke_plain(Other(), "x")                                  # other errors aren't retried
