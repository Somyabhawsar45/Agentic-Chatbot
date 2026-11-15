"""Long-term memory: facts saved in one conversation are known in every other one."""
import itertools

from langchain_core.messages import AIMessage, HumanMessage

from src.langgraphagenticai.database import db_utils
from src.langgraphagenticai.graph.graph_builder import GraphBuilder
from src.langgraphagenticai.memory.checkpointer import agent_config


def test_memory_store_basics():
    uid = db_utils.create_user("u1", "User One", "u1@example.com", "hash")
    assert db_utils.add_memory(uid, "Name is Somya")
    assert not db_utils.add_memory(uid, "  name is   somya ")      # duplicate (case/space-insensitive)
    assert not db_utils.add_memory(uid, "   ")                     # empty
    assert [m["content"] for m in db_utils.get_memories(uid)] == ["Name is Somya"]

    other = db_utils.create_user("u2", "User Two", "u2@example.com", "hash")
    assert db_utils.get_memories(other) == []                       # private per user

    db_utils.delete_memory(uid, db_utils.get_memories(uid)[0]["id"])
    assert db_utils.get_memories(uid) == []


def test_agent_saves_a_fact_and_recalls_it_in_another_chat(fake_llm_factory):
    uid = db_utils.create_user("somya", "Somya", "s@example.com", "hash")
    ids = itertools.count(1)

    def responder(messages, bound):
        last = messages[-1]
        if isinstance(last, HumanMessage) and "my name is" in last.content.lower() and "save_memory" in bound.get("tools", []):
            return AIMessage(content="", tool_calls=[
                {"name": "save_memory", "args": {"fact": "Name is Somya"}, "id": f"m{next(ids)}"}
            ])
        return AIMessage(content="ok")

    llm = fake_llm_factory(responder)
    graph = GraphBuilder(llm).setup_graph("Netra Agent")

    # chat 1: the user introduces themself -> agent calls save_memory
    graph.invoke({"messages": [HumanMessage(content="Hi, my name is Somya")]}, agent_config(1, uid))
    assert [m["content"] for m in db_utils.get_memories(uid)] == ["Name is Somya"]

    # chat 2 (different thread): the fact is in the system prompt
    graph.invoke({"messages": [HumanMessage(content="What is my name?")]}, agent_config(2, uid))
    system_prompt = llm.calls[-1][0][0].content
    assert "Name is Somya" in system_prompt


def test_feedback_and_rename():
    uid = db_utils.create_user("u3", "User Three", "u3@example.com", "hash")
    cid = db_utils.create_conversation(uid, "Netra Agent", "Old title")
    db_utils.rename_conversation(cid, "New title")
    assert db_utils.get_conversations(uid, "Netra Agent")[0]["title"] == "New title"

    db_utils.save_feedback(cid, 1, 1)
    db_utils.save_feedback(cid, 1, 0)              # last click wins
    db_utils.save_feedback(cid, 3, 1)
    assert db_utils.get_feedback(cid) == {1: 0, 3: 1}
