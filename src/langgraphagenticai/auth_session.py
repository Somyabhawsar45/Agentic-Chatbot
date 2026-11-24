"""
Staying signed in, and "Continue with Google".

Stay signed in: after a sign-in, a random token goes into a browser cookie (the database keeps only
its SHA-256 hash). When the page is opened again, the cookie is checked and the user goes straight
into the app. Signing out deletes the token and clears the cookie.

Google: uses Streamlit's built-in st.login (OpenID Connect). It only appears when an [auth] section
is in .streamlit/secrets.toml (see README). A Google account is matched to a Netra account by email.
"""

import json
import re
import secrets as pysecrets
import threading
import time

import bcrypt
import streamlit as st

from src.langgraphagenticai.database import db_utils

COOKIE = "netra_session"
REMEMBER_DAYS = 30
GUEST_REMEMBER_DAYS = 2          # guests are deleted after 2 days anyway
_PENDING_JS = "_netra_cookie_js"


# ---------------------------------------------------------------- session dicts

def session_for(user: dict, guest: bool = False, google: bool = False) -> dict:
    """What st.session_state.authenticated_user holds for a signed-in user."""
    return {"id": user["id"], "username": user["username"], "name": user["name"],
            "guest": guest or db_utils.is_guest_user(user), "google": google}


# ---------------------------------------------------------------- stay signed in

def _cookie_js(value: str, max_age: int) -> str:
    secure = "; Secure" if str(getattr(st.context, "url", "") or "").startswith("https") else ""
    cookie = f"{COOKIE}={value}; Max-Age={max_age}; Path=/; SameSite=Lax{secure}"
    return f'<span class="netra-cookie"></span><script>document.cookie = {json.dumps(cookie)};</script>'


def remember(user_id: int, days: float = REMEMBER_DAYS):
    """Create a login token and queue the cookie (written by write_pending_cookie on this run)."""
    token = db_utils.create_login_token(user_id, days=days)
    st.session_state[_PENDING_JS] = _cookie_js(token, int(days * 86400))
    st.session_state["_netra_token"] = token


def forget():
    """Sign-out: delete this browser's token and queue clearing the cookie."""
    for token in (st.session_state.pop("_netra_token", None), _cookie_value()):
        db_utils.delete_login_token(token)
    st.session_state[_PENDING_JS] = _cookie_js("", 0)


def _cookie_value():
    try:
        return st.context.cookies.get(COOKIE)
    except Exception:
        return None


def restore_from_cookie() -> bool:
    """Opened the app again with a valid cookie: sign straight in. True if it did."""
    user = db_utils.user_for_login_token(_cookie_value())
    if not user:
        return False
    st.session_state.authenticated_user = session_for(user)
    st.session_state["_netra_token"] = _cookie_value()
    return True


def write_pending_cookie():
    """Run a queued cookie write/clear in the browser (a hidden element; see theme.py)."""
    js = st.session_state.pop(_PENDING_JS, None)
    if js:
        st.html(js, unsafe_allow_javascript=True)


# ---------------------------------------------------------------- Google

def google_provider():
    """'google' or '' (single default provider) when [auth] is configured in secrets, else None."""
    try:
        auth = st.secrets.get("auth")
    except Exception:          # no secrets.toml at all
        return None
    if not auth:
        return None
    if "google" in auth:
        return "google"
    return "" if auth.get("client_id") else None


def google_signed_in() -> bool:
    if google_provider() is None:
        return False
    try:
        return bool(st.user.is_logged_in)
    except Exception:
        return False


def username_from_email(email: str) -> str:
    """A free username based on the email's first part ('somya.b@x.com' -> 'somyab', then 'somyab2'...)."""
    base = re.sub(r"[^a-z0-9_]", "", email.split("@")[0].lower())[:20] or "user"
    if base.startswith(db_utils.GUEST_PREFIX):
        base = "u" + base                       # 'guest_' names are reserved for guests
    name, n = base, 1
    while db_utils.username_exists(name):
        n += 1
        name = f"{base}{n}"
    return name


def account_for_google_user(email: str, name: str, email_verified=True):
    """Find the Netra account with this email, or create one. None if Google didn't verify the email."""
    if not email or email_verified is False:
        return None
    user = db_utils.get_user_by_email(email)
    if user is None:
        unusable = bcrypt.hashpw(pysecrets.token_bytes(24), bcrypt.gensalt()).decode()   # no password login
        username = username_from_email(email)
        db_utils.create_user(username, (name or username).strip(), email.strip(), unusable)
        user = db_utils.get_user_by_username(username)
    return session_for(user, google=True)


def sign_in_with_google_session() -> bool:
    """Google already confirmed who this is (st.user): open their Netra account. True if signed in."""
    if not google_signed_in():
        return False
    session = account_for_google_user(st.user.get("email"), st.user.get("name"), st.user.get("email_verified", True))
    if not session:
        return False
    st.session_state.authenticated_user = session
    return True


def start_google_login():
    provider = google_provider()
    if provider:
        st.login(provider)
    else:
        st.login()


# ---------------------------------------------------------------- abuse limits
# Free-tier quotas are shared by every visitor, so sign-in actions are rate-limited:
#   * new guests: a few per network per day (else "Try it now" again and again = endless messages)
#   * sign-ups: a few per network per hour, and a daily total for the whole app
#   * logins: after 5 wrong passwords a username is locked for 15 minutes (stops password guessing)
# Each number can be changed with the environment variable named next to it.

def _limit(name: str, default: int) -> int:
    from src.langgraphagenticai.settings import _int_env
    return _int_env(name, default)


DAY, HOUR = 86400, 3600
LOGIN_LOCK_SECONDS = 15 * 60


def client_address():
    """The visitor's network address (first X-Forwarded-For entry behind a proxy), or None."""
    try:
        forwarded = (st.context.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
        return forwarded or getattr(st.context, "ip_address", None) or None
    except Exception:
        return None


_IN_APP_BROWSERS = ("LinkedInApp", "FBAN", "FBAV", "Instagram", "Line/", "Twitter", "; wv)")


def in_app_browser() -> bool:
    """True inside an app's built-in browser (LinkedIn, Instagram, ...). Google refuses sign-in there."""
    try:
        agent = st.context.headers.get("User-Agent") or ""
    except Exception:
        return False
    return any(marker in agent for marker in _IN_APP_BROWSERS)


def guest_block_reason():
    """A message if this visitor may not start another guest session right now, else None."""
    if db_utils.count_events("guest", None, DAY) >= _limit("GUESTS_PER_DAY", 300):
        return "Guest access is very busy today. Please create a free account to keep going."
    address = client_address()
    # 10, not 3: mobile networks put many people behind one shared address (carrier NAT)
    if address and db_utils.count_events("guest", address, DAY) >= _limit("GUESTS_PER_IP_PER_DAY", 10):
        return ("You've already started a few guest sessions today. Create a free account (it takes "
                "seconds) to keep your chats and continue.")
    return None


def note_guest_created():
    db_utils.record_event("guest", client_address() or "unknown")


def signup_block_reason():
    if db_utils.count_events("signup", None, DAY) >= _limit("SIGNUPS_PER_DAY", 150):
        return "We've reached today's limit for new accounts. Please try again tomorrow, or continue as a guest."
    address = client_address()
    if address and db_utils.count_events("signup", address, HOUR) >= _limit("SIGNUPS_PER_IP_PER_HOUR", 10):
        return "Too many new accounts from this network. Please try again in an hour."
    return None


def note_signup():
    db_utils.record_event("signup", client_address() or "unknown")


def _login_key(username: str) -> str:
    return (username or "").strip().lower()


def login_locked(username: str) -> bool:
    attempts = _limit("LOGIN_ATTEMPTS", 5)
    return db_utils.count_events("login_fail", _login_key(username), LOGIN_LOCK_SECONDS) >= attempts


def note_login_failed(username: str):
    db_utils.record_event("login_fail", _login_key(username))


def note_login_ok(username: str):
    db_utils.clear_events("login_fail", _login_key(username))


# ---------------------------------------------------------------- housekeeping
_HOUSEKEEPING_EVERY = 3600
_housekeeping_lock = threading.Lock()
_last_housekeeping = [0.0]


def housekeeping_if_due(now: float = None) -> bool:
    """
    At most once an hour (per server): delete expired guests, tokens and limit rows. It runs when
    anyone opens the app, including the keep-alive visit every 10 minutes, so the database sees
    regular activity and a free Supabase project doesn't pause. Never blocks or breaks the page.
    """
    now = time.time() if now is None else now
    with _housekeeping_lock:
        if now - _last_housekeeping[0] < _HOUSEKEEPING_EVERY:
            return False
        _last_housekeeping[0] = now
    try:
        deleted = db_utils.housekeeping()
        if deleted:
            from src.langgraphagenticai.memory.checkpointer import delete_thread
            for convo_id in deleted:
                delete_thread(convo_id)
    except Exception:
        pass
    return True
