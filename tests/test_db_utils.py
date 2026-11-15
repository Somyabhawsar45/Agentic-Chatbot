from src.langgraphagenticai.database import db_utils


def test_user_conversation_message_roundtrip():
    uid = db_utils.create_user("somya", "Somya", "somya@example.com", "hash")
    assert db_utils.username_exists("somya")
    assert db_utils.email_exists("somya@example.com")
    assert not db_utils.username_exists("nobody")

    cid = db_utils.create_conversation(uid, "Netra Agent", "Hello there")
    db_utils.add_message(cid, "user", "hi")
    db_utils.add_message(cid, "assistant", "hello!")

    assert db_utils.get_messages(cid) == [("user", "hi"), ("assistant", "hello!")]
    assert [c["id"] for c in db_utils.get_conversations(uid, "Netra Agent")] == [cid]
    assert db_utils.get_conversations(uid, "Basic Chatbot") == []
    assert db_utils.count_user_messages_today(uid) == 1   # only user messages count

    db_utils.delete_conversation(cid)
    assert db_utils.get_messages(cid) == []
    assert db_utils.get_conversations(uid, "Netra Agent") == []


def test_pdf_index_is_stored_and_replaced():
    db_utils.save_pdf_index(7, "a.pdf", b"first")
    db_utils.save_pdf_index(7, "b.pdf", b"second")
    assert db_utils.get_pdf_index(7) == b"second"
    assert db_utils.has_pdf_index(7)
    assert not db_utils.has_pdf_index(8)


def test_make_title():
    assert db_utils.make_title("one two three") == "one two three"
    assert db_utils.make_title("a b c d e f g h") == "a b c d e f…"
    assert db_utils.make_title("   ") == "New Conversation"
