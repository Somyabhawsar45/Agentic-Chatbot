"""
Background runs for long graphs (Deep Research, AI News).

Streamlit stops a script run the moment the user clicks anything, so a 2-minute research run used to
die when you switched modes. These graphs now run in a worker thread instead: the page only *watches*
the job (an auto-refreshing fragment), and the worker writes the finished answer to the database
itself, so the report is there even if you were looking at another chat or another mode.

Rules that keep this safe:
  * the worker never touches Streamlit; it only updates its Job under the job's lock
  * one job registry per server process, keyed by job id and by conversation id
  * jobs live in memory: a server restart loses a running job (the UI then offers "Run again")
  * at most MAX_BACKGROUND_RUNS jobs work at once (default 3), first come first served; the rest
    wait in line (queue_position > 0) and start by themselves. A run waiting for plan approval
    doesn't hold a place.
"""
import threading
import time
import uuid
from dataclasses import dataclass, field

from langchain_core.messages import AIMessage
from langgraph.types import Command

from src.langgraphagenticai.database import db_utils
from src.langgraphagenticai.settings import max_background_runs
from src.langgraphagenticai.ui.streamlitui.components import ResearchProgress, describe_step, friendly_error

MAX_JOBS = 200                      # registry size cap (oldest finished jobs are dropped first)


@dataclass
class Job:
    id: str
    conversation_id: int
    usecase: str
    thread_id: str = None
    run_id: object = None            # LangSmith run id (for 👍/👎 feedback)
    status: str = "running"          # running | paused | done | error | cancelled
    trace: list = field(default_factory=list)
    progress: ResearchProgress = None
    answer: str = ""
    sources: list = field(default_factory=list)
    plan: list = field(default_factory=list)
    error: str = ""
    started: float = field(default_factory=time.time)
    finished: float = None
    queue_position: int = 0          # > 0 while waiting in line for a free slot
    delivered: bool = False          # the UI has put the answer into the open chat
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    finished_event: threading.Event = field(default_factory=threading.Event, repr=False)

    def snapshot(self) -> dict:
        """A consistent copy for the UI to render."""
        with self.lock:
            return {
                "status": self.status,
                "trace": list(self.trace),
                "progress_html": self.progress.html() if self.progress else "",
                "answer": self.answer,
                "sources": list(self.sources),
                "plan": list(self.plan),
                "error": self.error,
                "queued": self.queue_position,
                "elapsed": (self.finished or time.time()) - self.started,
            }

    def wait(self, timeout: float = None) -> bool:
        return self.finished_event.wait(timeout)


_registry_lock = threading.Lock()
_jobs = {}            # job id -> Job
_latest = {}          # conversation id -> job id of its most recent job


def get(job_id: str):
    with _registry_lock:
        return _jobs.get(job_id)


def latest_for(conversation_id):
    if conversation_id is None:
        return None
    with _registry_lock:
        job_id = _latest.get(conversation_id)
        return _jobs.get(job_id) if job_id else None


def _register(job: Job) -> None:
    with _registry_lock:
        _jobs[job.id] = job
        _latest[job.conversation_id] = job.id
        if len(_jobs) > MAX_JOBS:
            # drop the oldest finished jobs that are no longer anyone's latest
            latest_ids = set(_latest.values())
            removable = sorted((j for j in _jobs.values() if j.status != "running" and j.id not in latest_ids),
                               key=lambda j: j.started)
            for old in removable[: len(_jobs) - MAX_JOBS]:
                _jobs.pop(old.id, None)


def start(graph, inputs, config: dict, conversation_id: int, usecase: str, thread_id: str = None,
          progress: ResearchProgress = None, auto_approve: bool = False) -> Job:
    """Run `graph` on `inputs` in a background thread and return its Job immediately."""
    job = Job(id=uuid.uuid4().hex[:12], conversation_id=conversation_id, usecase=usecase,
              thread_id=thread_id, run_id=(config or {}).get("run_id"), progress=progress)
    _register(job)
    threading.Thread(target=_run, args=(job, graph, inputs, config, auto_approve),
                     name=f"netra-job-{job.id}", daemon=True).start()
    return job


def cancel(job: Job) -> None:
    """Cancel a job that is waiting for plan approval (a running graph can't be interrupted)."""
    with job.lock:
        if job.status == "paused":
            job.status = "cancelled"


# ---------------- the line: at most max_background_runs() jobs work at the same time ----------------
_slots = threading.Condition()
_active = 0
_waiting = []          # job ids, first come first served


def _take_slot(job: Job) -> None:
    """Block until it's this job's turn and a slot is free; keeps job.queue_position up to date."""
    global _active
    with _slots:
        _waiting.append(job.id)
        try:
            while _active >= max_background_runs() or _waiting[0] != job.id:
                with job.lock:
                    job.queue_position = _waiting.index(job.id) + 1
                _slots.wait(timeout=1.0)
        finally:
            _waiting.remove(job.id)
        _active += 1
    with job.lock:
        job.queue_position = 0


def _free_slot() -> None:
    global _active
    with _slots:
        _active = max(0, _active - 1)
        _slots.notify_all()


def running_count() -> int:
    with _slots:
        return _active


def _interrupt_plan(update_value) -> list:
    """The plan carried by a LangGraph interrupt (human review of the research plan)."""
    items = update_value if isinstance(update_value, (list, tuple)) else [update_value]
    for item in items:
        value = getattr(item, "value", item)
        if isinstance(value, dict) and "plan" in value:
            return list(value.get("plan") or [])
    return []


def _run(job: Job, graph, inputs, config: dict, auto_approve: bool) -> None:
    has_slot = False
    try:
        _take_slot(job)
        has_slot = True
        while True:
            paused_plan = None
            last_step = time.perf_counter()
            for update in graph.stream(inputs, config=config, stream_mode="updates"):
                for node, output in update.items():
                    if node == "__interrupt__":
                        paused_plan = _interrupt_plan(output)
                        continue
                    if not isinstance(output, dict):
                        continue
                    now = time.perf_counter()
                    lines = describe_step(node, output, now - last_step)
                    last_step = now
                    messages = output.get("messages", [])
                    messages = messages if isinstance(messages, list) else [messages]
                    with job.lock:
                        job.trace.extend(lines)
                        if job.progress is not None:
                            job.progress.update(node, output)
                        for finding in output.get("findings") or []:
                            job.sources.extend(finding.get("sources", []))
                        for m in messages:
                            if isinstance(m, AIMessage) and isinstance(m.content, str) and m.content:
                                job.answer = m.content

            if paused_plan is None:
                break
            if auto_approve:          # "Review the plan" switched off: carry on with the planner's plan
                inputs = Command(resume={"plan": paused_plan})
                with job.lock:
                    if job.progress is not None:
                        job.progress.update("human_review", {"plan": paused_plan})
                continue
            with job.lock:
                job.status, job.plan, job.finished = "paused", paused_plan, time.time()
                if job.progress is not None:
                    job.progress.pause()
            return

        if not job.answer:
            raise RuntimeError("The run finished without producing an answer.")
        # saved by the worker, so the answer exists even if nobody is looking at this chat
        db_utils.add_message(job.conversation_id, "assistant", job.answer)
        with job.lock:
            job.status, job.finished = "done", time.time()
    except Exception as e:
        with job.lock:
            job.status, job.error, job.finished = "error", friendly_error(e), time.time()
    finally:
        if has_slot:
            _free_slot()
        job.finished_event.set()
