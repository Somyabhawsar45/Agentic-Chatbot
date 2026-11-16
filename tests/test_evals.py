"""
Tests for the evaluation harness itself (offline: fake LLM + fake embeddings).
They check the scoring logic and that the golden set really matches the sample report;
the real quality numbers come from `python -m evals.run`.
"""
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.messages import AIMessage, HumanMessage

from evals import metrics, runner
from evals.report import to_markdown


# ---------------- scoring ----------------

def test_numbers_match_whole_and_ignore_currency_and_commas():
    assert metrics.matches_fact("Revenue was INR 4,820 crore.", "4,820")
    assert metrics.matches_fact("revenue: ₹4820 crore", "4,820")
    assert metrics.matches_fact("There were 3 incidents.", "3")
    assert not metrics.matches_fact("There were 30 incidents.", "3")
    assert not metrics.matches_fact("Margin was 3.5%.", "3")
    assert metrics.matches_fact("certified for PCI DSS v4.0", "4.0")


def test_alternatives_and_all_facts():
    assert metrics.matches_fact("Three major incidents", "3|three")
    assert metrics.all_facts_present("Founded in 2014, based in Pune.", ["2014", "Pune"])
    assert not metrics.all_facts_present("Founded in 2014.", ["2014", "Pune"])
    assert not metrics.all_facts_present("anything", [])


def test_fancy_punctuation_from_models_still_matches():
    # real cases from a live run: non-breaking hyphen and curly apostrophe
    assert metrics.matches_fact("The fastest was cross‑border payments (31%)", "Cross-border")
    assert metrics.matches_fact("grew by 31–% ", "31")
    assert metrics.is_abstention("I’m sorry, but the excerpts don’t contain information about merchants.")


def test_currency_stripping_does_not_corrupt_words():
    assert metrics.normalize("Our customers. 4 offices") == "our customers. 4 offices"


def test_citation_detection():
    assert metrics.cited_page("Revenue grew 18% (p. 2).", [2])
    assert metrics.cited_page("see page 2", [2])
    assert not metrics.cited_page("Revenue grew 18% (p. 12).", [2])
    assert not metrics.cited_page("no citation here", [2])


def test_abstention_detection():
    assert metrics.is_abstention("The document does not mention the stock price.")
    assert metrics.is_abstention("That information is not provided in the report.")
    assert metrics.is_abstention("I don't know.")
    assert not metrics.is_abstention("Revenue was INR 4,820 crore (p. 2).")


def test_retrieval_score_rank():
    assert metrics.retrieval_score([3, 2, 5], [2]) == (True, 0.5)
    assert metrics.retrieval_score([1, 4], [2]) == (False, 0.0)


def test_thresholds_report_only_measured_metrics_below_minimum():
    summary = {"answer_accuracy": 0.5, "retrieval_hit_rate": 0.95, "faithfulness": None}
    failures = metrics.check_thresholds(
        summary, {"_note": "x", "answer_accuracy": 0.7, "retrieval_hit_rate": 0.9, "faithfulness": 0.9})
    assert len(failures) == 1 and "answer_accuracy" in failures[0]


# ---------------- data integrity ----------------

def test_report_has_seven_pages():
    assert len(runner.load_pages()) == 7


def test_every_expected_fact_is_on_its_expected_page():
    pages = runner.load_pages()
    for case in runner.load_cases():
        if case["type"] != "answerable":
            continue
        page_text = " ".join(pages[p - 1] for p in case["expected_pages"])
        for fact in case["expected_facts"]:
            assert metrics.matches_fact(page_text, fact), f"{case['id']}: '{fact}' not on page(s) {case['expected_pages']}"


def test_golden_ids_are_unique_and_typed():
    cases = runner.load_cases()
    assert len({c["id"] for c in cases}) == len(cases)
    assert {c["type"] for c in cases} == {"answerable", "unanswerable"}


# ---------------- runner (fake LLM + fake embeddings) ----------------

def _oracle_responder(cases):
    """A fake model that answers perfectly, to prove the harness scores a perfect system as perfect."""
    by_question = {c["question"]: c for c in cases}

    def respond(messages, bound):
        question = next(m.content for m in reversed(messages) if isinstance(m, HumanMessage))
        case = by_question[question]
        if case["type"] == "answerable":
            facts = " and ".join(f.split("|")[0] for f in case["expected_facts"])
            return AIMessage(content=f"{facts} (p. {case['expected_pages'][0]}).",
                             usage_metadata={"input_tokens": 100, "output_tokens": 10, "total_tokens": 110})
        return AIMessage(content="The document does not mention this.",
                         usage_metadata={"input_tokens": 100, "output_tokens": 8, "total_tokens": 108})
    return respond


def test_runner_scores_a_perfect_fake_model(fake_llm_factory):
    cases = runner.load_cases()
    llm = fake_llm_factory(_oracle_responder(cases))
    outcome = runner.run_eval(llm, DeterministicFakeEmbedding(size=32), cases, k=4)
    summary = outcome["summary"]

    assert summary["questions"] == len(cases)
    assert summary["errors"] == 0
    assert summary["answer_accuracy"] == 1.0
    assert summary["citation_rate"] == 1.0
    assert summary["abstention_rate"] == 1.0
    assert 0.0 <= summary["retrieval_hit_rate"] <= 1.0   # fake embeddings: value is meaningless, just valid
    assert 0.0 <= summary["retrieval_top1"] <= summary["retrieval_hit_rate"]
    assert summary["avg_tokens"] > 100
    assert summary["p95_latency_s"] >= 0


def test_runner_scores_a_bad_fake_model_low(fake_llm_factory):
    cases = runner.load_cases()
    llm = fake_llm_factory(lambda messages, bound: AIMessage(content="Revenue was 999 crore."))
    summary = runner.run_eval(llm, DeterministicFakeEmbedding(size=32), cases)["summary"]
    assert summary["answer_accuracy"] == 0.0
    assert summary["abstention_rate"] == 0.0


def test_runner_records_errors_and_keeps_going(fake_llm_factory):
    def boom(messages, bound):
        raise RuntimeError("rate limited")
    cases = runner.load_cases()[:3]
    outcome = runner.run_eval(fake_llm_factory(boom), DeterministicFakeEmbedding(size=32), cases)
    assert outcome["summary"]["errors"] == 3
    assert all("rate limited" in r["error"] for r in outcome["results"])


def test_retrieval_only_run_needs_no_llm():
    cases = runner.load_cases()
    summary = runner.run_eval(None, DeterministicFakeEmbedding(size=32), cases)["summary"]
    assert summary["retrieval_hit_rate"] is not None
    assert summary["answer_accuracy"] is None


def test_faithfulness_judge(fake_llm_factory):
    cases = [c for c in runner.load_cases() if c["type"] == "answerable"][:2]
    llm = fake_llm_factory(_oracle_responder(runner.load_cases()))
    judge = fake_llm_factory(lambda messages, bound: AIMessage(content="YES"))
    summary = runner.run_eval(llm, DeterministicFakeEmbedding(size=32), cases, judge_llm=judge)["summary"]
    assert summary["faithfulness"] == 1.0


def test_markdown_report_has_summary_and_failures(fake_llm_factory):
    cases = runner.load_cases()[:4]
    llm = fake_llm_factory(lambda messages, bound: AIMessage(content="no idea"))
    outcome = runner.run_eval(llm, DeterministicFakeEmbedding(size=32), cases)
    md = to_markdown(outcome["summary"], outcome["results"], {"model": "fake"}, failures=["answer_accuracy = 0.00 is below the minimum 0.70"])
    assert "| Answer accuracy | **0%**" in md
    assert "## Thresholds" in md and "## Failures to look at" in md and "q01" in md
