import html
import json
import re

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from src.langgraphagenticai.database import db_utils


USECASE_META = {
    "Basic Chatbot":    ("chat",        "Basic Chatbot"),
    "Chatbot With Web": ("public",      "Web Search"),
    "AI News":          ("newspaper",   "News Summary"),
    "Chat with PDF":    ("description", "Chat With PDF"),
}


def clean_snippet(text: str, max_len: int = 200) -> str:
    if not text:
        return ""
    junk_patterns = [
        r"^edit this at", r"^#\s+", r"^←|^→|^↑|^↓", r"back to homepage",
        r"^jump to", r"^contents", r"^\s*\d+\s*$", r"retrieved from",
        r"wikipedia", r"wikidata", r"this page was last",
        r"categories\s*:", r"external links", r"see also", r"references",
    ]
    lines = text.splitlines()
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        low = stripped.lower()
        if any(re.match(p, low) for p in junk_patterns):
            continue
        clean_lines.append(stripped)
    clean_text = " ".join(clean_lines)
    if len(clean_text) > max_len:
        truncated = clean_text[:max_len]
        last_period = truncated.rfind(".")
        if last_period > max_len * 0.6:
            clean_text = truncated[: last_period + 1]
        else:
            clean_text = truncated.rstrip() + "…"
    return clean_text


def get_domain(url: str) -> str:
    try:
        match = re.search(r"https?://(?:www\.)?([^/]+)", url)
        return match.group(1) if match else url
    except Exception:
        return url


def render_search_results(results: list):
    st.markdown(
        "<h3 style='color:#4f8ef7; margin-bottom:12px; font-size:15px;'>Web Sources</h3>",
        unsafe_allow_html=True,
    )
    for i, r in enumerate(results[:5], 1):
        title = r.get("title", "Untitled")
        url = r.get("url", "#")
        content = r.get("content", "")
        snippet = clean_snippet(content, max_len=200)
        domain = get_domain(url)

        st.markdown(
            f"""
            <div style="
                background:#111;
                border:0.5px solid #1e1e1e;
                border-left:3px solid #4f8ef7;
                border-radius:10px;
                padding:14px 16px;
                margin-bottom:10px;
            ">
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
                    <span style="
                        background:#0d1d3a; color:#4f8ef7; font-size:11px;
                        font-weight:700; padding:2px 8px; border-radius:20px;
                    ">#{i}</span>
                    <span style="color:#555; font-size:11px;">{domain}</span>
                </div>
                <a href="{url}" target="_blank" style="
                    color:#ddd; font-weight:600; font-size:14px;
                    text-decoration:none; line-height:1.4; display:block; margin-bottom:6px;
                ">{title}</a>
                <p style="color:#999; font-size:13px; margin:0; line-height:1.6;">{snippet}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_message(role: str, content: str):
    content = content or ""

    if role == "user":
        # User messages: keep as plain escaped text (no markdown needed for input)
        safe = html.escape(content).replace("\n", "<br>")
        st.markdown(
            f"""<div class="msg-row msg-user"><div class="bubble bubble-user">{safe}</div></div>""",
            unsafe_allow_html=True,
        )
    else:
        # Assistant messages: render real markdown (tables, bold, lists, etc.)
        # by opening the styled wrapper, letting st.markdown parse content,
        # then closing the wrapper as a separate call.
        st.markdown(
            """<div class="msg-row msg-ai"><div class="avatar-ai">
            <span class="material-symbols-outlined">smart_toy</span></div>
            <div class="bubble bubble-ai">""",
            unsafe_allow_html=True,
        )
        st.markdown(content, unsafe_allow_html=False)
        st.markdown("</div></div>", unsafe_allow_html=True)


def render_thinking(placeholder):
    placeholder.markdown(
        """<div class="thinking-dots"><span></span><span></span><span></span></div>""",
        unsafe_allow_html=True,
    )


class DisplayResultStreamlit:
    def __init__(self, usecase, graph, user_message):
        self.usecase = usecase
        self.graph = graph
        self.user_message = user_message

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

    def _ensure_conversation(self, first_message: str):
        if st.session_state.current_conversation_id is None:
            user_id = st.session_state.authenticated_user["id"]
            title = db_utils.make_title(first_message)
            new_id = db_utils.create_conversation(user_id, self.usecase, title)
            st.session_state.current_conversation_id = new_id

    def _persist(self, role: str, content: str):
        st.session_state.chat_history.append((role, content))
        db_utils.add_message(st.session_state.current_conversation_id, role, content)

    def _render_topbar(self):
        icon, label = USECASE_META.get(self.usecase, ("chat", self.usecase))
        model_name = st.session_state.get("selected_groq_model", "Llama-3.1-8B")
        st.markdown(
            f"""
            <div class="topbar">
                <div class="topbar-left">
                    <span class="material-symbols-outlined">{icon}</span>
                    <span>{label}</span>
                </div>
                <div class="topbar-pill">Groq · {model_name}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    def _render_welcome(self):
        st.markdown(
            """
            <div class="welcome-wrap">
                <div class="welcome-title">What Can I Help With?</div>
                <div class="welcome-sub">Stateful Agentic AI · Powered By LangGraph + Groq</div>
                <div class="welcome-grid">
                    <div class="welcome-card">
                        <span class="material-symbols-outlined">public</span>
                        <div class="welcome-card-title">Web Search</div>
                    </div>
                    <div class="welcome-card">
                        <span class="material-symbols-outlined">psychology</span>
                        <div class="welcome-card-title">Stateful Memory</div>
                    </div>
                    <div class="welcome-card">
                        <span class="material-symbols-outlined">description</span>
                        <div class="welcome-card-title">Chat With PDF</div>
                    </div>
                    <div class="welcome-card">
                        <span class="material-symbols-outlined">newspaper</span>
                        <div class="welcome-card-title">News Summary</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    def display_result_on_ui(self):
        self._render_topbar()

        if len(st.session_state.chat_history) == 0 and not self.user_message:
            self._render_welcome()
            return

        for role, message in st.session_state.chat_history:
            render_message(role, message)

        # ================= BASIC CHATBOT =================
        if self.usecase == "Basic Chatbot":
            if not self.user_message:
                return

            render_message("user", self.user_message)
            self._ensure_conversation(self.user_message)
            self._persist("user", self.user_message)

            thinking = st.empty()
            render_thinking(thinking)

            final_response = ""
            history = [
                SystemMessage(content="You are Netra, an intelligent agentic AI assistant. You remember everything the user shares with you and respond helpfully and concisely.")
            ] + [
                HumanMessage(content=m) if r == "user" else AIMessage(content=m)
                for r, m in st.session_state.chat_history
            ]
            for event in self.graph.stream({"messages": history}):
                for value in event.values():
                    msg = value.get("messages")
                    if isinstance(msg, AIMessage) and msg.content:
                        final_response += msg.content

            thinking.empty()
            render_message("assistant", final_response)
            self._persist("assistant", final_response)

        # ================= CHATBOT WITH WEB =================
        elif self.usecase == "Chatbot With Web":
            if not self.user_message:
                return

            render_message("user", self.user_message)
            self._ensure_conversation(self.user_message)
            self._persist("user", self.user_message)

            thinking = st.empty()
            render_thinking(thinking)

            history = [
                SystemMessage(content="You are Netra, an intelligent agentic AI assistant with web search capability. Use search results to give accurate, up-to-date answers.")
            ] + [
                HumanMessage(content=m) if r == "user" else AIMessage(content=m)
                for r, m in st.session_state.chat_history
            ]
            result = self.graph.invoke({"messages": history})
            thinking.empty()

            with st.expander("Agent Execution Trace"):
                st.write("LLM → Groq")
                st.write("Tool → Tavily Web Search")

            for msg in result["messages"]:
                if isinstance(msg, ToolMessage):
                    try:
                        raw = json.loads(msg.content)
                        if isinstance(raw, dict):
                            results = raw.get("results", [])
                        elif isinstance(raw, list):
                            results = raw
                        else:
                            results = []
                        if results:
                            render_search_results(results)
                        else:
                            st.info("No structured results found.")
                    except (json.JSONDecodeError, TypeError):
                        blocks = msg.content.split("\n\n")
                        for block in blocks[:5]:
                            block = block.strip()
                            if not block:
                                continue
                            cleaned = clean_snippet(block, max_len=250)
                            if cleaned:
                                st.markdown(
                                    f"""<div style="background:#111;border:0.5px solid #1e1e1e;
                                    border-left:3px solid #4f8ef7;border-radius:10px;padding:12px 16px;
                                    margin-bottom:10px;color:#999;font-size:13px;line-height:1.6;">{cleaned}</div>""",
                                    unsafe_allow_html=True,
                                )

            for msg in result["messages"]:
                if isinstance(msg, AIMessage) and msg.content:
                    render_message("assistant", msg.content)
                    self._persist("assistant", msg.content)

        # ================= AI NEWS =================
        elif self.usecase == "AI News":
            if not self.user_message:
                return

            self._ensure_conversation(self.user_message)
            self._persist("user", self.user_message)

            thinking = st.empty()
            render_thinking(thinking)

            self.graph.invoke({"messages": HumanMessage(content=self.user_message)})
            thinking.empty()

            with st.expander("Agent Execution Trace"):
                st.write("Tool → Tavily")
                st.write("LLM → Groq")

            try:
                path = f"./AINews/{self.user_message.lower()}_summary.md"
                with open(path, "r") as f:
                    content = f.read()
                st.markdown(content, unsafe_allow_html=True)
                self._persist("assistant", content)
            except Exception as e:
                st.error(str(e))

        # ================= CHAT WITH PDF =================
        elif self.usecase == "Chat with PDF":
            if not self.user_message:
                return

            if st.session_state.current_conversation_id is None:
                st.warning("Please upload a PDF first.")
                return

            render_message("user", self.user_message)
            self._persist("user", self.user_message)

            thinking = st.empty()
            render_thinking(thinking)

            history = [
                        HumanMessage(content=m) if r == "user" else AIMessage(content=m)
                        for r, m in st.session_state.chat_history
          ]
            result = self.graph.invoke({"messages": history})
            thinking.empty()

            final_response = ""
            for msg in result["messages"]:
                if isinstance(msg, AIMessage) and msg.content:
                    final_response = msg.content

            render_message("assistant", final_response)
            self._persist("assistant", final_response)