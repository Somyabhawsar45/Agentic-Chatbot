import streamlit as st

from src.langgraphagenticai.ui.streamlitui.loadui import LoadStreamlitUI
from src.langgraphagenticai.LLMS.groqllm import GroqLLM
from src.langgraphagenticai.graph.graph_builder import GraphBuilder
from src.langgraphagenticai.ui.streamlitui.display_result import DisplayResultStreamlit


@st.cache_resource(show_spinner=False)
def get_cached_graph(usecase: str, groq_model: str, groq_api_key: str, tavily_api_key: str = "", conversation_id=None):
    llm_config = GroqLLM(user_contols_input={
        "selected_llm": "Groq",
        "selected_groq_model": groq_model,
        "GROQ_API_KEY": groq_api_key,
    })
    model = llm_config.get_llm_model()
    graph_builder = GraphBuilder(model)
    if usecase == "Chat with PDF":
        return graph_builder.setup_graph(usecase, conversation_id=conversation_id)
    return graph_builder.setup_graph(usecase)


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
        user_message = st.chat_input(
            "Ask anything…"
        )

    # ---------------- MODEL & GRAPH SETUP ----------------
    try:
        usecase = user_input.get("selected_usecase")
        if not usecase:
            st.error("No use case selected.")
            return

        if usecase == "Chat with PDF":
            graph = get_cached_graph(
                usecase,
                user_input.get("selected_groq_model"),
                user_input.get("GROQ_API_KEY"),
                tavily_api_key=user_input.get("TAVILY_API_KEY", ""),
                conversation_id=st.session_state.get("current_conversation_id"),
            )
        else:
            graph = get_cached_graph(
                usecase,
                user_input.get("selected_groq_model"),
                user_input.get("GROQ_API_KEY"),
                tavily_api_key=user_input.get("TAVILY_API_KEY", ""),
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