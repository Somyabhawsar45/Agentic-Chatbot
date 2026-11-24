import os
os.environ["STREAMLIT_WATCHER_TYPE"] = "none"

import re
import secrets

import bcrypt
import streamlit as st

from src.langgraphagenticai.settings import load_settings

load_settings()  # .env (local) / Streamlit secrets (cloud) -> os.environ, before anything reads them

from src.langgraphagenticai.database import db_utils
from src.langgraphagenticai import auth_session
from src.langgraphagenticai.main import load_langgraph_agenticai_app
from src.langgraphagenticai.rag.pdf_rag_utils import warm_up_in_background

warm_up_in_background()   # once per server: load the PDF embedding model before anyone needs it


def valid_email(email: str) -> bool:
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None


AUTH_CHIPS = [("travel_explore", "Web search"), ("description", "PDF citations"), ("hub", "Deep research")]

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
/* centred on tall screens, near the top on short ones (the page is about 660px tall) */
.block-container{ padding-top: max(3vh, calc(50vh - 360px)) !important; padding-bottom: 2rem !important; max-width: 420px !important; }
[data-testid="stAppViewContainer"]::before{ display:none; }   /* the login page has its own glow */
.auth-hero{ display:flex; flex-direction:column; align-items:center; text-align:center; margin-bottom: 18px; }
.auth-hero .netra-eye{ box-shadow: 0 0 30px rgba(79,142,247,.32); margin-bottom: 12px; }
.auth-title{ font-size: 28px; font-weight: 700; letter-spacing: -.03em; color:#fff; line-height:1.1; }
.auth-title span{ background: linear-gradient(90deg, #9dc0ff, var(--accent)); -webkit-background-clip:text; background-clip:text; color:transparent; }
.auth-tag{ color: var(--text-3); font-size: 14px; margin-top: 6px; }
.auth-chips{ display:flex; justify-content:center; flex-wrap:wrap; gap:6px; margin-top: 12px; }
.auth-chips span.chip{ display:inline-flex; align-items:center; gap:5px; font-size:11px; color: var(--text-2);
    border:1px solid var(--border-strong); background: rgba(18,18,20,.8); border-radius:999px; padding: 3px 10px 3px 8px; }
.auth-chips .material-symbols-outlined{ font-size:14px; color: var(--accent-2); }
.auth-or{ display:flex; align-items:center; gap:12px; color: var(--text-4); font-size:12px; margin: 10px 0 4px 0; }
.auth-or::before, .auth-or::after{ content:""; flex:1; height:1px; background: var(--border); }
div[class*="st-key-guest_entry"] button{
    background: linear-gradient(135deg, var(--accent), #2a5bd7) !important; border: none !important;
    border-radius: 12px !important; min-height: 42px; box-shadow: 0 6px 18px rgba(79,142,247,.18);
}
div[class*="st-key-guest_entry"] button p{ color:#fff !important; font-weight:600 !important; font-size:14px !important; }
div[class*="st-key-guest_entry"] button:hover{ transform: translateY(-1px); box-shadow: 0 14px 34px rgba(79,142,247,.35); }
div[class*="st-key-google_entry"] button{
    background: #ffffff !important; border: 1px solid #dadce0 !important; border-radius: 12px !important; min-height: 42px;
}
div[class*="st-key-google_entry"] button p{ color: #1f1f1f !important; font-weight: 600 !important; }
div[class*="st-key-google_entry"] button [data-testid="stIconMaterial"]{ color: #4285f4 !important; }
div[class*="st-key-google_entry"] button:hover{ background: #f4f7fd !important; }
div[data-testid="stForm"]{
    background: linear-gradient(180deg, rgba(18,18,20,.92), rgba(15,15,16,.92));
    border: 1px solid var(--border); border-radius: 16px; padding: 1.1rem 1.2rem;
    box-shadow: 0 20px 60px rgba(0,0,0,.45); backdrop-filter: blur(8px);
}
div[data-testid="stForm"] [data-testid="stVerticalBlock"]{ gap: .55rem; }
div[data-testid="stTabs"] [data-baseweb="tab-panel"]{ padding-top: .6rem; }
div[data-testid="stForm"] input{ background: var(--bg) !important; border-radius: 10px !important; }
div[data-testid="stForm"] [data-testid="stFormSubmitButton"] button{
    background: linear-gradient(135deg, var(--accent), #2a5bd7) !important;
    border: none !important; border-radius: 10px !important; color:#fff !important; font-weight:600;
}
/* short laptop screens (768px tall): squeeze a little more so Login stays close */
@media (min-width: 641px) and (max-height: 820px){
    .auth-hero{ margin-bottom: 14px; }
    .auth-hero .netra-eye{ --eye: 48px !important; margin-bottom: 10px; }
    .auth-title{ font-size: 26px; }
    .auth-chips{ margin-top: 10px; }
}
/* phones */
@media (max-width: 640px){
    .block-container{ padding-top: 3vh !important; padding-left: 18px !important; padding-right: 18px !important; }
    .auth-hero .netra-eye{ --eye: 52px !important; }
    .auth-title{ font-size: 26px; }
    .auth-tag{ font-size: 13.5px; }
}
</style>
"""


def hero_html(eye: str) -> str:
    chips = "".join(f'<span class="chip"><span class="material-symbols-outlined">{icon}</span>{label}</span>'
                    for icon, label in AUTH_CHIPS)
    return (f'<div class="auth-hero">{eye}<div class="auth-title">Netra <span>AI</span></div>'
            '<div class="auth-tag">Searches the web, reads your PDFs and remembers you.</div>'
            f'<div class="auth-chips">{chips}</div></div>')


def start_guest_session():
    """'Try without an account': a throwaway guest user, signed in straight away.
    (Expired guests are removed by the hourly housekeeping in auth_session.)"""
    unusable_hash = bcrypt.hashpw(secrets.token_bytes(24), bcrypt.gensalt()).decode()
    guest = db_utils.create_guest_user(unusable_hash)
    st.session_state.authenticated_user = {"id": guest["id"], "username": guest["username"],
                                           "name": "Guest", "guest": True, "google": False}
    auth_session.remember(guest["id"], days=auth_session.GUEST_REMEMBER_DAYS)   # a refresh keeps the guest chat
    auth_session.note_guest_created()


def render_auth_gate():
    db_utils.init_db()
    auth_session.housekeeping_if_due()   # at most hourly: expired guests/tokens; keeps Supabase awake
    if db_utils.postgres_error():
        st.warning(
            "⚠️ The cloud database is unreachable, so the app is using temporary local storage "
            "(accounts and chats reset on restart). Check `DATABASE_URL` in the app secrets."
        )

    if "authenticated_user" not in st.session_state:
        st.session_state.authenticated_user = None

    if st.session_state.authenticated_user:
        return True  # already logged in

    if st.session_state.pop("google_logout", False):
        st.logout()   # also end the Google sign-in, or it would sign them straight back in

    # back again? a "Keep me signed in" cookie or a Google sign-in opens the app straight away
    if not st.session_state.get("signed_out"):
        if auth_session.restore_from_cookie() or auth_session.sign_in_with_google_session():
            return True

    from src.langgraphagenticai.ui.streamlitui.theme import CSS, FONTS

    from src.langgraphagenticai.ui.streamlitui.brand import eye_html, logo_image

    st.set_page_config(page_title="Netra | Sign in", page_icon=logo_image(64) or "👁", layout="centered")
    st.markdown(FONTS + CSS, unsafe_allow_html=True)

    # Everything lives in one placeholder. On sign-in it is cleared and the app opens in this same
    # run (no st.rerun), so the sign-in page never lingers greyed-out behind the app while it loads.
    page = st.empty()
    signed_in = False

    with page.container():
        auth_session.write_pending_cookie()     # clears the cookie right after a sign-out
        st.markdown(AUTH_CSS + hero_html(eye_html(56)), unsafe_allow_html=True)

        with st.container(key="guest_entry"):
            if st.button("Try it now, no sign-up needed", icon=":material/bolt:", type="primary",
                         key="guest_btn", width="stretch"):
                blocked = auth_session.guest_block_reason()
                if blocked:
                    st.warning(blocked)
                else:
                    start_guest_session()
                    signed_in = True
            st.markdown('<div class="auth-or">or sign in</div>', unsafe_allow_html=True)
            # only once Google sign-in is configured, and not inside LinkedIn's/Instagram's built-in
            # browser, where Google blocks sign-in ("disallowed_useragent")
            if auth_session.google_provider() is not None and not auth_session.in_app_browser():
                with st.container(key="google_entry"):
                    if st.button("Continue with Google", key="google_btn", width="stretch",
                                 icon=":material/account_circle:"):
                        auth_session.start_google_login()

        # a guest's "Sign up" button lands straight on the Sign Up tab
        tab_login, tab_signup = st.tabs(["Login", "Sign Up"], default=st.session_state.get("auth_tab"))

        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                keep = st.checkbox("Keep me signed in", value=True, help="Skip this page for 30 days on this browser")
                submitted = st.form_submit_button("Login", width="stretch")

                if submitted:
                    user = db_utils.get_user_by_username(username.strip())
                    if auth_session.login_locked(username):
                        st.error("Too many wrong attempts. Please wait 15 minutes and try again.")
                    elif (not user or db_utils.is_guest_user(user)     # guest accounts can't be signed into
                          or not bcrypt.checkpw(password.encode(), user["password_hash"].encode())):
                        # one message for both cases, so nobody can find out which usernames exist
                        auth_session.note_login_failed(username)
                        st.error("Wrong username or password.")
                    else:
                        auth_session.note_login_ok(username)
                        st.session_state.authenticated_user = auth_session.session_for(user)
                        if keep:
                            auth_session.remember(user["id"])
                        signed_in = True

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
                    blocked = auth_session.signup_block_reason()
                    if blocked:
                        st.error(blocked)
                    elif not new_name or not new_username or not new_email or not new_password:
                        st.error("Please fill in all fields.")
                    elif not valid_email(new_email):
                        st.error("Please enter a valid email address.")
                    elif len(new_password) < 6:
                        st.error("Password must be at least 6 characters.")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match.")
                    elif new_username.strip().lower().startswith(db_utils.GUEST_PREFIX):
                        st.error("Usernames starting with 'guest_' are reserved. Please choose another.")
                    elif db_utils.username_exists(new_username.strip()):
                        st.error("Username already taken.")
                    elif db_utils.email_exists(new_email.strip()):
                        st.error("An account with this email already exists.")
                    else:
                        password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
                        db_utils.create_user(new_username.strip(), new_name.strip(), new_email.strip(), password_hash)
                        auth_session.note_signup()
                        # straight into the app: no second log-in after creating the account
                        user = db_utils.get_user_by_username(new_username.strip())
                        st.session_state.authenticated_user = auth_session.session_for(user)
                        auth_session.remember(user["id"])
                        st.session_state.pending_toast = f"Welcome to Netra, {new_name.strip().split()[0]}!"
                        signed_in = True

    if signed_in:
        st.session_state.pop("auth_tab", None)
        st.session_state.pop("signed_out", None)
        page.empty()
        return True
    return False


if __name__ == "__main__":
    share_token = st.query_params.get("share")
    if share_token:   # public read-only page for a shared answer: no login needed
        from src.langgraphagenticai.ui.streamlitui.shared_view import render_shared_page
        render_shared_page(share_token)
    elif render_auth_gate():
        auth_session.write_pending_cookie()   # saves the "stay signed in" cookie after a sign-in
        load_langgraph_agenticai_app()