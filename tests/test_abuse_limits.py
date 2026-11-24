"""Guest farming, password guessing, sign-up spam, the Deep Research cap and hourly housekeeping."""
from datetime import datetime, timedelta

import pytest

from src.langgraphagenticai import auth_session, main
from src.langgraphagenticai.database import db_utils


@pytest.fixture
def at(monkeypatch):
    """Pretend the visitor comes from a given network address."""
    def _set(address):
        monkeypatch.setattr(auth_session, "client_address", lambda: address)
    return _set


# ---------------------------------------------------------------- 1. guests

def test_a_few_guests_per_network_per_day(at, monkeypatch):
    monkeypatch.setenv("GUESTS_PER_IP_PER_DAY", "3")
    at("10.0.0.1")
    for _ in range(3):
        assert auth_session.guest_block_reason() is None
        auth_session.note_guest_created()
    assert "free account" in auth_session.guest_block_reason()
    at("10.0.0.2")                                         # another network is unaffected
    assert auth_session.guest_block_reason() is None


def test_app_wide_guest_cap_even_without_an_address(at, monkeypatch):
    at(None)                                               # no address known: only the total applies
    assert auth_session.guest_block_reason() is None
    auth_session.note_guest_created()
    monkeypatch.setenv("GUESTS_PER_DAY", str(db_utils.count_events("guest", None, 86400)))
    assert "very busy" in auth_session.guest_block_reason()


# ---------------------------------------------------------------- 2. logins + sign-ups

def test_five_wrong_passwords_lock_the_username(monkeypatch):
    monkeypatch.setenv("LOGIN_ATTEMPTS", "5")
    for _ in range(4):
        auth_session.note_login_failed("Somya")
    assert not auth_session.login_locked("somya")
    auth_session.note_login_failed(" SOMYA ")              # same username, any case/spacing
    assert auth_session.login_locked("somya")
    assert not auth_session.login_locked("someone_else")
    auth_session.note_login_ok("somya")                    # a correct login clears the count
    assert not auth_session.login_locked("somya")


def test_the_lock_expires_after_15_minutes():
    old = (datetime.now() - timedelta(minutes=16)).isoformat()
    for _ in range(6):
        db_utils._run("INSERT INTO auth_events (kind, key, created_at) VALUES (?, ?, ?)", ("login_fail", "late", old))
    assert not auth_session.login_locked("late")


def test_sign_ups_are_limited_per_network_and_per_day(at, monkeypatch):
    monkeypatch.setenv("SIGNUPS_PER_IP_PER_HOUR", "2")
    at("10.0.0.9")
    auth_session.note_signup()
    assert auth_session.signup_block_reason() is None
    auth_session.note_signup()
    assert "this network" in auth_session.signup_block_reason()
    at("10.0.0.10")
    assert auth_session.signup_block_reason() is None
    monkeypatch.setenv("SIGNUPS_PER_DAY", "2")
    assert "today's limit" in auth_session.signup_block_reason()


def test_address_comes_from_the_proxy_header(monkeypatch):
    class Ctx:
        headers = {"X-Forwarded-For": "203.0.113.7, 10.0.0.1"}
        ip_address = "10.0.0.1"
    monkeypatch.setattr(auth_session.st, "context", Ctx())
    assert auth_session.client_address() == "203.0.113.7"


# ---------------------------------------------------------------- 3. Deep Research cap

class State(dict):
    __getattr__ = dict.__getitem__


def _research_user(monkeypatch, guest, runs, own_tavily=""):
    uid = db_utils.create_user(f"r_{guest}_{runs}_{bool(own_tavily)}", "R", f"r{guest}{runs}{bool(own_tavily)}@x.test", "h")
    convo = db_utils.create_conversation(uid, "Deep Research", "t")
    for _ in range(runs):
        db_utils.add_message(convo, "user", "topic")
    monkeypatch.setattr(main.st, "session_state", State(
        authenticated_user={"id": uid, "guest": guest}, user_TAVILY_API_KEY=own_tavily))


def test_deep_research_has_its_own_daily_cap(monkeypatch):
    monkeypatch.setenv("GLOBAL_DAILY_LIMIT", "0")
    builtin = {"GROQ_API_KEY_IS_BUILTIN": True, "selected_usecase": "Deep Research"}
    _research_user(monkeypatch, guest=True, runs=1)
    assert main.limit_reached(builtin) == "research"                       # guests: 1 a day
    _research_user(monkeypatch, guest=False, runs=2)
    assert main.limit_reached(builtin) is None                             # accounts: 3 a day
    _research_user(monkeypatch, guest=False, runs=3)
    assert main.limit_reached(builtin) == "research"
    assert main.limit_reached({**builtin, "selected_usecase": "Netra Agent"}) is None   # other modes still work
    assert "Tavily" in main.limit_message({"guest": False}, "research")


def test_own_groq_key_alone_still_spends_the_apps_tavily(monkeypatch):
    own_groq = {"GROQ_API_KEY_IS_BUILTIN": False, "selected_usecase": "Deep Research"}
    _research_user(monkeypatch, guest=False, runs=3)
    assert main.limit_reached(own_groq) == "research"
    _research_user(monkeypatch, guest=False, runs=3, own_tavily="tvly-own")
    assert main.limit_reached(own_groq) is None                            # both own keys: no cap


# ---------------------------------------------------------------- 4. housekeeping

def test_housekeeping_runs_hourly_and_cleans_up(monkeypatch):
    monkeypatch.setattr(auth_session, "_last_housekeeping", [0.0])
    uid = db_utils.create_user("hk_user", "HK", "hk@x.test", "h")
    expired = db_utils.create_login_token(uid, days=-1)
    valid = db_utils.create_login_token(uid, days=30)
    old = (datetime.now() - timedelta(days=3)).isoformat()
    db_utils._run("INSERT INTO auth_events (kind, key, created_at) VALUES (?, ?, ?)", ("guest", "old-ip", old))
    db_utils.record_event("guest", "new-ip")

    assert auth_session.housekeeping_if_due(now=10_000) is True
    rows = {r["token_hash"] for r in db_utils._run("SELECT token_hash FROM login_tokens", fetch="all")}
    assert db_utils._token_hash(expired) not in rows and db_utils._token_hash(valid) in rows
    assert db_utils.count_events("guest", "old-ip", 10 * 86400) == 0
    assert db_utils.count_events("guest", "new-ip", 3600) == 1
    assert auth_session.housekeeping_if_due(now=10_000 + 1800) is False    # not again within the hour
    assert auth_session.housekeeping_if_due(now=10_000 + 3601) is True


def test_housekeeping_never_breaks_the_page(monkeypatch):
    monkeypatch.setattr(auth_session, "_last_housekeeping", [0.0])
    monkeypatch.setattr(db_utils, "housekeeping", lambda: (_ for _ in ()).throw(RuntimeError("db down")))
    assert auth_session.housekeeping_if_due(now=99_999) is True             # error swallowed


def test_in_app_browsers_are_detected(monkeypatch):
    class Ctx:
        def __init__(self, ua):
            self.headers = {"User-Agent": ua}
    linkedin = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 [LinkedInApp]"
    chrome = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
    monkeypatch.setattr(auth_session.st, "context", Ctx(linkedin))
    assert auth_session.in_app_browser()
    monkeypatch.setattr(auth_session.st, "context", Ctx(chrome))
    assert not auth_session.in_app_browser()


def test_embedding_warm_up_runs_once(monkeypatch):
    from src.langgraphagenticai.rag import pdf_rag_utils
    monkeypatch.setattr(pdf_rag_utils, "_warmup_started", False)
    monkeypatch.setattr(pdf_rag_utils, "embedding_provider", lambda: "fastembed")
    calls = []

    class Emb:
        def embed_query(self, text):
            calls.append(text)
    monkeypatch.setattr(pdf_rag_utils, "get_embeddings", lambda: Emb())
    assert pdf_rag_utils.warm_up_in_background() is True
    assert pdf_rag_utils.warm_up_in_background() is False         # only once per server
    import time
    for _ in range(50):
        if calls:
            break
        time.sleep(0.02)
    assert calls == ["warm up"]
