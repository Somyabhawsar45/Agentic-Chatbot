import html
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st

from src.langgraphagenticai.ui.uiconfigfile import Config
from src.langgraphagenticai.database import db_utils
from src.langgraphagenticai.ui.streamlitui.modes import NAV_ORDER, hints, mode
from src.langgraphagenticai.ui.streamlitui.components import css_string, typing_hints_css
from src.langgraphagenticai.ui.streamlitui.theme import CSS, FONTS, html_block
from src.langgraphagenticai.ui.streamlitui.brand import eye_html, logo_image

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


# ---- the ⋯ menu on each history row (callbacks run before the rerun) ----

def _user_id() -> int:
    return st.session_state.authenticated_user["id"]


def _pin_chat(convo_id: int, pinned: bool):
    db_utils.set_pinned(_user_id(), convo_id, pinned)
    st.session_state.pending_toast = "Chat pinned" if pinned else "Chat unpinned"


def _rename_chat(convo_id: int, key: str):
    title = (st.session_state.get(key) or "").strip()[:80]
    if title and db_utils.owns_conversation(_user_id(), convo_id):
        db_utils.rename_conversation(convo_id, title)
        st.session_state.pending_toast = "Chat renamed"


def _delete_chat(convo_id: int, usecase: str):
    if not db_utils.owns_conversation(_user_id(), convo_id):
        return
    db_utils.delete_conversation(convo_id)
    if usecase == "Netra Agent":
        from src.langgraphagenticai.memory.checkpointer import delete_thread
        delete_thread(convo_id)
    if st.session_state.current_conversation_id == convo_id:
        reset_conversation_state()
    st.session_state.pending_toast = "Chat deleted"


def _clear_memory():
    db_utils.clear_memories(_user_id())
    st.session_state.pending_toast = "Memory cleared. Netra has forgotten what you told it."


def _sign_out(open_tab: str = None):
    from src.langgraphagenticai import auth_session

    user = st.session_state.authenticated_user or {}
    auth_session.forget()                        # this browser's "stay signed in" token + cookie
    if user.get("google"):
        st.session_state.google_logout = True    # the sign-in page then ends the Google session too
    st.session_state.signed_out = True
    st.session_state.authenticated_user = None
    reset_conversation_state()
    if open_tab:
        st.session_state.auth_tab = open_tab   # the sign-in page opens on this tab


def history_groups(conversations: list) -> list:
    """Pinned chats first, then the rest by date."""
    pinned = [c for c in conversations if c.get("pinned")]
    rest = [c for c in conversations if not c.get("pinned")]
    return ([("Pinned", pinned)] if pinned else []) + group_by_date(rest[:40])


def short_model_name(model: str) -> str:
    """'openai/gpt-oss-20b' -> 'gpt-oss-20b' for the small model chip."""
    return (model or "").rsplit("/", 1)[-1] or "Model"


def account_status(user: dict, used: int, limit: int) -> str:
    """The small line under the name on the account card."""
    if user.get("guest"):
        left = max(0, limit - used)
        return f"{left} message{'' if left == 1 else 's'} left"
    return "@" + (user.get("username") or "")


class LoadStreamlitUI:
    def __init__(self):
        self.config = Config()
        self.user_controls = {}

    # ------------------------------------------------------------------
    def load_streamlit_ui(self):

        st.set_page_config(
            page_title="Netra | Agentic AI",
            page_icon=logo_image(64) or "🤖",          # a small copy, not the 870 KB original
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
            self._render_account_menu()      # account card -> memory + sign out
        self._history_signature = None
        self.render_history()

        # ---------------- TOP BAR (main area) ----------------
        self._render_topbar()

        return self.user_controls

    # ------------------------------------------------------------------
    def _render_logo(self):
        logo_html = eye_html(28)      # the blinking Netra eye (small cached copy of the logo)
        st.markdown(html_block(
            f"""<div class="sidebar-logo-wrap"><div class="sidebar-logo-row">{logo_html}
            <span class="sidebar-logo-text">Netra</span></div>
            <div class="sidebar-logo-tagline">See beyond.</div></div>"""),
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
                background: linear-gradient(135deg, var(--accent), #2a5bd7) !important;
                border-color: transparent !important; box-shadow: 0 3px 10px rgba(42,91,215,.18);
            }}
            section[data-testid="stSidebar"] div[class*="st-key-{active}"] button p,
            section[data-testid="stSidebar"] div[class*="st-key-{active}"] button span{{ color: #ffffff !important; font-weight: 600 !important; }}
            section[data-testid="stSidebar"] div[class*="st-key-{active}"] button [data-testid="stIconMaterial"]{{ color: #ffffff !important; }}
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
        signature = (tuple((c["id"], c["title"], c.get("pinned")) for c in conversations),
                     st.session_state.current_conversation_id)
        if final and signature == self._history_signature:
            return
        self._history_signature = signature
        with self._history_slot.container():
            self._render_history(conversations, stage="b" if final else "a")

    def _render_history(self, conversations: list, stage: str):
        st.markdown('<div class="sidebar-label">Recent</div>', unsafe_allow_html=True)
        if not conversations:
            st.markdown('<div class="hist-empty"><span class="material-symbols-outlined">add_comment</span>'
                        'No chats yet.<br>Ask anything to start.</div>', unsafe_allow_html=True)
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
            for group, items in history_groups(conversations):
                st.markdown(f"<div class='hist-group'>{group}</div>", unsafe_allow_html=True)
                for convo in items:
                    self._render_history_item(convo, stage)

    def _render_history_item(self, convo: dict, stage: str):
        """One row per chat; its ⋯ menu (shown on hover) pins, renames or deletes it."""
        convo_id = convo["id"]
        pinned = bool(convo.get("pinned"))
        state = "on" if st.session_state.current_conversation_id == convo_id else "off"
        usecase = self.user_controls["selected_usecase"]
        with st.container(key=f"histitem_{state}_{stage}_{convo_id}", horizontal=True,
                          vertical_alignment="center", gap="small"):
            st.button(truncate(convo["title"], 30), key=f"convo_{stage}_{convo_id}", width="stretch",
                      help=convo["title"], on_click=_open_conversation, args=(convo_id,),
                      icon=":material/keep:" if pinned else None)
            with st.popover("", icon=":material/more_horiz:", help="Chat options"):
                # a compact menu: Pin, Rename (type and press Enter), Delete
                st.markdown('<span class="pop-mark pop-hist"></span>', unsafe_allow_html=True)
                st.button("Unpin" if pinned else "Pin", icon=":material/keep:", width="stretch",
                          key=f"pin_{stage}_{convo_id}", on_click=_pin_chat, args=(convo_id, not pinned))
                rename_key = f"ren_{stage}_{convo_id}"
                st.text_input("Rename", value=convo["title"], key=rename_key, max_chars=80,
                              label_visibility="collapsed", placeholder="Rename, then press Enter",
                              on_change=_rename_chat, args=(convo_id, rename_key))
                with st.container(key=f"dangerzone_h{stage}_{convo_id}"):
                    st.button("Delete", icon=":material/delete:", width="stretch", key=f"del_{stage}_{convo_id}",
                              on_click=_delete_chat, args=(convo_id, usecase))

    # ------------------------------------------------------------------
    def _render_account_menu(self):
        """Account card at the bottom: avatar, name, a status line, and a ⋯ menu (memory, sign out)."""
        from src.langgraphagenticai.settings import guest_message_limit

        user = st.session_state.authenticated_user
        user_id = user["id"]
        display_name = user.get("name") or user.get("username") or "You"
        initials = "".join(part[0] for part in display_name.split()[:2]).upper() or "U"
        used = db_utils.count_user_messages(user_id) if user.get("guest") else 0
        status = account_status(user, used, guest_message_limit())

        # the round avatar with the initials is drawn by CSS in front of the name on the button
        st.markdown(f"<style>div[class*='st-key-acctmenu'] [data-testid='stPopoverButton']::before"
                    f"{{content:{css_string(initials[:2])};}}</style>", unsafe_allow_html=True)

        with st.container(key="acctcard", horizontal=True, vertical_alignment="center", gap="small"):
            with st.container(key="acctmenu", width="content"):
                with st.popover(truncate(display_name, 20), help="Account"):
                    sub = status + (" · chats kept 2 days" if user.get("guest") else "")
                    st.markdown(html_block(
                        f"""<div class="user-chip acct-head"><div class="user-avatar">{html.escape(initials)}</div>
                        <div><div class="user-name">{html.escape(display_name)}</div>
                        <div class="user-handle">{html.escape(sub)}</div></div></div>"""),
                        unsafe_allow_html=True,
                    )
                    with st.container(key="acct_btns", horizontal=True, gap="small"):
                        if user.get("guest"):
                            st.button("Sign up", key="guest_signup", width="stretch",
                                      icon=":material/person_add:", on_click=_sign_out, args=("Sign Up",))
                        st.button("Sign out", icon=":material/logout:", key="signout_btn", width="stretch",
                                  on_click=_sign_out)
            with st.container(key="acctgear", width="content"):
                with st.popover("", icon=":material/settings:", help="Settings"):
                    self._render_settings_body(self.user_controls["selected_usecase"],
                                               self.config.get_groq_model_options())

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

        # the empty message box types out example questions for this mode
        st.markdown(typing_hints_css(hints(usecase)), unsafe_allow_html=True)

        with st.container(key="topbar", horizontal=True, vertical_alignment="center", gap="small"):
            # left: the mode, only inside a chat (the welcome screen already says it in big letters)
            in_chat = bool(st.session_state.chat_history or st.session_state.current_conversation_id)
            label = (f'<div class="topbar-mode"><span class="material-symbols-outlined">{info["icon"]}</span>'
                     f'{html.escape(info["label"])}{chips}</div>') if in_chat else "&nbsp;"
            st.markdown(label, unsafe_allow_html=True, width="stretch")
            # right: the floating model chip (Settings sit next to your name in the sidebar)
            with st.popover(short_model_name(model_name), icon=":material/memory:", help="Model"):
                st.markdown('<span class="pop-mark pop-model"></span>', unsafe_allow_html=True)
                self.user_controls["selected_llm"] = "Groq"
                self.user_controls["selected_groq_model"] = st.radio(
                    "Model", model_options, key="selected_groq_model", label_visibility="collapsed",
                    format_func=short_model_name,
                )
                st.caption("Switches to the other model if busy.")

    def _render_settings_body(self, usecase: str, model_options: list):
        st.markdown('<span class="pop-mark pop-settings"></span>', unsafe_allow_html=True)   # sizes this menu (theme.py)
        self.user_controls["GROQ_API_KEY"] = self._api_key_input("Groq API Key", "GROQ_API_KEY")
        # True when the visitor relies on the app's own key -> daily limit applies
        builtin = not st.session_state.get("user_GROQ_API_KEY", "").strip()
        self.user_controls["GROQ_API_KEY_IS_BUILTIN"] = builtin
        if builtin and self.user_controls["GROQ_API_KEY"]:
            from src.langgraphagenticai.settings import daily_message_limit, guest_message_limit
            user = st.session_state.authenticated_user
            if user.get("guest"):
                used = db_utils.count_user_messages(user["id"])
                st.caption(f"Guest · {used}/{guest_message_limit()} free messages used")
            else:
                used = db_utils.count_user_messages_today(user["id"])
                st.caption(f"Demo key · {used}/{daily_message_limit()} messages used today")

        if usecase in WEB_MODES:
            self.user_controls["TAVILY_API_KEY"] = self._api_key_input(
                "Tavily API Key", "TAVILY_API_KEY", required=(usecase != "Netra Agent")
            )


        self._render_chat_options(usecase)
        self._render_memory_settings()

    def _render_memory_settings(self):
        """What Netra remembers isn't listed anywhere, but people can wipe it from Settings."""
        user_id = st.session_state.authenticated_user["id"]
        count = len(db_utils.get_memories(user_id))
        if not count:
            return
        st.markdown('<div class="menu-label">Memory</div>', unsafe_allow_html=True)
        st.caption(f"Netra remembers {count} thing{'' if count == 1 else 's'} you told it.")
        st.button("Clear memory", icon=":material/delete_sweep:", key="mem_clear", width="stretch",
                  on_click=_clear_memory)

    def _render_chat_options(self, usecase: str):
        """Export the open chat (pin / rename / delete live in the history row's ⋯ menu)."""
        if st.session_state.current_conversation_id is None:
            return
        if st.session_state.chat_history:
            st.markdown('<div class="menu-label">This chat</div>', unsafe_allow_html=True)
            st.download_button(
                "Export as Markdown",
                data=chat_as_markdown(usecase, st.session_state.chat_history),
                file_name="netra-chat.md",
                mime="text/markdown",
                icon=":material/download:",
                width="stretch",
                key="export_chat",
            )

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
