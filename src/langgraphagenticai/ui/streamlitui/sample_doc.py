"""
"Try with a sample PDF": one click loads a built-in document, so visitors can see page-cited
answers without having a PDF of their own. The sample is the fictional Meridian Payments annual
report that the evaluation harness also uses (evals/data), so its answers are known to be good.
"""

import re
from pathlib import Path

import streamlit as st

from src.langgraphagenticai.database import db_utils

SAMPLE_PATH = Path(__file__).resolve().parents[4] / "evals" / "data" / "meridian_report.txt"
SAMPLE_NAME = "Meridian annual report (sample)"
SAMPLE_QUESTIONS = [
    ("payments", "What was Meridian's revenue in FY2025, and how much did it grow?"),
    ("pie_chart", "Which business segment earned the most revenue?"),
    ("shield", "What risks and compliance issues does the report mention?"),
    ("person", "Who runs the company, and where is it based?"),
]
_PAGE_MARKER = re.compile(r"^=== PAGE (\d+) ===\s*$", re.MULTILINE)


def sample_pages(path: Path = SAMPLE_PATH) -> list:
    """The report as a list of page texts (index 0 = page 1)."""
    parts = _PAGE_MARKER.split(Path(path).read_text(encoding="utf-8"))
    pages = {int(parts[i]): parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}
    return [pages[n] for n in sorted(pages)]


def sample_available() -> bool:
    return SAMPLE_PATH.exists()


def is_sample_open() -> bool:
    """True when the open chat is the one with the sample report loaded."""
    cid = st.session_state.get("current_conversation_id")
    return cid is not None and db_utils.get_pdf_filename(cid) == SAMPLE_NAME


def load_sample(usecase: str) -> bool:
    """Start a new chat with the sample report indexed. True on success."""
    from src.langgraphagenticai.rag import pdf_rag_utils

    with st.spinner("Loading the sample report…"):
        try:
            user_id = st.session_state.authenticated_user["id"]
            cid = db_utils.create_conversation(user_id, usecase, "Sample: Meridian annual report")
            n_chunks = pdf_rag_utils.build_index_from_pages(sample_pages(), cid, filename=SAMPLE_NAME)
        except Exception as e:
            st.error(f"Couldn't load the sample report: {e}")
            return False
    st.session_state.chat_history = []
    st.session_state.current_conversation_id = cid
    st.session_state.pdf_indexed_for = (cid, SAMPLE_NAME)
    st.session_state.pending_toast = f"📎 Sample report loaded · {n_chunks} passages indexed. Ask anything about it."
    return True
