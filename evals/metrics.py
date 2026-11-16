"""
Scoring for the Netra evaluation harness. Everything here is pure Python (no LLM calls),
so the scores are deterministic and cheap to compute.

Answerable questions are scored on:
  * retrieval  - did the passages the app retrieved include the right page? (hit, rank)
  * correct    - does the answer contain every expected fact?
  * cited      - does the answer cite the right page, e.g. "(p. 4)"?
Unanswerable questions (the document doesn't say) are scored on:
  * abstained  - did the answer admit the document doesn't contain it, instead of guessing?
"""
import re
from statistics import mean

ABSTAIN_PATTERNS = [
    r"\bnot (?:mentioned|stated|specified|provided|available|included|given|covered|found|contained)\b",
    r"\bno (?:information|mention|data|details|record|reference)\b",
    r"\b(?:does not|doesn't|do not|don't|did not|didn't|cannot|can't|could not|couldn't|unable to)\b"
    r"[^.\n]{0,60}\b(?:say|state|mention|specify|provide|contain|include|find|know|answer|determine|have)\b",
    r"\b(?:isn't|is not|aren't|are not|wasn't|was not)\b[^.\n]{0,40}\b(?:in|within|mentioned|stated|provided|available|covered)\b",
    r"\bi don't know\b",
    r"\bnot (?:in|within) the (?:document|context|report|passages?|provided)\b",
]
_ABSTAIN_RE = re.compile("|".join(ABSTAIN_PATTERNS), re.IGNORECASE)


_PUNCT_FOLD = str.maketrans({
    "‘": "'", "’": "'", "ʼ": "'",                              # curly apostrophes
    "“": '"', "”": '"',                                              # curly quotes
    **{c: "-" for c in "‐‑‒–—―−"},          # hyphens / dashes / minus
    " ": " ", " ": " ", " ": " ",                               # odd spaces
})


def fold_punctuation(text: str) -> str:
    """Models often write ’ and ‑ (non-breaking hyphen); fold them to plain ASCII before matching."""
    return str(text).translate(_PUNCT_FOLD)


def normalize(text: str) -> str:
    """Lowercase, fold fancy punctuation, drop currency marks and thousands separators so '₹4,820' == '4820'."""
    text = fold_punctuation(text).lower().replace("₹", " ").replace("$", " ")
    text = re.sub(r"\b(?:inr|rs)\.?\s*(?=\d)", " ", text)   # 'INR 4,820' / 'Rs. 4,820', only before a number
    text = re.sub(r"(?<=\d),(?=\d)", "", text)
    return re.sub(r"\s+", " ", text).strip()


def matches_fact(answer: str, fact: str) -> bool:
    """
    True if the answer contains the fact. `fact` may list alternatives with '|' ("3|three").
    Numbers must match whole: '3' does not match inside '30' or '3.5'.
    """
    haystack = normalize(answer)
    for alternative in fact.split("|"):
        needle = normalize(alternative)
        if not needle:
            continue
        lead = r"(?<![\d.])" if needle[0].isdigit() else r"(?<!\w)"
        tail = r"(?!\d|\.\d)" if needle[-1].isdigit() else r"(?!\w)"
        if re.search(lead + re.escape(needle) + tail, haystack):
            return True
    return False


def all_facts_present(answer: str, facts: list) -> bool:
    return bool(facts) and all(matches_fact(answer, f) for f in facts)


def cited_page(answer: str, pages: list) -> bool:
    """True if the answer cites any expected page as '(p. 4)', 'p.4' or 'page 4'."""
    text = answer.lower()
    return any(re.search(rf"\bp\.?\s*{int(n)}\b|\bpages?\s*{int(n)}\b", text) for n in pages)


def is_abstention(answer: str) -> bool:
    return bool(_ABSTAIN_RE.search(fold_punctuation(answer)))


def retrieval_score(retrieved_pages: list, expected_pages: list):
    """(hit, reciprocal_rank): rank is the position of the first retrieved passage on an expected page."""
    for rank, page in enumerate(retrieved_pages, start=1):
        if page in expected_pages:
            return True, 1.0 / rank
    return False, 0.0


def _rate(values: list):
    values = [v for v in values if v is not None]
    return mean(values) if values else None


def _percentile(values: list, pct: float):
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, round(pct * (len(ordered) - 1)))
    return ordered[index]


def aggregate(results: list) -> dict:
    """Summary numbers (0-1 rates, seconds, tokens) over per-question result dicts."""
    answerable = [r for r in results if r["type"] == "answerable"]
    unanswerable = [r for r in results if r["type"] == "unanswerable"]
    latencies = [r["latency_s"] for r in results if r.get("latency_s") is not None]
    tokens = [r["total_tokens"] for r in results if r.get("total_tokens")]
    return {
        "questions": len(results),
        "answerable": len(answerable),
        "unanswerable": len(unanswerable),
        "errors": sum(1 for r in results if r.get("error")),
        "retrieval_hit_rate": _rate([float(r["retrieval_hit"]) for r in answerable if r.get("retrieval_hit") is not None]),
        "retrieval_top1": _rate([float(r["reciprocal_rank"] == 1.0) for r in answerable if r.get("reciprocal_rank") is not None]),
        "mrr": _rate([r["reciprocal_rank"] for r in answerable if r.get("reciprocal_rank") is not None]),
        "answer_accuracy": _rate([float(r["correct"]) for r in answerable if r.get("correct") is not None]),
        "citation_rate": _rate([float(r["cited"]) for r in answerable if r.get("cited") is not None]),
        "abstention_rate": _rate([float(r["abstained"]) for r in unanswerable if r.get("abstained") is not None]),
        "faithfulness": _rate([float(r["faithful"]) for r in answerable if r.get("faithful") is not None]),
        "avg_latency_s": _rate(latencies),
        "p95_latency_s": _percentile(latencies, 0.95),
        "avg_tokens": _rate(tokens),
    }


def check_thresholds(summary: dict, thresholds: dict) -> list:
    """Failure messages for every metric below its minimum (metrics that weren't measured are skipped)."""
    failures = []
    for metric, minimum in thresholds.items():
        if metric.startswith("_"):
            continue
        value = summary.get(metric)
        if value is not None and value < minimum:
            failures.append(f"{metric} = {value:.2f} is below the minimum {minimum:.2f}")
    return failures
