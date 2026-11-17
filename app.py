import os
os.environ["STREAMLIT_WATCHER_TYPE"] = "none"

import re
import base64
from pathlib import Path

import bcrypt
import streamlit as st

from src.langgraphagenticai.settings import load_settings

load_settings()  # .env (local) / Streamlit secrets (cloud) -> os.environ, before anything reads them

from src.langgraphagenticai.database import db_utils
from src.langgraphagenticai.main import load_langgraph_agenticai_app


def valid_email(email: str) -> bool:
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None


AUTH_FEATURES = [
    ("auto_awesome", "One agent, many tools", "Answers directly, searches the web or reads your PDF: it decides per message."),
    ("description", "Answers with page citations", "Every PDF answer cites the page and shows the exact passage it used."),
    ("travel_explore", "Deep Research", "Parallel researcher agents write a cited report. You approve the plan first."),
    ("psychology", "Remembers you", "Long-term memory of your preferences, across every chat."),
]

AUTH_CSS = """
<style>
.stApp{
    background:
        radial-gradient(900px 520px at 12% 18%, rgba(79,142,247,.16), transparent 60%),
        radial-gradient(760px 500px at 88% 85%, rgba(42,91,215,.14), transparent 60%),
        var(--bg) !important;
    background-size: 140% 140%, 140% 140%, auto !important;
    animation: authDrift 22s ease-in-out infinite alternate;
}
@keyframes authDrift{
    from{ background-position: 0% 0%, 100% 100%, 0 0; }
    to{ background-position: 30% 22%, 70% 78%, 0 0; }
}
.block-container{ padding-top: 8vh !important; max-width: 1120px !important; }
.auth-brand{ display:flex; align-items:center; gap:12px; }
.auth-brand img{ width:44px; height:44px; object-fit:contain; border-radius:12px; box-shadow: 0 0 28px rgba(79,142,247,.35); }
.auth-brand span{ font-size:22px; font-weight:650; letter-spacing:-.02em;
    background: linear-gradient(90deg, #ffffff 20%, #9dc0ff 100%); -webkit-background-clip:text; background-clip:text; color:transparent; }
.auth-head{ font-size: 40px; line-height: 1.12; font-weight: 700; letter-spacing: -.03em; color:#fff; margin: 28px 0 14px 0; }
.auth-head span{ background: linear-gradient(90deg, #9dc0ff, var(--accent)); -webkit-background-clip:text; background-clip:text; color:transparent; }
.auth-lead{ font-size: 15px; color: var(--text-3); line-height: 1.6; max-width: 520px; }
.auth-feats{ display:grid; gap: 16px; margin-top: 28px; }
.auth-feat{ display:flex; gap: 12px; align-items:flex-start; }
.auth-feat .material-symbols-outlined{
    color: var(--accent-2); font-size: 19px; background: var(--accent-soft); border:1px solid rgba(79,142,247,.25);
    border-radius: 10px; padding: 7px;
}
.auth-feat-title{ color:#fff; font-weight:600; font-size:14px; }
.auth-feat-text{ color: var(--text-3); font-size:13px; line-height:1.5; margin-top:1px; }
.auth-trust{ display:flex; gap:8px; flex-wrap:wrap; margin-top: 28px; }
.auth-trust span{ font-size:11.5px; color: var(--text-2); border:1px solid var(--border-strong); background: rgba(18,18,20,.8);
    border-radius:999px; padding: 4px 11px; }
.auth-welcome h2{ font-size: 22px; font-weight: 650; color:#fff; margin: 0 0 4px 0; letter-spacing:-.01em; }
.auth-welcome p{ color: var(--text-3); font-size: 13.5px; margin: 0 0 1.2rem 0; }
.auth-brand-mobile{ display:none; }
div[data-testid="stForm"]{
    background: linear-gradient(180deg, rgba(18,18,20,.92), rgba(15,15,16,.92));
    border: 1px solid var(--border); border-radius: 16px; padding: 1.8rem;
    box-shadow: 0 20px 60px rgba(0,0,0,.45); backdrop-filter: blur(8px);
}
div[data-testid="stForm"] input{ background: var(--bg) !important; border-radius: 10px !important; }
div[data-testid="stForm"] button{
    background: linear-gradient(135deg, var(--accent), #2a5bd7) !important;
    border: none !important; border-radius: 10px !important; color:#fff !important; font-weight:600;
}
@media (max-width: 640px){
    div[class*="st-key-auth_showcase"]{ display:none; }
    .auth-brand-mobile{ display:flex; justify-content:center; margin: 4px 0 18px 0; }
    .auth-welcome{ text-align:center; }
    .block-container{ padding-top: 5vh !important; }
}
</style>
"""


def showcase_html(logo_html: str) -> str:
    feats = "".join(
        f'<div class="auth-feat"><span class="material-symbols-outlined">{icon}</span><div>'
        f'<div class="auth-feat-title">{title}</div><div class="auth-feat-text">{text}</div></div></div>'
        for icon, title, text in AUTH_FEATURES
    )
    return (
        f'<div class="auth-brand">{logo_html}<span>Netra AI</span></div>'
        '<div class="auth-head">An AI assistant that <span>searches, reads and remembers.</span></div>'
        '<div class="auth-lead">Built with LangGraph agents: live web search, page-cited answers from your PDFs, '
        'multi-agent deep research and long-term memory.</div>'
        f'<div class="auth-feats">{feats}</div>'
        '<div class="auth-trust"><span>Evaluated in CI</span><span>MCP server</span><span>Open source</span></div>'
    )


def render_auth_gate():
    db_utils.init_db()
    if db_utils.postgres_error():
        st.warning(
            "⚠️ The cloud database is unreachable, so the app is using temporary local storage "
            "(accounts and chats reset on restart). Check `DATABASE_URL` in the app secrets."
        )

    if "authenticated_user" not in st.session_state:
        st.session_state.authenticated_user = None

    if st.session_state.authenticated_user:
        return True  # already logged in

    from src.langgraphagenticai.ui.streamlitui.theme import CSS, FONTS

    st.set_page_config(page_title="Netra | Sign in", page_icon="👁", layout="wide")
    st.markdown(FONTS + CSS, unsafe_allow_html=True)
    st.markdown(AUTH_CSS, unsafe_allow_html=True)

    logo_path = Path(__file__).resolve().parent / "assets" / "logo.png"
    logo_html = ""
    if logo_path.exists():
        encoded = base64.b64encode(logo_path.read_bytes()).decode()
        logo_html = f'<img src="data:image/png;base64,{encoded}" />'

    showcase_col, center_col = st.columns([1.2, 1], gap="large", vertical_alignment="center")

    with showcase_col:
        with st.container(key="auth_showcase"):
            st.markdown(showcase_html(logo_html), unsafe_allow_html=True)

    with center_col:
        st.markdown(
            f'<div class="auth-brand auth-brand-mobile">{logo_html}<span>Netra AI</span></div>'
            '<div class="auth-welcome"><h2>Welcome to Netra</h2>'
            '<p>Sign in, or create a free account in seconds.</p></div>',
            unsafe_allow_html=True,
        )

        tab_login, tab_signup = st.tabs(["Login", "Sign Up"])

        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login", width="stretch")

                if submitted:
                    user = db_utils.get_user_by_username(username.strip())
                    if not user:
                        st.error("No account found with that username.")
                    elif not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
                        st.error("Incorrect password.")
                    else:
                        st.session_state.authenticated_user = {
                            "id": user["id"],
                            "username": user["username"],
                            "name": user["name"],
                        }
                        st.rerun()

        with tab_signup:
            with st.form("signup_form"):
                new_name = st.text_input("Full Name")
                new_username = st.text_input("Choose a Username")
                new_email = st.text_input("Email")
                new_password = st.text_input("Password", type="password")
                st.caption("At least 6 characters. A longer passphrase is stronger.")
                confirm_password = st.text_input("Confirm Password", type="password")
                signup_submitted = st.form_submit_button("Create Account", width="stretch")

                if signup_submitted:
                    if not new_name or not new_username or not new_email or not new_password:
                        st.error("Please fill in all fields.")
                    elif not valid_email(new_email):
                        st.error("Please enter a valid email address.")
                    elif len(new_password) < 6:
                        st.error("Password must be at least 6 characters.")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match.")
                    elif db_utils.username_exists(new_username.strip()):
                        st.error("Username already taken.")
                    elif db_utils.email_exists(new_email.strip()):
                        st.error("An account with this email already exists.")
                    else:
                        password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
                        db_utils.create_user(new_username.strip(), new_name.strip(), new_email.strip(), password_hash)
                        st.success("Account created! Please log in from the Login tab.")

    return False


if __name__ == "__main__":
    if render_auth_gate():
        load_langgraph_agenticai_app()