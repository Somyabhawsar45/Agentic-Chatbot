"""Stay signed in (login tokens) and Google account matching."""
from src.langgraphagenticai import auth_session
from src.langgraphagenticai.database import db_utils
from src.langgraphagenticai.ui.streamlitui.loadui import short_model_name


def _user(name, email=None):
    return db_utils.create_user(name, name.title(), email or f"{name}@x.test", "hash")


def test_login_token_signs_back_in_and_is_stored_hashed():
    uid = _user("tok_user")
    token = db_utils.create_login_token(uid, days=30)
    assert len(token) >= 40
    assert db_utils.user_for_login_token(token)["id"] == uid
    stored = db_utils._run("SELECT token_hash FROM login_tokens WHERE user_id = ?", (uid,), fetch="all")
    assert stored and all(row["token_hash"] != token for row in stored)     # only the hash is kept

    db_utils.delete_login_token(token)                                     # sign-out
    assert db_utils.user_for_login_token(token) is None


def test_expired_wrong_or_odd_tokens_do_nothing():
    uid = _user("tok_expired")
    old = db_utils.create_login_token(uid, days=-1)
    assert db_utils.user_for_login_token(old) is None
    for bad in (None, "", "nope", 123, "x" * 500):
        assert db_utils.user_for_login_token(bad) is None


def test_username_from_email_is_free_and_never_a_guest_name():
    _user("somyab")
    assert auth_session.username_from_email("Somya.B@gmail.com") == "somyab2"
    assert auth_session.username_from_email("guest_x@gmail.com") == "uguest_x"
    assert auth_session.username_from_email("@weird") == "user"


def test_google_user_gets_matched_by_email_or_a_new_account():
    uid = _user("existing_g", email="Existing@Gmail.com")
    session = auth_session.account_for_google_user("existing@gmail.com", "Ex Isting")
    assert session["id"] == uid and session["google"] is True and session["guest"] is False

    fresh = auth_session.account_for_google_user("brand.new@gmail.com", "Brand New")
    row = db_utils.get_user_by_id(fresh["id"])
    assert row["email"] == "brand.new@gmail.com" and row["name"] == "Brand New" and row["username"] == "brandnew"
    assert auth_session.account_for_google_user("brand.new@gmail.com", "Brand New")["id"] == fresh["id"]

    assert auth_session.account_for_google_user("x@gmail.com", "X", email_verified=False) is None
    assert auth_session.account_for_google_user("", "X") is None


def test_short_model_name():
    assert short_model_name("openai/gpt-oss-20b") == "gpt-oss-20b"
    assert short_model_name("llama-3.1-8b-instant") == "llama-3.1-8b-instant"
    assert short_model_name("") == "Model"
