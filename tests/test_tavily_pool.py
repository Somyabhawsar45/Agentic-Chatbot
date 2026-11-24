"""Several Tavily keys: the next one takes over when a key runs out; a visitor's own key stays alone."""
import json

import pytest
from tavily.errors import InvalidAPIKeyError, UsageLimitExceededError

from src.langgraphagenticai.tools import search_tool, tavily_pool


class FakeClient:
    """Fails for keys listed in `broken`, answers for the others; records every call."""
    calls = []
    broken = {}

    def __init__(self, api_key=None):
        self.api_key = api_key

    def search(self, **kwargs):
        FakeClient.calls.append(self.api_key)
        if self.api_key in FakeClient.broken:
            raise FakeClient.broken[self.api_key]
        return {"results": [{"title": "t", "url": "https://example.com/a", "content": "c"}], "key": self.api_key}


@pytest.fixture(autouse=True)
def keys(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "t1")
    monkeypatch.setenv("TAVILY_API_KEYS", "t2, t3 ,t1")
    FakeClient.calls, FakeClient.broken = [], {}


def test_pool_order_and_visitor_key_alone():
    assert tavily_pool.builtin_tavily_keys() == ["t1", "t2", "t3"]
    assert tavily_pool.tavily_key_pool(None) == ["t1", "t2", "t3"]
    assert tavily_pool.tavily_key_pool("t2") == ["t1", "t2", "t3"]          # one of the app's keys
    assert tavily_pool.tavily_key_pool("visitor-key") == ["visitor-key"]   # never mixed with ours


def test_moves_to_the_next_key_and_stays_there():
    FakeClient.broken = {"t1": UsageLimitExceededError("out of credits"), "t2": InvalidAPIKeyError("bad key")}
    client = tavily_pool.RotatingTavilyClient(None, client_factory=FakeClient)
    assert client.search(query="q")["key"] == "t3"
    assert FakeClient.calls == ["t1", "t2", "t3"]
    FakeClient.calls = []
    assert client.search(query="q2")["key"] == "t3"
    assert FakeClient.calls == ["t3"]                     # doesn't retry the used-up keys every time


def test_all_keys_out_raises_the_last_error():
    FakeClient.broken = {k: UsageLimitExceededError("out") for k in ("t1", "t2", "t3")}
    with pytest.raises(UsageLimitExceededError):
        tavily_pool.RotatingTavilyClient(None, client_factory=FakeClient).search(query="q")


def test_other_errors_are_not_swallowed():
    FakeClient.broken = {"t1": ValueError("bug")}
    with pytest.raises(ValueError):
        tavily_pool.RotatingTavilyClient(None, client_factory=FakeClient).search(query="q")


def test_web_search_tool_keeps_its_name_and_json_results(monkeypatch):
    real = tavily_pool.RotatingTavilyClient
    monkeypatch.setattr(search_tool, "RotatingTavilyClient", lambda key: real(key, client_factory=FakeClient))
    (search,) = search_tool.get_tools(None)
    assert search.name == "tavily_search"
    # called the way the agent calls it: a tool call in, a ToolMessage out
    out = search.invoke({"name": "tavily_search", "args": {"query": "groq", "time_range": "week"},
                         "id": "c1", "type": "tool_call"})
    assert json.loads(out.content)["results"][0]["url"] == "https://example.com/a"   # the UI's source icons read this
    assert FakeClient.calls == ["t1"]
