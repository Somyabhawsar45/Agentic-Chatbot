import streamlit as st

from src.langgraphagenticai.ui.streamlitui.loadui import LoadStreamlitUI
from src.langgraphagenticai.LLMS.groqllm import GroqLLM
from src.langgraphagenticai.graph.graph_builder import GraphBuilder
from src.langgraphagenticai.ui.streamlitui.display_result import DisplayResultStreamlit
from src.langgraphagenticai.database import db_utils
from src.langgraphagenticai.settings import (daily_message_limit, global_daily_limit, guest_message_limit,
                                             research_daily_limit)

WEB_USECASES = ("Chatbot With Web", "AI News", "Deep Research")   # need a Tavily key
OPTIONAL_WEB_USECASES = ("Netra Agent",)                          # web search if a key exists
PDF_USECASES = ("Netra Agent", "Chat with PDF")                   # 📎 attach in the chat box


# Capped: the key includes the conversation for Chat with PDF and each visitor's own API key, so an
# uncapped cache kept one graph per chat forever and memory grew until the app crashed.
@st.cache_resource(show_spinner=False, max_entries=64, ttl=6 * 3600)
def get_cached_graph(usecase: str, groq_model: str, groq_api_key: str, tavily_api_key: str = "", conversation_id=None):
    llm_config = GroqLLM(user_contols_input={
        "selected_llm": "Groq",
        "selected_groq_model": groq_model,
        "GROQ_API_KEY": groq_api_key,
    })
    model = llm_config.get_llm_model()
    graph_builder = GraphBuilder(model, tavily_api_key=tavily_api_key or None)
    if usecase == "Chat with PDF":
        return graph_builder.setup_graph(usecase, conversation_id=conversation_id)
    return graph_builder.setup_graph(usecase)


def limit_reached(user_input: dict):
    """
    Quotas for visitors who use the app's own keys:
      * Deep Research has its own, lower, daily limit, unless the visitor brought BOTH a Groq and a
        Tavily key (a run also spends the app's Tavily web searches, not only Groq calls)
      * on the built-in Groq key: one cap for the whole app per day (so a flood of visitors can't use
        up everything), then per day for accounts and per account for guests
    Returns "research", "global", "user" or None.
    """
    user = st.session_state.authenticated_user
    builtin_groq = bool(user_input.get("GROQ_API_KEY_IS_BUILTIN"))
    own_tavily = bool((st.session_state.get("user_TAVILY_API_KEY") or "").strip())
    if user_input.get("selected_usecase") == "Deep Research" and (builtin_groq or not own_tavily):
        runs = db_utils.count_user_usecase_messages_today(user["id"], "Deep Research")
        if runs >= research_daily_limit(bool(user.get("guest"))):
            return "research"
    if not builtin_groq:
        return None  # they brought their own Groq key
    cap = global_daily_limit()
    if cap and db_utils.count_all_user_messages_today() >= cap:
        return "global"
    if user.get("guest"):
        return "user" if db_utils.count_user_messages(user["id"]) >= guest_message_limit() else None
    return "user" if db_utils.count_user_messages_today(user["id"]) >= daily_message_limit() else None


def over_daily_limit(user_input: dict) -> bool:
    return limit_reached(user_input) is not None


OWN_KEY_HINT = ("add your own free Groq API key with the **⚙ gear next to your name** "
                "(get one at console.groq.com in a minute)")


def limit_message(user: dict, reason: str = "user") -> str:
    if reason == "research":
        n = research_daily_limit(bool(user.get("guest")))
        return (f"That's today's {n} free Deep Research run{'' if n == 1 else 's'} (each one runs a whole "
                "team of agents and many web searches). The other modes are still available. To research "
                "more today, add your own free Groq **and** Tavily keys with the **⚙ gear next to your name**.")
    if reason == "global":
        return ("The free demo has reached today's limit because a lot of people are trying Netra. "
                f"To keep going right now, {OWN_KEY_HINT}. The demo resets tomorrow.")
    if user.get("guest"):
        return (f"That's the {guest_message_limit()} free guest messages. Create a free account "
                f"(click your name, then **Create a free account**) or {OWN_KEY_HINT}.")
    return (f"You've reached today's limit of {daily_message_limit()} messages on the demo key. "
            f"To keep chatting, {OWN_KEY_HINT}, or come back tomorrow.")


def load_langgraph_agenticai_app():
    """
    Entry point for LangGraph Agentic AI Streamlit App
    """

    # ---------------- LOAD UI ----------------
    ui = LoadStreamlitUI()
    user_input = ui.load_streamlit_ui()

    if not user_input:
        st.error("Failed to load UI inputs.")
        return

    _run_chat(user_input)
    # a chat created during this run (first message) appears in the sidebar right away
    ui.render_history(final=True)


def _message_from_input(value, user_input: dict):
    """Typed text, plus the transcript of a voice note if one was recorded."""
    if value is None:
        return None
    text = getattr(value, "text", None) or ""
    audio = getattr(value, "audio", None)
    if not audio:
        return text or None
    from src.langgraphagenticai import voice
    from src.langgraphagenticai.LLMS.groqllm import builtin_key_pool
    key = user_input.get("GROQ_API_KEY")
    keys = builtin_key_pool() if user_input.get("GROQ_API_KEY_IS_BUILTIN") else [key]
    try:
        with st.spinner("Transcribing your voice note…"):
            spoken = voice.transcribe(audio.getvalue(), keys, filename=getattr(audio, "name", None) or "voice.wav")
    except voice.VoiceError as e:
        st.warning(str(e))
        return text or None
    except Exception as e:
        from src.langgraphagenticai.ui.streamlitui.components import friendly_error
        st.error(friendly_error(e))
        return text or None
    return voice.combine(text, spoken)


def _run_chat(user_input: dict):
    """Read the user's message, build the graph for the selected mode and render the conversation."""
    # ---------------- USER MESSAGE ----------------
    user_message = None

    # AI News flow
    if st.session_state.get("IsFetchButtonClicked", False):
        user_message = st.session_state.get("timeframe")
        st.session_state.IsFetchButtonClicked = False

    # Chat-based flow
    else:
        usecase_now = user_input.get("selected_usecase")
        if usecase_now in PDF_USECASES:
            # 📎 attach button and 🎙 mic inside the message box
            value = st.chat_input("Ask anything, attach a PDF or use the mic…", accept_file=True,
                                  file_type=["pdf"], accept_audio=True)
            files = list(getattr(value, "files", None) or []) if value is not None else []
            if files:
                from src.langgraphagenticai.ui.streamlitui.pdf_upload import index_uploaded_pdf
                indexed = index_uploaded_pdf(files[0], usecase_now)
                if indexed and not (getattr(value, "text", None) or "").strip() and not getattr(value, "audio", None):
                    st.rerun()  # file only: refresh so the top bar shows the 📎 chip
        else:
            placeholder = ("Enter a topic to research, or use the mic…" if usecase_now == "Deep Research"
                           else "Ask anything, or use the mic…")
            value = st.chat_input(placeholder, accept_audio=True)
        user_message = _message_from_input(value, user_input)

        # a starter card on the welcome screen was clicked
        if not user_message and st.session_state.get("pending_prompt"):
            user_message = st.session_state.pending_prompt
            st.session_state.pending_prompt = None

    # ---------------- MODEL & GRAPH SETUP ----------------
    try:
        usecase = user_input.get("selected_usecase")
        if not usecase:
            st.error("No use case selected.")
            return

        # Don't build/cache a graph without the keys it needs, but still show the saved
        # conversation: reading an old report shouldn't require an API key.
        missing = None
        if not user_input.get("GROQ_API_KEY"):
            missing = "Add a Groq API key with the **⚙ gear next to your name** to start chatting."
        elif usecase in WEB_USECASES and not user_input.get("TAVILY_API_KEY"):
            missing = "Add a Tavily API key with the **⚙ gear next to your name** to use this feature."
        if missing:
            st.info(missing)
            if st.session_state.get("chat_history"):
                DisplayResultStreamlit(usecase=usecase, graph=None, user_message=None).display_result_on_ui()
            return

        reason = limit_reached(user_input) if user_message else None
        if reason:
            st.warning(limit_message(st.session_state.authenticated_user, reason))
            user_message = None

        graph = get_cached_graph(
            usecase,
            user_input.get("selected_groq_model"),
            user_input.get("GROQ_API_KEY"),
            # Netra Agent: web search is optional — without a Tavily key it simply has no web tool
            tavily_api_key=user_input.get("TAVILY_API_KEY", "") if usecase in WEB_USECASES + OPTIONAL_WEB_USECASES else "",
            conversation_id=st.session_state.get("current_conversation_id") if usecase == "Chat with PDF" else None,
        )

    except Exception as e:
        st.error(f"Setup failed: {e}")
        return

    # ---------------- RENDER OUTPUT ----------------
    DisplayResultStreamlit(
        usecase=usecase,
        graph=graph,
        user_message=user_message
    ).display_result_on_ui()


# ---------------- STREAMLIT ENTRY ----------------
if __name__ == "__main__":
    load_langgraph_agenticai_app()
