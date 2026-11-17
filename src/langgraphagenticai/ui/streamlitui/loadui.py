import base64
import html
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st

from src.langgraphagenticai.ui.uiconfigfile import Config
from src.langgraphagenticai.database import db_utils
from src.langgraphagenticai.ui.streamlitui.modes import NAV_ORDER, mode
from src.langgraphagenticai.ui.streamlitui.theme import CSS, FONTS, html_block

# (internal_usecase_value, material_icon_name, display_label) — kept for compatibility
NAV_ITEMS = [(u, mode(u)["icon"], mode(u)["label"]) for u in NAV_ORDER]
USECASE_LABELS = {v: label for v, _, label in NAV_ITEMS}

WEB_MODES = ["Chatbot With Web", "AI News", "Netra Agent", "Deep Research"]
LOGO_PATH = Path(__file__).resolve().parents[4] / "assets" / "logo.png"


def get_default_secret(name: str) -> str:
    """App-owned key from Streamlit secrets, falling back to an env var / .env."""
    try:
        value = st.secrets.get(name, "")
    except Exception:  # no secrets.toml when running locally
        value = ""
    return value or os.environ.get(name, "")


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def truncate(text: str, n: int = 24) -> str:
    text = text or "Untitled"
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def _parse_ts(ts):
    try:
        return datetime.fromisoformat(str(ts).replace("Z", ""))
    except Exception:
        return None


def group_by_date(conversations: list) -> list:
    """[(group_name, [convo, ...]), ...] in ChatGPT-style buckets, newest first."""
    today = datetime.now().date()
    buckets = {"Today": [], "Yesterday": [], "Previous 7 days": [], "Older": []}
    for c in conversations:
        dt = _parse_ts(c.get("created_at"))
        d = dt.date() if dt else None
        if d == today:
            buckets["Today"].append(c)
        elif d == today - timedelta(days=1):
            buckets["Yesterday"].append(c)
        elif d and d >= today - timedelta(days=7):
            buckets["Previous 7 days"].append(c)
        else:
            buckets["Older"].append(c)
    return [(name, items) for name, items in buckets.items() if items]


def chat_as_markdown(usecase: str, history: list) -> str:
    lines = [f"# Netra · {mode(usecase)['label']}", f"_Exported {datetime.now():%Y-%m-%d %H:%M}_", ""]
    for role, content in history:
        lines += [f"### {'You' if role == 'user' else 'Netra'}", content, ""]
    return "\n".join(lines)


def reset_conversation_state():
    st.session_state.chat_history = []
    st.session_state.current_conversation_id = None
    st.session_state.pdf_indexed_for = None


def _open_conversation(convo_id: int):
    """History row clicked (runs before the rerun, so the right chat renders straight away)."""
    reset_conversation_state()
    st.session_state.current_conversation_id = convo_id
    st.session_state.chat_history = db_utils.get_messages(convo_id)


class LoadStreamlitUI:
    def __init__(self):
        self.config = Config()
        self.user_controls = {}

    # ------------------------------------------------------------------
    def load_streamlit_ui(self):
        from PIL import Image

        st.set_page_config(
            page_title="Netra | Agentic AI",
            page_icon=Image.open(LOGO_PATH) if LOGO_PATH.exists() else "🤖",
            layout="wide",
            initial_sidebar_state="auto",   # expanded on desktop, collapsed on phones
        )
        db_utils.init_db()

        # ---------------- SESSION DEFAULTS ----------------
        defaults = {
            "timeframe": "",
            "IsFetchButtonClicked": False,
            "current_conversation_id": None,
            "active_usecase": None,
            "chat_history": [],
            "pdf_indexed_for": None,
            "selected_usecase_value": NAV_ORDER[0],
            "pending_prompt": None,
            "run_ids": {},
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

        st.markdown(FONTS + CSS, unsafe_allow_html=True)

        if st.session_state.get("pending_toast"):
            st.toast(st.session_state.pending_toast)
            st.session_state.pending_toast = None

        # ---------------- SIDEBAR ----------------
        with st.sidebar:
            self._render_logo()
            self._render_new_chat()
            self._render_usecase_nav()
            self._history_slot = st.empty()  # filled below, refreshed by render_history(final=True)
            st.markdown("<hr/>", unsafe_allow_html=True)
            self._render_account_menu()      # user chip -> memory + sign out
            self._render_version_footer()
        self._history_signature = None
        self.render_history()

        # ---------------- TOP BAR (main area) ----------------
        self._render_topbar()

        return self.user_controls

    # ------------------------------------------------------------------
    def _render_logo(self):
        logo_html = ""
        if LOGO_PATH.exists():
            encoded = base64.b64encode(LOGO_PATH.read_bytes()).decode()
            logo_html = f'<img src="data:image/png;base64,{encoded}" class="sidebar-logo-img" />'
        st.markdown(html_block(
            f"""<div class="sidebar-logo-wrap"><div class="sidebar-logo-row">{logo_html}
            <span class="sidebar-logo-text">Netra</span></div>
            <div class="sidebar-logo-tagline">See Beyond.</div></div>"""),
            unsafe_allow_html=True,
        )

    def _render_new_chat(self):
        with st.container(key="newchat_wrap"):
            if st.button("New chat", icon=":material/add:", key="new_chat_btn", width="stretch"):
                reset_conversation_state()
                st.rerun()

    # ------------------------------------------------------------------
    def _render_usecase_nav(self):
        st.markdown('<div class="sidebar-label">Modes</div>', unsafe_allow_html=True)

        for internal_value, icon, label in NAV_ITEMS:
            slug = slugify(internal_value)
            with st.container(key=f"navitem_{slug}"):
                if st.button(label, icon=f":material/{icon}:", key=f"nav_{slug}", width="stretch"):
                    st.session_state.selected_usecase_value = internal_value
                    st.rerun()

        # active highlight: a filled blue pill. The sidebar's <style> comes BEFORE the main stylesheet in
        # the page, so it can't win on order; the extra `section[...]` makes it more specific instead.
        active = "navitem_" + slugify(st.session_state.selected_usecase_value)
        st.markdown(html_block(
            f"""<style>
            section[data-testid="stSidebar"] div[class*="st-key-{active}"] button{{
                background: linear-gradient(90deg, rgba(79,142,247,.20), rgba(79,142,247,.06)) !important;
                border-color: rgba(79,142,247,.32) !important;
            }}
            section[data-testid="stSidebar"] div[class*="st-key-{active}"] button p,
            section[data-testid="stSidebar"] div[class*="st-key-{active}"] button span{{ color: #ffffff !important; font-weight: 600 !important; }}
            section[data-testid="stSidebar"] div[class*="st-key-{active}"] button [data-testid="stIconMaterial"]{{ color: var(--accent-2) !important; }}
            </style>"""),
            unsafe_allow_html=True,
        )

        self.user_controls["selected_usecase"] = st.session_state.selected_usecase_value

        # ---- usecase switch -> fresh conversation ----
        if st.session_state.active_usecase is None:
            st.session_state.active_usecase = self.user_controls["selected_usecase"]
        elif st.session_state.active_usecase != self.user_controls["selected_usecase"]:
            st.session_state.active_usecase = self.user_controls["selected_usecase"]
            reset_conversation_state()

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    def render_history(self, final: bool = False):
        """
        Draw the history list into its sidebar slot. Called at the start of the run, and again
        at the end (final=True) so a chat created during this run shows up immediately. The
        second pass only redraws if the list actually changed, and uses its own widget keys.
        """
        user_id = st.session_state.authenticated_user["id"]
        conversations = db_utils.get_conversations(user_id, self.user_controls["selected_usecase"])
        signature = (tuple((c["id"], c["title"]) for c in conversations), st.session_state.current_conversation_id)
        if final and signature == self._history_signature:
            return
        self._history_signature = signature
        with self._history_slot.container():
            self._render_history(conversations, stage="b" if final else "a")

    def _render_history(self, conversations: list, stage: str):
        st.markdown('<div class="sidebar-label">History</div>', unsafe_allow_html=True)
        if not conversations:
            st.markdown('<div class="hist-empty">Your chats in this mode will appear here.</div>',
                        unsafe_allow_html=True)
            return

        if len(conversations) > 8:
            if stage == "a":
                with st.container(key="histsearch"):
                    st.text_input("Search chats", key="hist_query", placeholder="Search chats…",
                                  label_visibility="collapsed")
            query = (st.session_state.get("hist_query") or "").strip().lower()
            if query:
                conversations = [c for c in conversations if query in (c["title"] or "").lower()]
                if not conversations:
                    st.markdown('<div class="hist-empty">No matching chats.</div>', unsafe_allow_html=True)
                    return

        with st.container(key=f"histlist_{stage}"):
            for group, items in group_by_date(conversations[:40]):
                st.markdown(f"<div class='hist-group'>{group}</div>", unsafe_allow_html=True)
                for convo in items:
                    self._render_history_item(convo, stage)

    def _render_history_item(self, convo: dict, stage: str):
        """One clean row per chat (rename/delete live in Settings > This chat)."""
        convo_id = convo["id"]
        state = "on" if st.session_state.current_conversation_id == convo_id else "off"
        with st.container(key=f"histitem_{state}_{stage}_{convo_id}"):
            st.button(truncate(convo["title"], 34), key=f"convo_{stage}_{convo_id}", width="stretch",
                      help=convo["title"], on_click=_open_conversation, args=(convo_id,))

    # ------------------------------------------------------------------
    def _render_account_menu(self):
        """User chip that opens a menu: long-term memory + sign out."""
        user = st.session_state.authenticated_user
        user_id = user["id"]
        display_name = user.get("name") or user.get("username") or "You"
        initials = "".join(part[0] for part in display_name.split()[:2]).upper() or "U"
        memories = db_utils.get_memories(user_id)

        with st.container(key="account"):
            with st.popover(f"{initials}   {truncate(display_name, 20)}", width="stretch"):
                st.markdown(html_block(
                    f"""<div class="user-chip"><div class="user-avatar">{html.escape(initials)}</div>
                    <div><div class="user-name">{html.escape(display_name)}</div>
                    <div class="user-handle">@{html.escape(user.get('username', ''))}</div></div></div>"""),
                    unsafe_allow_html=True,
                )

                st.markdown(f'<div class="menu-label">🧠 What Netra remembers · {len(memories)}</div>',
                            unsafe_allow_html=True)
                if not memories:
                    st.caption("Nothing yet. Tell the Netra Agent about yourself, e.g. "
                               "*“Remember I'm a backend developer”*.")
                for m in memories:
                    c1, c2 = st.columns([9, 1], vertical_alignment="center")
                    c1.markdown(f"<div class='mem-item'>{html.escape(m['content'])}</div>", unsafe_allow_html=True)
                    with c2:
                        with st.container(key=f"memdel_{m['id']}"):
                            if st.button("✕", key=f"memx_{m['id']}", help="Forget this"):
                                db_utils.delete_memory(user_id, m["id"])
                                st.rerun()
                if memories and st.button("Forget everything", key="mem_clear", icon=":material/delete_sweep:",
                                          width="stretch"):
                    db_utils.clear_memories(user_id)
                    st.rerun()

                st.divider()
                if st.button("Sign out", icon=":material/logout:", key="signout_btn", width="stretch"):
                    st.session_state.authenticated_user = None
                    reset_conversation_state()
                    st.rerun()

    def _render_version_footer(self):
        from src.langgraphagenticai.settings import tracing_enabled

        storage = "Cloud DB" if db_utils.use_postgres() else "Local DB"
        tracing = " · LangSmith" if tracing_enabled() else ""
        st.markdown(f'<div class="version-footer">Netra v3 · {storage}{tracing}</div>', unsafe_allow_html=True)

    # ------------------------------------------------------------------
    def _render_topbar(self):
        usecase = self.user_controls["selected_usecase"]
        info = mode(usecase)
        model_options = self.config.get_groq_model_options()
        model_name = st.session_state.get("selected_groq_model") or model_options[0]

        chips = ""
        if info.get("pdf"):
            pdf_name = db_utils.get_pdf_filename(st.session_state.current_conversation_id)
            if pdf_name:
                chips += (f'<span class="chip"><span class="material-symbols-outlined">attach_file</span>'
                          f'{html.escape(truncate(pdf_name, 28))}</span>')

        with st.container(key="topbar"):
            left, right = st.columns([5, 1.6], vertical_alignment="center")
            with left:
                st.markdown(html_block(
                    f"""<div class="topbar-left">
                        <div class="topbar-icon"><span class="material-symbols-outlined">{info['icon']}</span></div>
                        <div><div class="topbar-title">{info['label']}{chips}</div>
                        <div class="topbar-sub">Groq · {html.escape(model_name)}</div></div>
                    </div>"""),
                    unsafe_allow_html=True,
                )
            with right:
                with st.popover("⚙  Settings", width="stretch"):
                    self._render_settings_body(usecase, model_options)

    def _render_settings_body(self, usecase: str, model_options: list):
        self.user_controls["selected_llm"] = "Groq"
        self.user_controls["selected_groq_model"] = st.selectbox(
            "Model", model_options, key="selected_groq_model"
        )

        self.user_controls["GROQ_API_KEY"] = self._api_key_input("Groq API Key", "GROQ_API_KEY")
        # True when the visitor relies on the app's own key -> daily limit applies
        builtin = not st.session_state.get("user_GROQ_API_KEY", "").strip()
        self.user_controls["GROQ_API_KEY_IS_BUILTIN"] = builtin
        if builtin and self.user_controls["GROQ_API_KEY"]:
            from src.langgraphagenticai.settings import daily_message_limit
            used = db_utils.count_user_messages_today(st.session_state.authenticated_user["id"])
            st.caption(f"Demo key · {used}/{daily_message_limit()} messages used today")

        if usecase in WEB_MODES:
            self.user_controls["TAVILY_API_KEY"] = self._api_key_input(
                "Tavily API Key", "TAVILY_API_KEY", required=(usecase != "Netra Agent")
            )

        if usecase == "Deep Research":
            st.toggle("Review the plan before agents start", value=True, key="research_review")

        self._render_chat_options(usecase)

    def _render_chat_options(self, usecase: str):
        """Rename / export / delete the open chat (kept out of the history list for a clean sidebar)."""
        convo_id = st.session_state.current_conversation_id
        if convo_id is None:
            return
        st.markdown('<div class="menu-label">This chat</div>', unsafe_allow_html=True)

        user_id = st.session_state.authenticated_user["id"]
        current = next((c for c in db_utils.get_conversations(user_id, usecase) if c["id"] == convo_id), None)
        if current:
            new_title = st.text_input("Name", value=current["title"], key=f"rename_{convo_id}")
            if new_title.strip() and new_title.strip() != current["title"]:
                if st.button("Save name", key=f"rensave_{convo_id}", icon=":material/edit:", width="stretch"):
                    db_utils.rename_conversation(convo_id, new_title)
                    st.rerun()

        if st.session_state.chat_history:
            st.download_button(
                "Export as Markdown",
                data=chat_as_markdown(usecase, st.session_state.chat_history),
                file_name="netra-chat.md",
                mime="text/markdown",
                icon=":material/download:",
                width="stretch",
                key="export_chat",
            )

        with st.container(key="dangerzone"):
            if st.button("Delete this chat", key=f"del_{convo_id}", icon=":material/delete:", width="stretch"):
                db_utils.delete_conversation(convo_id)
                if usecase == "Netra Agent":
                    from src.langgraphagenticai.memory.checkpointer import delete_thread
                    delete_thread(convo_id)
                reset_conversation_state()
                st.rerun()

    def _api_key_input(self, label: str, secret_name: str, required: bool = True) -> str:
        """
        Optional key field. The user's own key wins; otherwise the app's built-in
        key (Streamlit secrets / env var) is used. The built-in key is never put
        into the text box, so visitors can't reveal it with the 'show password' eye.
        """
        default_key = get_default_secret(secret_name)
        user_key = st.text_input(
            label,
            type="password",
            key=f"user_{secret_name}",
            placeholder="Using built-in key (optional)" if default_key else "Paste your key",
        ).strip()
        if not user_key and not default_key:
            if required:
                st.warning(f"Enter your {label} to continue")
            else:
                st.caption(f"Optional: add a {label} to enable web search.")
        return user_key or default_key
