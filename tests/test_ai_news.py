from langchain_core.messages import AIMessage, HumanMessage

from src.langgraphagenticai.graph.graph_builder import GraphBuilder
from src.langgraphagenticai.nodes import ai_news_node


class FakeTavilyClient:
    def __init__(self, api_key=None):
        self.queries = []

    def search(self, **kwargs):
        self.queries.append(kwargs)
        return {"results": [{"title": f"News {i}", "content": "text", "url": f"https://n{i}.com"} for i in range(3)]}


def _graph(fake_llm_factory, monkeypatch):
    monkeypatch.setattr(ai_news_node, "TavilyClient", FakeTavilyClient)
    llm = fake_llm_factory(lambda messages, bound: AIMessage(content="- summary"))
    return GraphBuilder(llm, tavily_api_key="test-key").setup_graph("AI News"), llm


def test_daily_news_report(fake_llm_factory, monkeypatch):
    graph, llm = _graph(fake_llm_factory, monkeypatch)
    result = graph.invoke({"messages": [HumanMessage(content="Daily")]})

    assert result["messages"][-1].content.startswith("# Daily AI News Summary")
    assert len(result["news_data"]) == 3
    assert len(llm.calls) == 3 + 1          # map: one call per article, reduce: one call


def test_invalid_timeframe_is_reported(fake_llm_factory, monkeypatch):
    graph, llm = _graph(fake_llm_factory, monkeypatch)
    result = graph.invoke({"messages": [HumanMessage(content="yearly")]})
    assert "Invalid timeframe" in result["messages"][-1].content
    assert llm.calls == []
