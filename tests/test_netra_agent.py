"""The Netra Agent graph end-to-end, with a fake LLM (no API calls)."""
import itertools

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from src.langgraphagenticai.graph.graph_builder import GraphBuilder
from src.langgraphagenticai.memory.checkpointer import agent_config
from src.langgraphagenticai.nodes.tool_limits import MAX_TOOL_ROUNDS
from src.langgraphagenticai.rag import pdf_rag_utils


def test_agent_remembers_previous_turns(fake_llm_factory):
    counter = itertools.count(1)
    llm = fake_llm_factory(lambda messages, bound: AIMessage(content=f"reply {next(counter)}"))
    graph = GraphBuilder(llm).setup_graph("Netra Agent")
    config = agent_config(1)

    graph.invoke({"messages": [HumanMessage(content="My name is Somya")]}, config)
    # Second turn sends ONLY the new message; the checkpointer must supply the rest
    graph.invoke({"messages": [HumanMessage(content="What is my name?")]}, config)

    second_call_messages, _ = llm.calls[-1]
    texts = [m.content for m in second_call_messages]
    assert "My name is Somya" in texts
    assert "reply 1" in texts
    assert len(graph.get_state(config).values["messages"]) == 4


def test_threads_are_isolated(fake_llm_factory):
    llm = fake_llm_factory(lambda messages, bound: AIMessage(content="ok"))
    graph = GraphBuilder(llm).setup_graph("Netra Agent")
    graph.invoke({"messages": [HumanMessage(content="secret A")]}, agent_config(1))
    graph.invoke({"messages": [HumanMessage(content="hello")]}, agent_config(2))

    texts = [m.content for m in llm.calls[-1][0]]
    assert "secret A" not in texts


def test_agent_uses_pdf_tool_then_is_forced_to_answer(fake_llm_factory, monkeypatch):
    passage = {"text": "Revenue grew 20% in 2025.", "page": 3, "source": "report.pdf"}
    monkeypatch.setattr(pdf_rag_utils, "has_index", lambda cid: True)
    monkeypatch.setattr(pdf_rag_utils, "retrieve", lambda cid, q, k=4: [passage])

    ids = itertools.count(1)

    def responder(messages, bound):
        if not bound.get("tools"):       # the forced final answer: asked with NO tools declared
            return AIMessage(content="Revenue grew 20% (p. 3).")
        # a "stubborn" model that always wants to search again
        return AIMessage(content="", tool_calls=[
            {"name": "search_pdf", "args": {"query": "revenue"}, "id": f"call_{next(ids)}"}
        ])

    llm = fake_llm_factory(responder)
    graph = GraphBuilder(llm).setup_graph("Netra Agent")
    result = graph.invoke({"messages": [HumanMessage(content="How did revenue change?")]}, agent_config(5))

    messages = result["messages"]
    assert messages[-1].content == "Revenue grew 20% (p. 3)."
    assert sum(1 for m in messages if isinstance(m, AIMessage) and m.tool_calls) == MAX_TOOL_ROUNDS

    tool_messages = [m for m in messages if isinstance(m, ToolMessage)]
    assert "page 3" in tool_messages[0].content
    assert tool_messages[0].artifact == [passage]          # used for the citation box
    assert "search_pdf" in llm.calls[0][1]["tools"]       # tool offered because a PDF is attached

    # the final answer was requested with no tools and a plain-text history (no tool-call objects left)
    final_messages, final_bound = llm.calls[-1]
    assert not final_bound.get("tools") and "tool_choice" not in final_bound
    assert not any(isinstance(m, ToolMessage) or getattr(m, "tool_calls", None) for m in final_messages)
    assert any("[Result from search_pdf]" in str(m.content) and "page 3" in str(m.content) for m in final_messages)
