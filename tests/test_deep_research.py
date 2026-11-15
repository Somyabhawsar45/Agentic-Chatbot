from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from src.langgraphagenticai.graph.graph_builder import GraphBuilder
from src.langgraphagenticai.nodes import research_nodes
from src.langgraphagenticai.nodes.research_nodes import parse_questions


class FakeTavilyClient:
    def __init__(self, api_key=None):
        pass

    def search(self, query, **kwargs):
        return {"results": [{"title": f"About {query}", "content": "facts", "url": f"https://src/{len(query)}"}]}


def _responder(critic_reply):
    def respond(messages, bound):
        system = messages[0].content
        if "research planner" in system:
            return AIMessage(content="1. history of topic\n2. latest news on topic\n- key numbers for topic")
        if "research assistant" in system:
            return AIMessage(content="- a fact (https://src/1)")
        if "report writer" in system:
            return AIMessage(content="# Report\nSummary...")
        if "strict reviewer" in system:
            return AIMessage(content=critic_reply)
        raise AssertionError(f"unexpected prompt: {system[:40]}")
    return respond


def _run(fake_llm_factory, monkeypatch, critic_reply, edited_plan=None):
    """Start research, check it pauses for human review, then resume with the (edited) plan."""
    monkeypatch.setattr(research_nodes, "TavilyClient", FakeTavilyClient)
    llm = fake_llm_factory(_responder(critic_reply))
    graph = GraphBuilder(llm, tavily_api_key="test-key").setup_graph("Deep Research")
    config = {"configurable": {"thread_id": "research-test"}}

    graph.invoke({"messages": [HumanMessage(content="Small modular reactors")]}, config)
    snapshot = graph.get_state(config)
    assert snapshot.next == ("human_review",)            # paused: waiting for the user
    assert len(snapshot.values["plan"]) == 3
    assert not any("research assistant" in msgs[0].content for msgs, _ in llm.calls)  # nobody researched yet

    plan = edited_plan if edited_plan is not None else snapshot.values["plan"]
    result = graph.invoke(Command(resume={"plan": plan}), config)
    writer_calls = sum(1 for msgs, _ in llm.calls if "report writer" in msgs[0].content)
    return result, writer_calls


def test_parse_questions_strips_numbering():
    assert parse_questions("1. alpha beta\n- gamma delta\n\n• epsilon zeta") == [
        "alpha beta", "gamma delta", "epsilon zeta"]


def test_parallel_researchers_then_approved_report(fake_llm_factory, monkeypatch):
    result, writer_calls = _run(fake_llm_factory, monkeypatch, "APPROVED")
    assert len(result["findings"]) == 3            # one per parallel researcher, merged
    assert result["messages"][-1].content.startswith("# Report")
    assert writer_calls == 1


def test_user_can_edit_the_plan(fake_llm_factory, monkeypatch):
    result, _ = _run(fake_llm_factory, monkeypatch, "APPROVED",
                     edited_plan=["my own question one", "my own question two"])
    assert result["plan"] == ["my own question one", "my own question two"]
    assert sorted(f["query"] for f in result["findings"]) == ["my own question one", "my own question two"]


def test_critic_triggers_at_most_one_revision(fake_llm_factory, monkeypatch):
    result, writer_calls = _run(fake_llm_factory, monkeypatch, "- add more numbers")
    assert writer_calls == 2                        # draft + one revision, then finalize
    assert result["messages"][-1].content.startswith("# Report")
