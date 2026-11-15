from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from src.langgraphagenticai.nodes.tool_limits import MAX_TOOL_ROUNDS, tool_rounds_this_turn, tools_exhausted


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


def test_exhausted_after_max_rounds():
    messages = [HumanMessage(content="q")]
    for i in range(MAX_TOOL_ROUNDS):
        messages += [_tool_call(i), ToolMessage(content="r", tool_call_id=f"c{i}")]
    assert tools_exhausted(messages)
