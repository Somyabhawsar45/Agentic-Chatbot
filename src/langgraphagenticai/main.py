import streamlit as st

from src.langgraphagenticai.ui.streamlitui.loadui import LoadStreamlitUI
from src.langgraphagenticai.LLMS.groqllm import GroqLLM
from src.langgraphagenticai.graph.graph_builder import GraphBuilder
from src.langgraphagenticai.ui.streamlitui.display_result import DisplayResultStreamlit
from src.langgraphagenticai.database import db_utils
from src.langgraphagenticai.settings import daily_message_limit

WEB_USECASES = ("Chatbot With Web", "AI News", "Deep Research")   # need a Tavily key
OPTIONAL_WEB_USECASES = ("Netra Agent",)                          # web search if a key exists
PDF_USECASES = ("Netra Agent", "Chat with PDF")                   # 📎 attach in the chat box


@st.cache_resource(show_spinner=False)
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


def over_daily_limit(user_input: dict) -> bool:
    """Visitors on the app's built-in Groq key get a daily message quota."""
    if not user_input.get("GROQ_API_KEY_IS_BUILTIN"):
        return False  # they brought their own key
    user_id = st.session_state.authenticated_user["id"]
    return db_utils.count_user_messages_today(user_id) >= daily_message_limit()


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
            # 📎 attach button inside the message box (Streamlit >= 1.43)
            value = st.chat_input("Ask anything, or attach a PDF…", accept_file=True, file_type=["pdf"])
            user_message = getattr(value, "text", None) if value is not None else None
            files = list(getattr(value, "files", None) or []) if value is not None else []
            if files:
                from src.langgraphagenticai.ui.streamlitui.pdf_upload import index_uploaded_pdf
                indexed = index_uploaded_pdf(files[0], usecase_now)
                if indexed and not (user_message or "").strip():
                    st.rerun()  # file only: refresh so the top bar shows the 📎 chip
        else:
            placeholder = "Enter a topic to research…" if usecase_now == "Deep Research" else "Ask anything…"
            user_message = st.chat_input(placeholder)

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

        # Don't build/cache a graph without the keys it needs
        if not user_input.get("GROQ_API_KEY"):
            st.info("Add a Groq API key in **⚙ Settings** (sidebar) to start chatting.")
            return
        if usecase in WEB_USECASES and not user_input.get("TAVILY_API_KEY"):
            st.info("Add a Tavily API key in **⚙ Settings** (sidebar) to use this feature.")
            return

        if user_message and over_daily_limit(user_input):
            st.warning(
                f"You've reached today's limit of {daily_message_limit()} messages on the demo key. "
                "Add your own free Groq API key in **⚙ Settings** to keep chatting, or come back tomorrow."
            )
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
