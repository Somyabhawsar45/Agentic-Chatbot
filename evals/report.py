"""Turn eval results into a markdown report (also used as the GitHub Actions job summary)."""

_LABELS = [
    ("retrieval_hit_rate", "Retrieval hit rate", "right page in the top-k passages"),
    ("retrieval_top1", "Retrieval top-1", "the very first passage is from the right page (stricter)"),
    ("mrr", "Retrieval MRR", "how high the right page ranked"),
    ("answer_accuracy", "Answer accuracy", "answer contains every expected fact"),
    ("citation_rate", "Citation rate", "answer cites the correct page"),
    ("abstention_rate", "Abstention rate", "says 'not in the document' instead of guessing"),
    ("faithfulness", "Faithfulness (LLM judge)", "every claim supported by retrieved text"),
]


def _pct(value):
    return "n/a" if value is None else f"{value * 100:.0f}%"


def _mark(value):
    return "n/a" if value is None else ("✅" if value else "❌")


def to_markdown(summary: dict, results: list, meta: dict, failures: list = None) -> str:
    lines = ["# Netra RAG evaluation", ""]
    lines.append(" · ".join(f"**{k}:** {v}" for k, v in meta.items() if v not in (None, "")))
    lines += [
        "",
        f"{summary['answerable']} answerable + {summary['unanswerable']} unanswerable questions "
        f"on a {summary.get('chunks_indexed', '?')}-chunk sample report (top-{summary.get('k', '?')} retrieval).",
        "",
        "| Metric | Score | Meaning |",
        "|---|---|---|",
    ]
    for key, label, meaning in _LABELS:
        value = summary.get(key)
        if value is not None:
            lines.append(f"| {label} | **{value:.2f}**" if key == "mrr" else f"| {label} | **{_pct(value)}**")
            lines[-1] += f" | {meaning} |"
    if summary.get("avg_latency_s") is not None:
        lines.append(f"| Latency | **{summary['avg_latency_s']:.2f}s** avg · {summary['p95_latency_s']:.2f}s p95 | per question |")
    if summary.get("avg_tokens"):
        lines.append(f"| Tokens | **{summary['avg_tokens']:.0f}** avg | per question |")
    if summary.get("errors"):
        lines.append(f"| Errors | **{summary['errors']}** | questions that raised an exception |")

    if failures is not None:
        lines += ["", "## Thresholds", ""]
        lines += [f"- ❌ {f}" for f in failures] if failures else ["- ✅ all metrics meet their minimum"]

    lines += ["", "## Per question", "", "| ID | Question | Retrieved | Correct | Cited | Abstained | Time |", "|---|---|---|---|---|---|---|"]
    for r in results:
        question = r["question"] if len(r["question"]) <= 60 else r["question"][:57] + "..."
        lines.append(
            f"| {r['id']} | {question} | {_mark(r.get('retrieval_hit'))} | {_mark(r.get('correct'))} | "
            f"{_mark(r.get('cited'))} | {_mark(r.get('abstained'))} | {r.get('latency_s', 0):.1f}s |"
        )

    bad = [r for r in results if r.get("error") or r.get("correct") is False or r.get("abstained") is False
           or r.get("retrieval_hit") is False]
    if bad:
        lines += ["", "## Failures to look at", ""]
        for r in bad:
            lines.append(f"**{r['id']}** — {r['question']}")
            if r.get("error"):
                lines.append(f"- error: `{r['error']}`")
            else:
                lines.append(f"- retrieved pages: {r.get('retrieved_pages')}")
                answer = (r.get("answer") or "").replace("\n", " ")
                if answer:
                    lines.append(f"- answer: {answer[:300]}{'...' if len(answer) > 300 else ''}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"
