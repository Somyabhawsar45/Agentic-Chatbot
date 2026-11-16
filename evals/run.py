"""
Run the Netra RAG evaluation.

    python -m evals.run                   # full run: needs GROQ_API_KEY (embeddings run locally)
    python -m evals.run --retrieval-only  # only checks retrieval: no keys needed
    python -m evals.run --judge           # also scores faithfulness with an LLM judge (extra LLM calls)

Keys are read from .env / environment (never printed). Exit code 1 if a metric is below
evals/thresholds.json, so CI can fail the build when quality drops.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from evals import runner
from evals.metrics import check_thresholds
from evals.report import to_markdown

ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL = "openai/gpt-oss-20b"


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", default=DEFAULT_MODEL, help="Groq model for answering (default: %(default)s)")
    p.add_argument("--judge-model", default=None, help="Groq model for the faithfulness judge (default: same as --model)")
    p.add_argument("--k", type=int, default=4, help="passages retrieved per question (the app uses 4)")
    p.add_argument("--limit", type=int, default=None, help="only run the first N questions")
    p.add_argument("--retrieval-only", action="store_true", help="skip the LLM; score retrieval only")
    p.add_argument("--judge", action="store_true", help="score faithfulness with an LLM judge")
    p.add_argument("--pause", type=float, default=0.0, help="seconds to wait between questions (rate limits)")
    p.add_argument("--out", default=str(ROOT / "results"), help="folder for latest.json / latest.md")
    p.add_argument("--no-thresholds", action="store_true", help="don't fail on thresholds.json")
    return p.parse_args(argv)


def missing_keys(args) -> list:
    from src.langgraphagenticai.rag import pdf_rag_utils
    needs_hf = pdf_rag_utils.embedding_provider() != "fastembed"   # local embeddings need no HF token
    needed = (["HUGGINGFACEHUB_API_TOKEN"] if needs_hf else []) + ([] if args.retrieval_only else ["GROQ_API_KEY"])
    return [k for k in needed if not os.environ.get(k)]


def main(argv=None) -> int:
    args = parse_args(argv)
    for stream in (sys.stdout, sys.stderr):  # Windows consoles default to cp1252 and choke on ✅/❌
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    from src.langgraphagenticai.settings import load_settings
    load_settings()  # .env -> environment

    missing = missing_keys(args)
    if missing:
        print(f"Missing keys: {', '.join(missing)}. Put them in a local .env file (never commit it).", file=sys.stderr)
        return 2

    from src.langgraphagenticai.rag import pdf_rag_utils
    embeddings = pdf_rag_utils.get_embeddings()
    try:  # fail fast with a readable message instead of a traceback halfway through
        embeddings.embed_query("preflight check")
    except Exception as e:
        hint = ""
        if "401" in str(e):
            hint = (" HuggingFace rejected the token (401): re-copy the FULL token (about 37 characters, "
                    "starting with hf_) or create a new one at huggingface.co/settings/tokens.")
        elif "402" in str(e):
            hint = (" HuggingFace has no free Inference credits left (402). Use the free local embeddings "
                    "instead: `pip install fastembed` and remove EMBEDDINGS_PROVIDER=huggingface.")
        print(f"Embedding check failed: {type(e).__name__}.{hint}", file=sys.stderr)
        return 2

    llm = judge_llm = None
    if not args.retrieval_only:
        from langchain_groq import ChatGroq
        key = os.environ["GROQ_API_KEY"]
        llm = ChatGroq(api_key=key, model=args.model, temperature=0)
        if args.judge:
            judge_llm = ChatGroq(api_key=key, model=args.judge_model or args.model, temperature=0)

    cases = runner.load_cases()[: args.limit]
    print(f"Running {len(cases)} questions" + (" (retrieval only)" if args.retrieval_only else f" with {args.model}") + "...")

    def progress(r):
        outcome_value = next((r[k] for k in ("correct", "abstained", "retrieval_hit") if k in r), None)
        status = "ERROR" if r.get("error") else ("-" if outcome_value is None else "ok" if outcome_value else "MISS")
        print(f"  {r['id']:>4}  {status:<5} {r.get('latency_s', 0):5.1f}s  {r['question'][:60]}")

    outcome = runner.run_eval(llm, embeddings, cases, k=args.k, judge_llm=judge_llm,
                              on_case=progress, pause_s=args.pause)
    summary, results = outcome["summary"], outcome["results"]

    failures = None
    if not args.no_thresholds:
        thresholds = json.loads((ROOT / "thresholds.json").read_text(encoding="utf-8"))
        failures = check_thresholds(summary, thresholds)

    meta = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "model": None if args.retrieval_only else args.model,
        "embeddings": pdf_rag_utils.embedding_label(),
    }
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "latest.json").write_text(
        json.dumps({"meta": meta, "summary": summary, "results": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    markdown = to_markdown(summary, results, meta, failures)
    (out / "latest.md").write_text(markdown, encoding="utf-8")

    print("\n" + markdown.split("## Per question")[0])
    print(f"Saved {out / 'latest.md'} and latest.json")
    if failures:
        print("FAILED thresholds:\n  " + "\n  ".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
