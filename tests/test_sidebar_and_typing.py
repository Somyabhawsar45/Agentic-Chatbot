"""Pinned chats, history groups, the account card line, the typing greeting and the typing hints."""
from datetime import datetime, timedelta

from src.langgraphagenticai.database import db_utils
from src.langgraphagenticai.ui.streamlitui import components as c
from src.langgraphagenticai.ui.streamlitui.loadui import account_status, history_groups
from src.langgraphagenticai.ui.streamlitui.modes import hints


def _user(name):
    return db_utils.create_user(name, name, f"{name}@x.test", "hash")


def test_pinned_chats_come_first_and_only_the_owner_can_pin():
    owner, other = _user("pin_owner"), _user("pin_other")
    first = db_utils.create_conversation(owner, "Netra Agent", "first")
    second = db_utils.create_conversation(owner, "Netra Agent", "second")

    assert [c["id"] for c in db_utils.get_conversations(owner, "Netra Agent")] == [second, first]
    db_utils.set_pinned(owner, first, True)
    convos = db_utils.get_conversations(owner, "Netra Agent")
    assert [c["id"] for c in convos] == [first, second] and convos[0]["pinned"] == 1

    db_utils.set_pinned(other, second, True)                  # someone else's chat: nothing changes
    assert not next(c for c in db_utils.get_conversations(owner, "Netra Agent") if c["id"] == second)["pinned"]
    assert db_utils.owns_conversation(owner, first) and not db_utils.owns_conversation(other, first)


def test_history_groups_put_pinned_first_then_dates():
    now = datetime.now()
    convos = [
        {"id": 1, "title": "a", "created_at": now.isoformat(), "pinned": 0},
        {"id": 2, "title": "b", "created_at": (now - timedelta(days=1)).isoformat(), "pinned": 1},
        {"id": 3, "title": "c", "created_at": (now - timedelta(days=1)).isoformat(), "pinned": 0},
    ]
    groups = history_groups(convos)
    assert [name for name, _ in groups] == ["Pinned", "Today", "Yesterday"]
    assert [c["id"] for c in groups[0][1]] == [2]
    assert history_groups([]) == []


def test_account_status_line():
    assert account_status({"guest": True}, used=3, limit=10) == "7 messages left"
    assert account_status({"guest": True}, used=9, limit=10) == "1 message left"
    assert account_status({"guest": True}, used=15, limit=10) == "0 messages left"
    assert account_status({"username": "somya"}, used=0, limit=10) == "@somya"


def test_typed_greeting_escapes_and_keeps_words_whole():
    out = c.typed_html("Hi <b>Al</b>, ", "what can I help with?")
    assert "<b>" not in out and "&lt;" in out                       # names are escaped
    assert 'aria-label="Hi &lt;b&gt;Al&lt;/b&gt;, what can I help with?"' in out
    assert out.count('class="tw"') == 7                              # one per word
    assert ";color:#9dc0ff" in out and ";color:#4f8ef7" in out       # blue fades across the highlight
    assert 'class="type-cur"' in out


def test_typing_hints_css():
    css = c.typing_hints_css(['Say "hi"', "Two"])
    assert css.startswith("<style>") and "@keyframes netraHints" in css
    assert '{content:"Say \\"hi\\"▏"}' in css                       # typed letter by letter, quotes escaped
    assert '{content:"Two"}' in css
    assert "textarea:placeholder-shown" in css and "prefers-reduced-motion" in css
    assert c.typing_hints_css([]) == "" and c.typing_hints_css(["  "]) == ""


def test_every_mode_has_hints():
    for usecase in ("Netra Agent", "Basic Chatbot", "Chatbot With Web", "Chat with PDF", "AI News", "Deep Research"):
        assert hints(usecase), usecase
    assert "What happened in AI this week?" in hints("AI News")


def test_sample_report_pages_and_questions():
    from src.langgraphagenticai.ui.streamlitui import sample_doc
    pages = sample_doc.sample_pages()
    assert sample_doc.sample_available() and len(pages) == 7
    assert pages[0].startswith("MERIDIAN PAYMENTS LTD") and "4,820" in pages[1]   # page 2 = financial highlights
    assert len(sample_doc.SAMPLE_QUESTIONS) == 4 and all(q.endswith("?") for _, q in sample_doc.SAMPLE_QUESTIONS)
