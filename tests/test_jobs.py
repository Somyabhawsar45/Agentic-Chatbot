"""
Background jobs: long graphs keep running when the page reruns, and the worker saves the answer itself.
"""
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from src.langgraphagenticai import jobs
from src.langgraphagenticai.database import db_utils
from src.langgraphagenticai.graph.graph_builder import GraphBuilder
from src.langgraphagenticai.nodes import research_nodes
from src.langgraphagenticai.ui.streamlitui.components import ResearchProgress
from tests.test_deep_research import FakeTavilyClient, _responder


def _conversation(usecase="AI News"):
    user_id = db_utils.create_user(f"u{usecase[:3]}", "Tester", f"{usecase[:3]}@example.com", "hash")
    return db_utils.create_conversation(user_id, usecase, "test")


class FakeGraph:
    """Yields the given 'updates' events; raises `error` at the end if set."""

    def __init__(self, events, error=None):
        self.events, self.error, self.calls = events, error, []

    def stream(self, inputs, config=None, stream_mode=None):
        self.calls.append((inputs, stream_mode))
        yield from self.events
        if self.error:
            raise self.error


def test_job_finishes_and_saves_the_answer_itself():
    convo = _conversation()
    graph = FakeGraph([
        {"fetch_news": {"news_data": [{"title": "a"}]}},
        {"save_result": {"messages": [AIMessage(content="# Daily AI News\n- item")]}},
    ])
    job = jobs.start(graph, {"messages": [HumanMessage(content="daily")]}, {"run_id": "r1"}, convo, "AI News")
    assert job.wait(5)
    snap = job.snapshot()
    assert snap["status"] == "done" and snap["answer"].startswith("# Daily AI News")
    assert len(snap["trace"]) == 2 and "fetch_news" in snap["trace"][0]
    assert db_utils.get_messages(convo)[-1] == ("assistant", "# Daily AI News\n- item")   # saved by the worker
    assert jobs.latest_for(convo) is job and jobs.get(job.id) is job and job.run_id == "r1"
    assert graph.calls[0][1] == "updates"


def test_errors_are_friendly_and_nothing_is_saved():
    convo = _conversation()
    graph = FakeGraph([{"fetch_news": {"news_data": []}}],
                      error=RuntimeError("Error code: 429 - rate limit. Please try again in 7.2s"))
    job = jobs.start(graph, {}, {}, convo, "AI News")
    assert job.wait(5)
    snap = job.snapshot()
    assert snap["status"] == "error" and "about 7 seconds" in snap["error"]
    assert db_utils.get_messages(convo) == []


def test_a_run_without_an_answer_is_an_error():
    convo = _conversation()
    job = jobs.start(FakeGraph([{"fetch_news": {"news_data": []}}]), {}, {}, convo, "AI News")
    assert job.wait(5) and job.snapshot()["status"] == "error"


def test_latest_job_per_conversation():
    convo = _conversation()
    first = jobs.start(FakeGraph([{"save_result": {"messages": [AIMessage(content="one")]}}]), {}, {}, convo, "AI News")
    first.wait(5)
    second = jobs.start(FakeGraph([{"save_result": {"messages": [AIMessage(content="two")]}}]), {}, {}, convo, "AI News")
    second.wait(5)
    assert jobs.latest_for(convo) is second
    assert jobs.latest_for(None) is None and jobs.latest_for(987654) is None


# ---------------- the real Deep Research graph (fake LLM + fake search) ----------------

def _research_graph(fake_llm_factory, monkeypatch):
    monkeypatch.setattr(research_nodes, "TavilyClient", FakeTavilyClient)
    llm = fake_llm_factory(_responder("APPROVED"))
    return GraphBuilder(llm, tavily_api_key="test-key").setup_graph("Deep Research")


def test_research_pauses_for_review_then_resumes_to_a_saved_report(fake_llm_factory, monkeypatch):
    convo = _conversation("Deep Research")
    graph = _research_graph(fake_llm_factory, monkeypatch)
    config = {"configurable": {"thread_id": "job-research-1"}}

    job = jobs.start(graph, {"messages": [HumanMessage(content="Small modular reactors")]}, config, convo,
                     "Deep Research", thread_id="job-research-1", progress=ResearchProgress())
    assert job.wait(10)
    snap = job.snapshot()
    assert snap["status"] == "paused" and len(snap["plan"]) == 3
    assert "Waiting for you" in snap["progress_html"]
    assert db_utils.get_messages(convo) == []                         # nothing saved while waiting

    plan = snap["plan"][:2]                                            # the user removed one question
    resumed = jobs.start(graph, Command(resume={"plan": plan}), config, convo, "Deep Research",
                         thread_id="job-research-1", progress=ResearchProgress(total=len(plan), resumed=True))
    assert resumed.wait(10)
    done = resumed.snapshot()
    assert done["status"] == "done" and done["answer"].startswith("# Report")
    assert len(done["sources"]) == 2 and "Report ready" in done["progress_html"]
    assert db_utils.get_messages(convo)[-1][1].startswith("# Report")
    assert jobs.latest_for(convo) is resumed


def test_research_with_auto_approve_never_pauses(fake_llm_factory, monkeypatch):
    convo = _conversation("Deep Research")
    graph = _research_graph(fake_llm_factory, monkeypatch)
    job = jobs.start(graph, {"messages": [HumanMessage(content="Solid-state batteries")]},
                     {"configurable": {"thread_id": "job-research-2"}}, convo, "Deep Research",
                     thread_id="job-research-2", progress=ResearchProgress(), auto_approve=True)
    assert job.wait(10)
    snap = job.snapshot()
    assert snap["status"] == "done" and snap["answer"].startswith("# Report")
    assert "Report ready" in snap["progress_html"]


def test_cancel_only_affects_a_waiting_job(fake_llm_factory, monkeypatch):
    convo = _conversation("Deep Research")
    graph = _research_graph(fake_llm_factory, monkeypatch)
    job = jobs.start(graph, {"messages": [HumanMessage(content="Topic")]},
                     {"configurable": {"thread_id": "job-research-3"}}, convo, "Deep Research",
                     progress=ResearchProgress())
    job.wait(10)
    jobs.cancel(job)
    assert job.snapshot()["status"] == "cancelled"


class BlockingGraph:
    """Holds its run open until `release` is set, then answers."""

    def __init__(self):
        import threading
        self.started, self.release = threading.Event(), threading.Event()

    def stream(self, inputs, config=None, stream_mode=None):
        self.started.set()
        self.release.wait(5)
        yield {"save_result": {"messages": [AIMessage(content="done")]}}


def test_only_a_few_runs_work_at_once_and_the_rest_wait_in_line(monkeypatch):
    import time
    monkeypatch.setenv("MAX_BACKGROUND_RUNS", "1")
    first_graph, second_graph = BlockingGraph(), BlockingGraph()
    first = jobs.start(first_graph, {}, {}, _conversation("Deep Research"), "Deep Research")
    assert first_graph.started.wait(5)
    second = jobs.start(second_graph, {}, {}, _conversation("AI News"), "AI News")

    deadline = time.time() + 5
    while second.snapshot()["queued"] != 1 and time.time() < deadline:
        time.sleep(0.05)
    assert second.snapshot()["queued"] == 1 and second.snapshot()["status"] == "running"
    assert not second_graph.started.is_set()          # still waiting for its turn
    assert jobs.running_count() == 1

    first_graph.release.set()
    assert first.wait(5) and second_graph.started.wait(5)   # the slot passes to the next in line
    assert second.snapshot()["queued"] == 0
    second_graph.release.set()
    assert second.wait(5) and second.snapshot()["status"] == "done"
    assert jobs.running_count() == 0                  # every slot is given back
