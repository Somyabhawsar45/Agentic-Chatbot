"""Guest mode, share links, key/model fallback and voice input (offline)."""
from datetime import datetime, timedelta

import groq
import httpx
import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.fallbacks import RunnableWithFallbacks
from langchain_core.tools import tool

from src.langgraphagenticai import voice
from src.langgraphagenticai.database import db_utils
from src.langgraphagenticai.LLMS import groqllm
from src.langgraphagenticai.ui.streamlitui.components import share_title, share_url


def _rate_limit():
    return groq.RateLimitError("Rate limit reached. Please try again in 7s",
                               response=httpx.Response(429, request=httpx.Request("POST", "https://api.groq.com")),
                               body=None)


# ================================================================ guests

def test_guest_accounts_are_recognised_and_counted():
    guest = db_utils.create_guest_user("hash")
    assert guest["username"].startswith("guest_") and db_utils.is_guest_user(db_utils.get_user_by_username(guest["username"]))
    real_id = db_utils.create_user("somya", "Somya", "somya@example.com", "hash")
    assert not db_utils.is_guest_user(db_utils.get_user_by_username("somya"))
    # a normal user can't pretend to be a guest with just the prefix (the email domain must match too)
    db_utils.create_user("guest_fake", "x", "fake@example.com", "hash")
    assert not db_utils.is_guest_user(db_utils.get_user_by_username("guest_fake"))

    convo = db_utils.create_conversation(guest["id"], "Netra Agent", "t")
    for text in ("one", "two", "three"):
        db_utils.add_message(convo, "user", text)
        db_utils.add_message(convo, "assistant", "answer")
    assert db_utils.count_user_messages(guest["id"]) == 3
    assert db_utils.count_user_messages(real_id) == 0


def test_cleanup_removes_only_old_guests_and_their_chats():
    old_guest = db_utils.create_guest_user("hash")
    new_guest = db_utils.create_guest_user("hash")
    real_id = db_utils.create_user("realuser", "Real", "real@example.com", "hash")
    old_convo = db_utils.create_conversation(old_guest["id"], "Netra Agent", "old")
    db_utils.add_message(old_convo, "user", "hi")
    db_utils.add_memory(old_guest["id"], "Likes tea")
    real_convo = db_utils.create_conversation(real_id, "Netra Agent", "keep me")
    # age the old guest AND the real user: the real account must survive anyway
    three_days_ago = (datetime.now() - timedelta(days=3)).isoformat()
    db_utils._run("UPDATE users SET created_at = ? WHERE id IN (?, ?)", (three_days_ago, old_guest["id"], real_id))

    deleted = db_utils.delete_stale_guests(max_age_days=2)

    assert deleted == [old_convo]
    assert db_utils.get_user_by_username(old_guest["username"]) is None
    assert db_utils.get_messages(old_convo) == [] and db_utils.get_memories(old_guest["id"]) == []
    assert db_utils.get_user_by_username(new_guest["username"]) is not None
    assert db_utils.get_user_by_username("realuser") is not None
    assert any(c["id"] == real_convo for c in db_utils.get_conversations(real_id, "Netra Agent"))


# ================================================================ share links

def test_share_create_is_idempotent_and_owner_only():
    owner = db_utils.create_user("owner", "Owner", "o@example.com", "hash")
    other = db_utils.create_user("other", "Other", "x@example.com", "hash")
    token = db_utils.create_share(owner, 7, 1, "Deep Research", "UPI report", "# UPI\nBody")
    assert db_utils.create_share(owner, 7, 1, "Deep Research", "UPI report", "# UPI\nBody") == token
    share = db_utils.get_share(token)
    assert share["content"] == "# UPI\nBody" and share["usecase"] == "Deep Research"

    assert db_utils.delete_share(token, other) is False          # not yours: nothing happens
    assert db_utils.get_share(token) is not None
    assert db_utils.delete_share(token, owner) is True
    assert db_utils.get_share(token) is None


@pytest.mark.parametrize("bad", ["", "short", "x" * 65, "abc'; DROP TABLE users;--", None, 123, "token with space"])
def test_bad_share_tokens_are_rejected(bad):
    assert db_utils.get_share(bad) is None


def test_share_title_and_url():
    assert share_title("# Impact of UPI\n\nBody") == "Impact of UPI"
    assert share_title("**Short answer:** yes it does") == "Short answer: yes it does"
    assert share_title("") == "Netra answer"
    assert len(share_title("x" * 300)) == 80
    assert share_url("https://netra.app/?share=old#x", "abc123") == "https://netra.app/?share=abc123"
    assert share_url("http://localhost:8501", "t0k3n") == "http://localhost:8501/?share=t0k3n"


# ================================================================ key + model fallback

def test_builtin_key_gets_the_whole_pool_then_the_fallback_model(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEYS", "k2, k3 ,k1")
    monkeypatch.delenv("GROQ_FALLBACK_MODELS", raising=False)
    assert groqllm.builtin_key_pool() == ["k1", "k2", "k3"]
    assert groqllm.candidate_chain("k1", "openai/gpt-oss-20b") == [
        ("k1", "openai/gpt-oss-20b"), ("k2", "openai/gpt-oss-20b"), ("k3", "openai/gpt-oss-20b"),
        ("k1", "openai/gpt-oss-120b"), ("k2", "openai/gpt-oss-120b"), ("k3", "openai/gpt-oss-120b"),
    ]


def test_a_visitors_own_key_is_never_mixed_with_the_app_keys(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "app-key")
    monkeypatch.setenv("GROQ_API_KEYS", "app-key-2")
    assert groqllm.candidate_chain("visitor-key", "openai/gpt-oss-20b") == [
        ("visitor-key", "openai/gpt-oss-20b"), ("visitor-key", "openai/gpt-oss-120b")]


def test_fallback_models_are_configurable_and_never_repeat_the_primary(monkeypatch):
    monkeypatch.setenv("GROQ_FALLBACK_MODELS", "llama-3.1-8b-instant, openai/gpt-oss-120b, llama-3.1-8b-instant")
    assert groqllm.fallback_models("openai/gpt-oss-120b") == ["llama-3.1-8b-instant"]
    monkeypatch.delenv("GROQ_FALLBACK_MODELS")
    assert groqllm.fallback_models("openai/gpt-oss-120b") == ["openai/gpt-oss-20b"]   # defaults back each other up


def test_a_retired_model_moves_on_to_the_next_one():
    import groq
    assert groq.NotFoundError in groqllm._retryable_errors()     # 404 "model does not exist"


def test_build_llm_chains_models_and_still_supports_tools(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k1")
    monkeypatch.delenv("GROQ_API_KEYS", raising=False)
    monkeypatch.delenv("GROQ_FALLBACK_MODELS", raising=False)
    llm = groqllm.build_llm("k1", "openai/gpt-oss-20b")
    assert isinstance(llm, RunnableWithFallbacks)
    assert [m.model_name for m in [llm.runnable, *llm.fallbacks]] == ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]
    assert llm.runnable.max_retries == 1 and llm.fallbacks[-1].max_retries == 6     # fail fast, last one patient

    @tool
    def search(query: str) -> str:
        """Search."""
        return ""
    bound = llm.bind_tools([search])                       # the agent and web nodes call this
    assert isinstance(bound, RunnableWithFallbacks)


def test_a_rate_limited_model_falls_back_to_the_next_one():
    def limited(_):
        raise _rate_limit()
    chain = RunnableLambda(limited).with_fallbacks(
        [RunnableLambda(lambda _: AIMessage(content="answered by the fallback"))],
        exceptions_to_handle=groqllm._retryable_errors())
    assert chain.invoke("hi").content == "answered by the fallback"


def test_ordinary_bugs_do_not_trigger_a_fallback():
    def broken(_):
        raise ValueError("a real bug")
    chain = RunnableLambda(broken).with_fallbacks([RunnableLambda(lambda _: "hidden")],
                                                  exceptions_to_handle=groqllm._retryable_errors())
    with pytest.raises(ValueError):
        chain.invoke("hi")


# ================================================================ voice

class FakeTranscriber:
    def __init__(self, text="", error=None):
        self.text, self.error, self.calls = text, error, []
        self.audio = self
        self.transcriptions = self

    def create(self, file, model, temperature):
        self.calls.append((file[0], len(file[1]), model))
        if self.error:
            raise self.error
        return type("Result", (), {"text": self.text})()


def test_voice_note_is_transcribed():
    fake = FakeTranscriber("  What is RAG?  ")
    assert voice.transcribe(b"RIFF...", ["k1"], client_factory=lambda key: fake) == "What is RAG?"
    assert fake.calls[0][2] == voice.WHISPER_MODEL


def test_voice_tries_the_next_key_when_rate_limited():
    used = []

    def factory(key):
        used.append(key)
        return FakeTranscriber(error=_rate_limit()) if key == "k1" else FakeTranscriber("hello")
    assert voice.transcribe(b"audio", ["k1", "k2"], client_factory=factory) == "hello"
    assert used == ["k1", "k2"]


def test_voice_gives_clear_errors():
    with pytest.raises(voice.VoiceError, match="No audio"):
        voice.transcribe(b"", ["k"])
    with pytest.raises(voice.VoiceError, match="too long"):
        voice.transcribe(b"x" * (voice.MAX_AUDIO_BYTES + 1), ["k"])
    with pytest.raises(voice.VoiceError, match="Groq API key"):
        voice.transcribe(b"audio", [])
    with pytest.raises(voice.VoiceError, match="couldn't hear"):
        voice.transcribe(b"audio", ["k"], client_factory=lambda key: FakeTranscriber("   "))


def test_typed_text_and_voice_combine():
    assert voice.combine("", "spoken") == "spoken"
    assert voice.combine("Summarise this:", "the attached report") == "Summarise this:\n\nthe attached report"


# ================================================================ app-wide daily cap on the built-in key

def test_global_cap_stops_everyone_on_the_built_in_key_but_not_own_keys(monkeypatch):
    from src.langgraphagenticai import main

    uid = db_utils.create_user("cap_user", "Cap", "cap@x.test", "hash")
    convo = db_utils.create_conversation(uid, "Netra Agent", "t")
    for _ in range(3):
        db_utils.add_message(convo, "user", "hi")
    db_utils.add_message(convo, "assistant", "hello")              # answers don't count
    assert db_utils.count_all_user_messages_today() >= 3

    class State(dict):
        __getattr__ = dict.__getitem__
    monkeypatch.setattr(main.st, "session_state", State(
        authenticated_user={"id": uid, "username": "cap_user", "guest": False}))
    monkeypatch.setenv("DAILY_MESSAGE_LIMIT", "100")
    monkeypatch.setenv("GLOBAL_DAILY_LIMIT", str(db_utils.count_all_user_messages_today()))
    assert main.limit_reached({"GROQ_API_KEY_IS_BUILTIN": True}) == "global"
    assert main.limit_reached({"GROQ_API_KEY_IS_BUILTIN": False}) is None      # own key: no cap
    monkeypatch.setenv("GLOBAL_DAILY_LIMIT", "0")                               # 0 = no app-wide cap
    assert main.limit_reached({"GROQ_API_KEY_IS_BUILTIN": True}) is None
    monkeypatch.setenv("DAILY_MESSAGE_LIMIT", "3")
    assert main.limit_reached({"GROQ_API_KEY_IS_BUILTIN": True}) == "user"
    assert "a lot of people" in main.limit_message({"guest": False}, "global")
    assert "gear next to your name" in main.limit_message({"guest": True}, "user")
