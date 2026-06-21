import re
import os
import tempfile
from datetime import datetime

import streamlit as st
from src.langgraphagenticai.ui.uiconfigfile import Config
from src.langgraphagenticai.database import db_utils

# (internal_usecase_value, material_icon_name, display_label)
NAV_ITEMS = [
    ("Basic Chatbot",     "chat",        "Basic Chatbot"),
    ("Chatbot With Web",  "public",      "Web Search"),
    ("Chat with PDF",     "description", "Chat With PDF"),
    ("AI News",           "newspaper",   "News Summary"),
]

USECASE_LABELS = {v: label for v, _, label in NAV_ITEMS}


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def truncate(text: str, n: int = 24) -> str:
    text = text or "Untitled"
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def relative_time(ts) -> str:
    """Best-effort relative time. Returns '' if ts is missing/unparseable."""
    if not ts:
        return ""
    try:
        if isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts)
        elif isinstance(ts, str):
            dt = datetime.fromisoformat(ts.replace("Z", ""))
        else:
            return ""
        secs = (datetime.now() - dt).total_seconds()
        if secs < 60:
            return "Just Now"
        mins = int(secs // 60)
        if mins < 60:
            return f"{mins} Minute{'s' if mins != 1 else ''} Ago"
        hours = int(mins // 60)
        if hours < 24:
            return f"{hours} Hour{'s' if hours != 1 else ''} Ago"
        days = int(hours // 24)
        return f"{days} Day{'s' if days != 1 else ''} Ago"
    except Exception:
        return ""


def get_timestamp(convo: dict):
    return convo.get("created_at") or convo.get("updated_at") or convo.get("timestamp")


class LoadStreamlitUI:
    def __init__(self):
        self.config = Config()
        self.user_controls = {}

    # ------------------------------------------------------------------
    def load_streamlit_ui(self):
        from pathlib import Path
        from PIL import Image

        logo_path = Path(__file__).resolve().parents[4] / "assets" / "logo.png"
        page_icon = Image.open(logo_path) if logo_path.exists() else "🤖"

        st.set_page_config(
            page_title="Netra | Agentic AI",
            page_icon=page_icon,
            layout="wide",
            initial_sidebar_state="expanded",
        )

        db_utils.init_db()

        # ---------------- SESSION DEFAULTS ----------------
        if "timeframe" not in st.session_state:
            st.session_state.timeframe = ""
        if "IsFetchButtonClicked" not in st.session_state:
            st.session_state.IsFetchButtonClicked = False
        if "current_conversation_id" not in st.session_state:
            st.session_state.current_conversation_id = None
        if "active_usecase" not in st.session_state:
            st.session_state.active_usecase = None
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        if "pdf_indexed_for" not in st.session_state:
            st.session_state.pdf_indexed_for = None
        if "selected_usecase_value" not in st.session_state:
            st.session_state.selected_usecase_value = NAV_ITEMS[0][0]

        self._inject_fonts()

        self._inject_css()

        # ---------------- SIDEBAR ----------------
        with st.sidebar:
            self._render_logo()

            
            self._render_new_chat()            
            self._render_usecase_nav()
            self._render_active_usecase_controls()
            self._render_history()
            self._render_settings()            
            self._render_version_footer()

        return self.user_controls

    # ------------------------------------------------------------------
    def _inject_fonts(self):
        st.markdown(
            """
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
            <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20,400,0,0" />
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/dist/tabler-icons.min.css" />
            """,
            unsafe_allow_html=True,
        )

    def _inject_css(self):
        st.markdown(
            """
            <style>
            :root{
                --bg:#0a0a0a;
                --sidebar-bg:#0d0d0d;
                --accent:#4f8ef7;
                --border:#1e1e1e;
                --border-soft:#181818;
                --border-faint:#2a2a2a;
                --text-dim:#666;
                --text-dimmer:#555;
                --text-faint:#444;
                --text-version:#333;
            }

            html, body, .stApp, [class*="css"] {
                font-family: 'Inter', sans-serif !important;
                background-color: var(--bg) !important;
            }

            #MainMenu, footer { visibility: hidden; }

            .material-symbols-outlined{
                font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 20;
                vertical-align: middle;
                font-size: 18px;
            }

            /* ---------- SIDEBAR BASE ---------- */
            section[data-testid="stSidebar"] {
                background-color: #0d0d0d !important;
                border-right: 0.5px solid var(--border-soft);
                width: 220px !important;
                min-width: 220px !important;
            }
            section[data-testid="stSidebar"] > div{
                background-color: #0d0d0d !important;
                padding-top: 1rem;
            }
            section[data-testid="stSidebar"] hr{
                border-color: var(--border-soft);
                margin: 10px 0;
            }
            .sidebar-label{
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.04em;
                color: var(--text-dimmer);
                text-transform: capitalize;
                margin: 14px 0 6px 4px;
            }

            /* ---------- LOGO ---------- */
            .sidebar-logo-wrap{
                padding: 4px 4px 12px 4px;
            }
            .sidebar-logo-row{
                display:flex;
                align-items:center;
                gap:8px;
            }
           .sidebar-logo-row i{
                color: var(--accent);
                font-size: 19px;
            }
            .sidebar-logo-img{
                width: 24px;
                height: 24px;
                object-fit: contain;
                border-radius: 6px;
            }
            .sidebar-logo-text{
                font-size: 18px;
                font-weight: 500;
                color: #fff;
            }
            .sidebar-logo-tagline{
                font-size: 11px;
                color: var(--text-faint);
                margin: 2px 0 0 27px;
            }
            .sidebar-logo-divider{
                border: none;
                border-top: 0.5px solid var(--border-soft);
                margin: 12px 0 14px 0;
            }

            /* ---------- NEW CHAT (ghost button) ---------- */
            div[class*="st-key-newchat_wrap"] button{
                background-color: transparent !important;
                border: 0.5px solid var(--border-faint) !important;
                color: #ccc !important;
                border-radius: 8px !important;
                font-weight: 500;
                text-transform: capitalize;
            }
            div[class*="st-key-newchat_wrap"] button:hover{
                border-color: var(--accent) !important;
                color: #fff !important;
            }

            /* ---------- USE CASE NAV ITEMS ---------- */
            div[class*="st-key-navitem_"] button{
                background-color: transparent !important;
                border: none !important;
                justify-content: flex-start !important;
                color: var(--text-dimmer) !important;
                font-weight: 500;
                border-radius: 8px !important;
                padding: 8px 10px !important;
                text-transform: capitalize;
            }
            div[class*="st-key-navitem_"] button *{
                color: var(--text-dimmer) !important;
            }
            div[class*="st-key-navitem_"] button [data-testid="stIconMaterial"],
            div[class*="st-key-navitem_"] button svg{
                color: var(--text-dim) !important;
                fill: var(--text-dim) !important;
            }
            div[class*="st-key-navitem_"] button:hover{
                background-color: #111 !important;
            }

           /* ---------- SETTINGS EXPANDER (muted, low priority) ---------- */
            section[data-testid="stSidebar"] details{
                background-color: transparent !important;
                border: 0.5px solid var(--border-soft) !important;
                border-radius: 8px !important;
                opacity: 0.75;
            }
            section[data-testid="stSidebar"] details:hover{
                opacity: 1;
            }
            section[data-testid="stSidebar"] summary{
                color: var(--text-dim) !important;
                font-size: 12px !important;
                text-transform: capitalize;
            }
            section[data-testid="stSidebar"] summary span{
                font-size: 12px !important;
            }
            section[data-testid="stSidebar"] input,
            section[data-testid="stSidebar"] textarea{
                background-color: #0a0a0a !important;
                color: #ccc !important;
                border: 0.5px solid var(--border-faint) !important;
                border-radius: 6px !important;
            }
            section[data-testid="stSidebar"] div[data-baseweb="select"] > div{
                background-color: #0a0a0a !important;
                border: 0.5px solid var(--border-faint) !important;
                border-radius: 6px !important;
                color: #ccc !important;
            }

            /* ---------- HISTORY ---------- */
            div[class*="st-key-histitem_"] button{
                background-color: transparent !important;
                border: none !important;
                color: #888 !important;
                font-size: 13px;
                justify-content: flex-start !important;
                padding: 6px 8px !important;
                text-transform: capitalize;
            }
            div[class*="st-key-histitem_"] button:hover{
                background-color: #111 !important;
                color: #ccc !important;
            }
            div[class*="st-key-histdel_"] button{
                background-color: transparent !important;
                border: none !important;
                color: var(--text-dimmer) !important;
                padding: 2px !important;
            }
            div[class*="st-key-histdel_"] button:hover{
                color: #e05a5a !important;
            }
            .hist-ts{
                font-size: 10px;
                color: var(--text-faint);
                margin: -6px 0 8px 10px;
            }

            /* ---------- VERSION FOOTER ---------- */
            .version-footer{
                font-size: 10.5px;
                color: var(--text-version);
                padding: 14px 6px 6px 6px;
                text-transform: capitalize;
            }

            /* ---------- TOPBAR ---------- */
            .topbar{
                display:flex;
                align-items:center;
                justify-content:space-between;
                background-color:#111;
                border:0.5px solid #1e1e1e;
                border-radius:10px;
                padding:10px 16px;
                margin-bottom:18px;
            }
            .topbar-left{
                display:flex;
                align-items:center;
                gap:8px;
                color:#ddd;
                font-weight:500;
                font-size:14px;
                text-transform: capitalize;
            }
            .topbar-left .material-symbols-outlined{ color: var(--accent); }
            .topbar-pill{
                font-size:11px;
                color: #666;
                background-color:#111;
                border:0.5px solid #2a2a2a;
                border-radius:20px;
                padding:4px 12px;
            }

            /* ---------- WELCOME SCREEN ---------- */
            .welcome-wrap{
                display:flex;
                flex-direction:column;
                align-items:center;
                justify-content:center;
                min-height: 68vh;
                padding: 0 1rem;
            }
            .welcome-title{
                font-size:24px;
                font-weight:400;
                color:#fff;
                text-align:center;
                margin-bottom:6px;
                text-transform: capitalize;
            }
            .welcome-sub{
                font-size:12px;
                color: var(--text-faint);
                text-align:center;
                margin-bottom:2.4rem;
                text-transform: capitalize;
            }
            .welcome-grid{
                display:grid;
                grid-template-columns: repeat(2, 1fr);
                gap:12px;
                width:100%;
                max-width:520px;
            }
            .welcome-card{
                background-color: var(--sidebar-bg);
                border: 0.5px solid #1e1e1e;
                border-radius:9px;
                padding:16px;
                display:flex;
                align-items:center;
                gap:12px;
                transition: border-color 0.2s, box-shadow 0.2s;
            }
            .welcome-card:hover{
                border-color: var(--accent);
                box-shadow: 0 0 12px rgba(79,142,247,0.12);
            }
            .welcome-card .material-symbols-outlined{
                color: var(--accent);
                font-size:20px;
            }
            .welcome-card-title{
                font-size:13px;
                font-weight:500;
                color:#ddd;
                text-transform: capitalize;
            }

            /* ---------- CHAT BUBBLES ---------- */
            .msg-row{ display:flex; margin-bottom:14px; align-items:flex-start; gap:10px; }
            .msg-row.msg-user{ justify-content:flex-end; }
            .avatar-ai{
                width:28px; height:28px;
                background-color:#0d1d3a;
                border-radius:6px;
                display:flex; align-items:center; justify-content:center;
                flex-shrink:0;
            }
            .avatar-ai .material-symbols-outlined{ color: var(--accent); font-size:16px; }
            .bubble{
                max-width:70%;
                padding:10px 14px;
                border-radius:10px;
                font-size:14px;
                line-height:1.55;
            }
            .bubble-ai{
                background-color:#111;
                border:0.5px solid #1e1e1e;
                color:#ccc;
            }
            .bubble-user{
                background-color:#0d1d3a;
                border:0.5px solid #1a3560;
                color:#a8c8f8;
            }

            /* ---------- THINKING DOTS ---------- */
            .thinking-dots{ display:flex; gap:6px; padding:6px 0 14px 38px; }
            .thinking-dots span{
                width:7px; height:7px; border-radius:50%;
                background-color: var(--accent);
                animation: tdBounce 1.2s infinite ease-in-out;
            }
            .thinking-dots span:nth-child(2){ animation-delay:0.15s; }
            .thinking-dots span:nth-child(3){ animation-delay:0.3s; }
            @keyframes tdBounce{
                0%,80%,100%{ transform:scale(0.6); opacity:0.4; }
                40%{ transform:scale(1); opacity:1; }
            }

            /* ---------- CHAT INPUT ---------- */
            [data-testid="stChatInput"]{
                background-color: var(--sidebar-bg) !important;
                border: 0.5px solid var(--border-faint) !important;
                border-radius: 10px !important;
            }
            [data-testid="stChatInput"] textarea{
                color: #ddd !important;
                background-color: transparent !important;
            }
            [data-testid="stChatInput"]:focus-within{
                border-color: var(--accent) !important;
            }
            button[data-testid="stChatInputSubmitButton"]{
                background-color: var(--accent) !important;
                border-radius: 6px !important;
            }
            button[data-testid="stChatInputSubmitButton"] svg{
                fill: #fff !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

    def _render_logo(self):
        import base64
        from pathlib import Path

        logo_path = Path(__file__).resolve().parents[4] / "assets" / "logo.png"
        logo_html = ""
        if logo_path.exists():
            encoded = base64.b64encode(logo_path.read_bytes()).decode()
            logo_html = f'<img src="data:image/png;base64,{encoded}" class="sidebar-logo-img" />'
        else:
            logo_html = '<i class="ti ti-eye"></i>'

        st.markdown(
            f"""
            <div class="sidebar-logo-wrap">
                <div class="sidebar-logo-row">
                    {logo_html}
                    <span class="sidebar-logo-text">Netra</span>
                </div>
                <div class="sidebar-logo-tagline">See Beyond.</div>
            </div>
            <hr class="sidebar-logo-divider" />
            """,
            unsafe_allow_html=True,
        )

    def _render_new_chat(self):
        with st.container(key="newchat_wrap"):
            if st.button("New Chat", icon=":material/add:", key="new_chat_btn", use_container_width=True):
                st.session_state.chat_history = []
                st.session_state.current_conversation_id = None
                st.session_state.pdf_indexed_for = None
                st.rerun()

    def _render_settings(self):
        st.markdown("<hr/>", unsafe_allow_html=True)
        with st.expander("⚙ Settings", expanded=False):
            llm_options = self.config.get_llm_options()
            self.user_controls["selected_llm"] = st.selectbox("LLM", llm_options)

            if self.user_controls["selected_llm"] == "Groq":
                self.user_controls["selected_groq_model"] = st.selectbox(
                    "Model", self.config.get_groq_model_options()
                )
                st.session_state["selected_groq_model"] = self.user_controls["selected_groq_model"]

                self.user_controls["GROQ_API_KEY"] = st.session_state["GROQ_API_KEY"] = st.text_input(
                    "Groq API Key", type="password", value=st.session_state.get("GROQ_API_KEY", "")
                )
                if not self.user_controls["GROQ_API_KEY"]:
                    st.warning("Enter your Groq API key to continue")

            if st.session_state.selected_usecase_value in ["Chatbot With Web", "AI News"]:
                default_tavily_key = st.session_state.get("TAVILY_API_KEY") or st.secrets.get("TAVILY_API_KEY", "")
                self.user_controls["TAVILY_API_KEY"] = st.session_state["TAVILY_API_KEY"] = st.text_input(
                    "Tavily API Key", type="password", value=default_tavily_key
                )
                os.environ["TAVILY_API_KEY"] = self.user_controls["TAVILY_API_KEY"] or ""
                if not self.user_controls["TAVILY_API_KEY"]:
                    st.warning("Enter your Tavily API key to continue")
    def _render_usecase_nav(self):
        st.markdown('<div class="sidebar-label">Use Cases</div>', unsafe_allow_html=True)

        for internal_value, icon, label in NAV_ITEMS:
            slug = slugify(internal_value)
            with st.container(key=f"navitem_{slug}"):
                if st.button(label, icon=f":material/{icon}:", key=f"nav_{slug}", use_container_width=True):
                    st.session_state.selected_usecase_value = internal_value
                    st.rerun()

        # active highlight (emitted after generic rules so it wins)
        active_slug = slugify(st.session_state.selected_usecase_value)
        st.markdown(
            f"""
            <style>
            div[class*="st-key-navitem_{active_slug}"] button[kind]{{
                background-color:#0d1d3a !important;
            }}
            div[class*="st-key-navitem_{active_slug}"] button[kind] *{{
                color: var(--accent) !important;
            }}
            div[class*="st-key-navitem_{active_slug}"] button[kind] svg{{
                fill: var(--accent) !important;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )

        self.user_controls["selected_usecase"] = st.session_state.selected_usecase_value

        # ---- detect usecase switch -> force new conversation ----
        if st.session_state.active_usecase is None:
            st.session_state.active_usecase = self.user_controls["selected_usecase"]
        elif st.session_state.active_usecase != self.user_controls["selected_usecase"]:
            st.session_state.active_usecase = self.user_controls["selected_usecase"]
            st.session_state.chat_history = []
            st.session_state.current_conversation_id = None
            st.session_state.pdf_indexed_for = None

    def _render_active_usecase_controls(self):
        usecase = self.user_controls["selected_usecase"]

        if usecase == "AI News":
            st.markdown('<div class="sidebar-label">News Options</div>', unsafe_allow_html=True)
            time_frame = st.selectbox("Time Frame", ["Daily", "Weekly", "Monthly"], index=0)
            if st.button("Fetch Latest AI News", icon=":material/search:", use_container_width=True):
                st.session_state.IsFetchButtonClicked = True
                st.session_state.timeframe = time_frame

        elif usecase == "Chat with PDF":
            from src.langgraphagenticai.rag import pdf_rag_utils

            st.markdown('<div class="sidebar-label">Upload PDF</div>', unsafe_allow_html=True)
            uploaded_file = st.file_uploader("Choose a PDF", type=["pdf"], label_visibility="collapsed")

            if uploaded_file is not None:
                already_indexed = st.session_state.get("pdf_indexed_for") == uploaded_file.name

                if not already_indexed:
                    with st.spinner("Reading and indexing PDF..."):
                        try:
                            if st.session_state.current_conversation_id is None:
                                title = db_utils.make_title(uploaded_file.name)
                                new_id = db_utils.create_conversation("Chat with PDF", title)
                                st.session_state.current_conversation_id = new_id

                            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                                tmp.write(uploaded_file.getbuffer())
                                tmp_path = tmp.name

                            pdf_rag_utils.build_index(tmp_path, st.session_state.current_conversation_id)
                            os.remove(tmp_path)

                            st.session_state.pdf_indexed_for = uploaded_file.name
                            st.success(f"Indexed: {uploaded_file.name}")
                        except Exception as e:
                            st.error(f"Failed to index PDF: {e}")
                else:
                    st.success(f"Indexed: {uploaded_file.name}")
            else:
                st.caption("Upload a PDF to start asking questions about it.")

    def _render_history(self):
        st.markdown("<hr/>", unsafe_allow_html=True)
        st.markdown('<div class="sidebar-label">History</div>', unsafe_allow_html=True)

        conversations = db_utils.get_conversations(self.user_controls["selected_usecase"])

        if not conversations:
            st.caption("No past conversations yet.")
            return

        for convo in conversations:
            convo_id = convo["id"]
            is_active = st.session_state.current_conversation_id == convo_id

            with st.container(key=f"histitem_{convo_id}"):
                c1, c2 = st.columns([5, 1])
                with c1:
                    if st.button(truncate(convo["title"]), key=f"convo_{convo_id}", use_container_width=True):
                        st.session_state.current_conversation_id = convo_id
                        st.session_state.chat_history = db_utils.get_messages(convo_id)
                        st.rerun()
                with c2:
                    with st.container(key=f"histdel_{convo_id}"):
                        if st.button("", icon=":material/delete:", key=f"del_{convo_id}"):
                            db_utils.delete_conversation(convo_id)
                            if is_active:
                                st.session_state.chat_history = []
                                st.session_state.current_conversation_id = None
                            st.rerun()

            rel = relative_time(get_timestamp(convo))
            if rel:
                st.markdown(f"<div class='hist-ts'>{rel}</div>", unsafe_allow_html=True)

            if is_active:
                st.markdown(
                    f"""
                    <style>
                    div[class*="st-key-histitem_{convo_id}"] button{{
                        color: var(--accent) !important;
                    }}
                    </style>
                    """,
                    unsafe_allow_html=True,
                )

    def _render_version_footer(self):
        model = st.session_state.get("selected_groq_model", "gpt-oss-20b")
        st.markdown(
            f'<div class="version-footer">Groq · {model} · V2.0</div>',
            unsafe_allow_html=True,
        )