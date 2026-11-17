import json

from langchain_core.messages import AIMessage, ToolMessage

from src.langgraphagenticai.ui.streamlitui.display_result import (
    dedupe_citations,
    describe_step,
    friendly_error,
    parse_tavily_results,
)


def test_friendly_error_for_groq_rate_limit():
    raw = ("Error code: 429 - {'error': {'message': 'Rate limit reached for model openai/gpt-oss-20b ... "
           "on tokens per minute (TPM): Limit 8000, Used 7888, Requested 2557. Please try again in 18.3375s.', "
           "'code': 'rate_limit_exceeded'}}")
    message = friendly_error(RuntimeError(raw))
    assert "rate limit" in message and "about 18 seconds" in message and "org_" not in message and "{" not in message
    assert "about 1 seconds" not in friendly_error(RuntimeError("429 rate limit. Please try again in 6.4ms"))
    assert "a minute" in friendly_error(RuntimeError("429 Too Many Requests"))


def test_friendly_error_for_bad_key_and_unknown_errors():
    assert "key was rejected" in friendly_error(RuntimeError("Error code: 401 - Invalid API Key"))
    assert friendly_error(ValueError("boom")) == "Something went wrong: boom"


def test_parse_tavily_results():
    msg = ToolMessage(content=json.dumps({"results": [{"title": "T", "url": "https://x.com"}]}),
                      tool_call_id="1", name="tavily_search")
    assert parse_tavily_results(msg) == [{"title": "T", "url": "https://x.com"}]
    assert parse_tavily_results(ToolMessage(content="not json", tool_call_id="2")) == []


def test_describe_step_shows_real_tool_calls():
    call = AIMessage(content="", tool_calls=[{"name": "tavily_search", "args": {"query": "groq news"}, "id": "c1"}])
    lines = describe_step("agent", {"messages": [call]}, 1.25)
    assert "tavily_search" in lines[0] and "groq news" in lines[0]
    assert lines[-1].endswith("1.2s") or lines[-1].endswith("1.3s")


def test_describe_step_for_pipeline_state():
    lines = describe_step("planner", {"plan": ["q1", "q2"]}, 0.5)
    assert "q1" in lines[0] and "q2" in lines[0]
    lines = describe_step("researcher", {"findings": [{"query": "q1", "sources": [{}, {}]}]}, 0.5)
    assert "2 sources" in lines[0]


def test_dedupe_citations():
    c = {"text": "same passage", "page": 2}
    assert len(dedupe_citations([c, dict(c), {"text": "other", "page": 2}])) == 2
