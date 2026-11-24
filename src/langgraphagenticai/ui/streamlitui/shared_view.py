"""
The public page behind a share link (?share=<token>): one answer, read-only, no login needed.
It shows only the frozen answer text, never the owner's name, other messages, memory or files.
"""

import streamlit as st

from src.langgraphagenticai.database import db_utils
from src.langgraphagenticai.ui.streamlitui.components import clean_markdown, report_header_html
from src.langgraphagenticai.ui.streamlitui.modes import mode
from src.langgraphagenticai.ui.streamlitui.theme import CSS, FONTS
from src.langgraphagenticai.ui.streamlitui.brand import eye_html

REPORT_MODES = ("Deep Research", "AI News")

SHARE_CSS = """
<style>
.block-container{ max-width: 860px !important; padding-top: 2.2rem !important; }
.share-top{ display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom: 18px; }
.share-brand{ display:flex; align-items:center; gap:10px; }
.share-brand img{ width:34px; height:34px; border-radius:10px; box-shadow: 0 0 22px rgba(79,142,247,.35); }
.share-brand span{ font-size:18px; font-weight:650; color:#fff; letter-spacing:-.01em; }
.share-badge{ font-size:11.5px; color: var(--accent-2); border:1px solid rgba(79,142,247,.35); background: var(--accent-soft);
    border-radius:999px; padding: 3px 11px; white-space:nowrap; }
.share-meta{ font-size:12.5px; color: var(--text-4); margin: -6px 0 14px 2px; }
.share-foot{ text-align:center; color: var(--text-3); font-size: 13px; margin: 22px 0 8px 0; line-height:1.6; }
div[class*="st-key-share_cta"] button{
    background: linear-gradient(135deg, var(--accent), #2a5bd7) !important; border:none !important;
    border-radius: 12px !important; min-height: 46px; box-shadow: 0 10px 30px rgba(79,142,247,.25);
}
div[class*="st-key-share_cta"] button p{ color:#fff !important; font-weight:600 !important; }
/* the shared answer sits in a quiet card (no avatar column here, so no left indent) */
div[class*="st-key-ai_msg_shared"], div[class*="st-key-ai_msg_report_shared"]{
    padding: 16px 20px 8px 20px !important; border: 1px solid var(--border) !important; border-radius: 16px !important;
    background: rgba(18,18,22,.6) !important; margin-top: 4px !important;
}
</style>
"""


def _open_app():
    st.query_params.clear()   # back to the normal app (sign-in / guest)


def _header(label: str):
    logo = eye_html(34)
    st.markdown(f'<div class="share-top"><div class="share-brand">{logo}<span>Netra AI</span></div>'
                f'<span class="share-badge">{label}</span></div>', unsafe_allow_html=True)


def _cta():
    _, middle, _ = st.columns([1, 1.4, 1])
    with middle:
        with st.container(key="share_cta"):
            st.button("Try Netra yourself, free", icon=":material/bolt:", key="share_try",
                      width="stretch", on_click=_open_app)


def render_shared_page(token: str) -> None:
    st.set_page_config(page_title="Netra | Shared answer", page_icon="👁", layout="centered")
    st.markdown(FONTS + CSS + SHARE_CSS, unsafe_allow_html=True)
    db_utils.init_db()
    share = db_utils.get_share(token)

    if not share:
        _header("Link not found")
        st.info("This link doesn't exist or its owner stopped sharing it.")
        _cta()
        return

    is_report = share["usecase"] in REPORT_MODES
    _header("Shared answer")
    created = str(share.get("created_at", ""))[:10]
    st.markdown(f'<div class="share-meta">{mode(share["usecase"])["label"]} · shared {created}</div>',
                unsafe_allow_html=True)
    with st.container(key="ai_msg_report_shared" if is_report else "ai_msg_shared"):
        if is_report:
            st.markdown(report_header_html(share["content"]), unsafe_allow_html=True)
        st.markdown(clean_markdown(share["content"]))   # model text: rendered as markdown, never raw HTML
    st.markdown('<div class="share-foot">Netra is an AI assistant built with LangGraph: it searches the web, '
                'answers from your PDFs with page citations and runs multi-agent research.</div>',
                unsafe_allow_html=True)
    _cta()
