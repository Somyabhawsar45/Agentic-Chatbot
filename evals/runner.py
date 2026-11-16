"""
Runs the golden questions through the app's real PDF-RAG code path
(chunking -> FAISS -> PdfRagNode) and scores each answer.

`embeddings` and `llm` are injected, so the same code runs offline in pytest
(fake embeddings + fake LLM) and for real from `python -m evals.run`.
"""
import json
import re
import time
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from evals import metrics

DATA_DIR = Path(__file__).parent / "data"
EVAL_CONVERSATION_ID = "eval-meridian"   # not a numeric DB id -> served from the in-memory index cache
_PAGE_MARKER = re.compile(r"^=== PAGE (\d+) ===\s*$", re.MULTILINE)


def load_pages(path: Path = DATA_DIR / "meridian_report.txt") -> list:
    """Sample report -> list of page texts (index 0 = page 1)."""
    parts = _PAGE_MARKER.split(Path(path).read_text(encoding="utf-8"))
    # split() gives ['', '1', text, '2', text, ...]
    pages = {int(parts[i]): parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}
    return [pages[n] for n in sorted(pages)]


def load_cases(path: Path = DATA_DIR / "golden.jsonl") -> list:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def build_index(embeddings, pages: list, conversation_id: str = EVAL_CONVERSATION_ID) -> int:
    """Index the pages exactly like the app does and register them for retrieval. Returns chunk count."""
    from langchain_community.vectorstores import FAISS
    from src.langgraphagenticai.rag import pdf_rag_utils

    texts, metadatas = pdf_rag_utils.chunk_pages(pages, source="meridian_report.txt")
    vectorstore = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
    pdf_rag_utils._cache_put(str(conversation_id), vectorstore)
    return len(texts)


class UsageTracker:
    """Wraps an LLM and adds up token usage (PdfRagNode drops usage_metadata from its reply)."""

    def __init__(self, llm):
        self.llm = llm
        self.total_tokens = 0

    def invoke(self, *args, **kwargs):
        response = self.llm.invoke(*args, **kwargs)
        usage = getattr(response, "usage_metadata", None) or {}
        self.total_tokens += usage.get("total_tokens", 0) or 0
        return response

    def __getattr__(self, name):
        return getattr(self.llm, name)


def judge_faithfulness(judge_llm, context: str, answer: str) -> bool:
    """LLM-as-judge: is every claim in the answer supported by the retrieved context?"""
    reply = judge_llm.invoke([
        SystemMessage(content=(
            "You are a strict fact-checker. Given CONTEXT and an ANSWER, reply with exactly YES if every "
            "factual claim in the ANSWER is supported by the CONTEXT, otherwise reply with exactly NO."
        )),
        HumanMessage(content=f"CONTEXT:\n{context}\n\nANSWER:\n{answer}"),
    ])
    return str(getattr(reply, "content", reply)).strip().upper().startswith("YES")


def run_case(case: dict, node, k: int, judge_llm=None, tracker: UsageTracker = None) -> dict:
    from src.langgraphagenticai.rag import pdf_rag_utils

    result = {"id": case["id"], "type": case["type"], "question": case["question"]}
    started = time.perf_counter()
    tokens_before = tracker.total_tokens if tracker else 0
    try:
        if node is None:   # retrieval-only run: no LLM
            passages = pdf_rag_utils.retrieve(EVAL_CONVERSATION_ID, case["question"], k=k)
            answer = ""
        else:
            output = node.process({"messages": [HumanMessage(content=case["question"])]})
            passages = output.get("citations", [])
            answer = output["messages"][-1].content
        result["latency_s"] = round(time.perf_counter() - started, 3)
    except Exception as e:  # keep going: one failed call shouldn't hide the other results
        result.update(error=f"{type(e).__name__}: {e}", latency_s=round(time.perf_counter() - started, 3))
        return result

    result["answer"] = answer
    result["retrieved_pages"] = [p.get("page") for p in passages]
    if tracker:
        result["total_tokens"] = tracker.total_tokens - tokens_before

    if case["type"] == "answerable":
        hit, rank = metrics.retrieval_score(result["retrieved_pages"], case["expected_pages"])
        result["retrieval_hit"], result["reciprocal_rank"] = hit, rank
        if node is not None:
            result["correct"] = metrics.all_facts_present(answer, case["expected_facts"])
            result["cited"] = metrics.cited_page(answer, case["expected_pages"])
            if judge_llm is not None:
                context = pdf_rag_utils.format_passages(passages)
                result["faithful"] = judge_faithfulness(judge_llm, context, answer)
    elif node is not None:
        result["abstained"] = metrics.is_abstention(answer)
    return result


def run_eval(llm, embeddings, cases: list, k: int = 4, judge_llm=None, pages: list = None,
             on_case=None, pause_s: float = 0.0) -> dict:
    """
    Returns {"summary": {...}, "results": [...]}. Pass llm=None for a retrieval-only run.
    `on_case(result)` is called after each question (for progress output).
    """
    from src.langgraphagenticai.nodes.pdf_rag_node import PdfRagNode

    chunks = build_index(embeddings, pages or load_pages())
    tracker = UsageTracker(llm) if llm is not None else None
    node = PdfRagNode(tracker, EVAL_CONVERSATION_ID) if tracker else None

    results = []
    for case in cases:
        result = run_case(case, node, k, judge_llm=judge_llm, tracker=tracker)
        results.append(result)
        if on_case:
            on_case(result)
        if pause_s:
            time.sleep(pause_s)
    summary = metrics.aggregate(results)
    summary["chunks_indexed"] = chunks
    summary["k"] = k
    return {"summary": summary, "results": results}
