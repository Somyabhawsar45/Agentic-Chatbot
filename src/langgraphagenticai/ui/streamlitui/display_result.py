import html
import json
import re
import time
import uuid

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk, ToolMessage, SystemMessage

from src.langgraphagenticai import jobs
from src.langgraphagenticai.database import db_utils
from src.langgraphagenticai.ui.streamlitui.modes import mode
from src.langgraphagenticai.ui.streamlitui.theme import html_block
from src.langgraphagenticai.ui.streamlitui.components import (  # noqa: F401  (re-exported)
    ResearchProgress, citation_chips_html, clean_markdown, clean_snippet, dedupe_citations, describe_step,
    friendly_error, get_domain, report_header_html, safe_url, source_pills_html, timeline_html, unique_sources,
)

REPORT_MODES = ("Deep Research", "AI News")   # answers that get a "Download report" button
BACKGROUND_MODES = REPORT_MODES               # long runs that keep going when you switch modes

AI_HEAD = html_block("""<div class="ai-head"><div class="ai-avatar">
<span class="material-symbols-outlined">auto_awesome</span></div>
<span class="ai-name">Netra</span></div>""")


# =====================================================================
# Small helpers
# =====================================================================

THINKING_HTML = html_block("""<div class="thinking"><div class="thinking-label">Thinking…</div>
<div class="sk-line w1"></div><div class="sk-line w2"></div><div class="sk-line w3"></div></div>""")


def render_thinking(placeholder):
    placeholder.markdown(THINKING_HTML, unsafe_allow_html=True)


def render_user_message(content: str):
    safe = html.escape(content or "").replace("\n", "<br>")
    st.markdown(f'<div class="msg-user"><div class="bubble-user">{safe}</div></div>', unsafe_allow_html=True)


# =====================================================================
# Sources & citations
# =====================================================================

def render_search_results(results: list):
    """Detailed source cards (title, domain, snippet). Only http(s) links are rendered."""
    for i, r in enumerate(unique_sources(results)[:8], 1):
        title = html.escape(r.get("title") or "Untitled")
        link = html.escape(r["url"], quote=True)
        snippet = html.escape(clean_snippet(r.get("content", ""), max_len=200))
        domain = html.escape(get_domain(r["url"]))
        st.markdown(html_block(
            f"""<div style="background:var(--bg-raised);border:1px solid var(--border);border-left:3px solid var(--accent);
            border-radius:12px;padding:12px 16px;margin-bottom:10px;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
            <span class="src-num">{i}</span>
            <span style="color:var(--text-4);font-size:11.5px;">{domain}</span></div>
            <a href="{link}" target="_blank" rel="noopener noreferrer" style="color:var(--text);font-weight:600;font-size:13.5px;
            text-decoration:none;line-height:1.4;display:block;margin-bottom:4px;">{title}</a>
            <div style="color:var(--text-3);font-size:12.5px;line-height:1.6;">{snippet}</div></div>"""),
            unsafe_allow_html=True,
        )


def parse_tavily_results(msg: ToolMessage) -> list:
    """Extract the list of {title, url, content} results from a Tavily ToolMessage."""
    try:
        raw = json.loads(msg.content)
    except (json.JSONDecodeError, TypeError):
        return []
    if isinstance(raw, dict):
        return raw.get("results", []) or []
    if isinstance(raw, list):
        return raw
    return []


def render_sources(results: list):
    """Numbered domain pills under the answer, plus a details box with the source cards."""
    unique = unique_sources(results)
    if not unique:
        return
    st.markdown(source_pills_html(unique), unsafe_allow_html=True)
    with st.expander(f"Source details · {len(unique)}", icon=":material/public:", expanded=False):
        render_search_results(unique)


def render_pdf_citations(citations: list):
    """'p. 7' chips under the answer; each opens the exact passage the answer used."""
    chips = citation_chips_html(citations)
    if chips:
        st.markdown(chips, unsafe_allow_html=True)


# =====================================================================
# Live execution trace
# =====================================================================

def stream_graph_answer(
    graph,
    inputs,
    answer_nodes: set,
    config: dict = None,
    show_sources: bool = False,
    show_trace: bool = False,
    card_key: str = "ai_msg_live",
) -> str:
    """
    Runs the graph and types the assistant's answer out token by token, inside
    a Netra message card.

    - "messages" stream mode gives LLM tokens as they are generated; only tokens
      from `answer_nodes` are shown.
    - "updates" stream mode gives each node's output as it finishes. It drives
      the live execution trace, collects web sources / PDF citations (shown once,
      under the answer) and notices when the graph pauses for human review.
    Returns the final answer text ("" if the run paused or failed).
    (Deep Research and AI News don't use this: they run as background jobs, see jobs.py.)
    """
    trace = st.status("Thinking…", expanded=False) if show_trace else None
    trace_box = trace.empty() if trace is not None else None
    trace_lines = []
    web_results = []
    pdf_citations = []

    slot = st.empty()
    with slot.container(key=card_key):
        st.markdown(AI_HEAD, unsafe_allow_html=True)
        placeholder = st.empty()
        render_thinking(placeholder)

    answer = ""
    fallback_answer = ""  # complete AIMessage from node output, if tokens didn't stream
    started = last_step = time.perf_counter()
    step_count = 0
    tools_used = []
    paused = False

    try:
        for stream_mode, data in graph.stream(inputs, config=config, stream_mode=["messages", "updates"]):
            if stream_mode == "messages":
                chunk, meta = data
                if (
                    isinstance(chunk, AIMessageChunk)
                    and isinstance(chunk.content, str)
                    and chunk.content
                    and meta.get("langgraph_node") in answer_nodes
                ):
                    answer += chunk.content
                    placeholder.markdown(clean_markdown(answer) + " ▌")
                continue

            for node, node_output in data.items():
                if node == "__interrupt__":
                    paused = True
                    continue
                if not isinstance(node_output, dict):
                    continue
                now = time.perf_counter()
                step_count += 1
                if trace is not None:
                    trace_lines.extend(describe_step(node, node_output, now - last_step))
                    trace_box.markdown(timeline_html(trace_lines), unsafe_allow_html=True)
                    trace.update(label=f"Working… ({node})")
                last_step = now

                pdf_citations.extend(node_output.get("citations") or [])     # Chat with PDF node
                for f in node_output.get("findings") or []:                 # Deep Research
                    web_results.extend(f.get("sources", []))

                msgs = node_output.get("messages", [])
                if not isinstance(msgs, list):
                    msgs = [msgs]
                for m in msgs:
                    if isinstance(m, ToolMessage):
                        tools_used.append(m.name or node)
                        if (m.name or "").startswith("tavily"):
                            web_results.extend(parse_tavily_results(m))
                        elif m.name == "search_pdf" and isinstance(m.artifact, list):
                            pdf_citations.extend(m.artifact)
                        # any text before the tool call wasn't the final answer
                        answer, fallback_answer = "", ""
                        render_thinking(placeholder)
                    elif isinstance(m, AIMessage) and isinstance(m.content, str) and m.content:
                        fallback_answer = m.content
    except Exception as e:
        if trace is not None:
            trace.update(label="Run failed", state="error")
        slot.empty()
        st.error(friendly_error(e))
        return ""

    elapsed = time.perf_counter() - started
    if trace is not None:
        if paused:
            trace.update(label=f"Plan ready · {elapsed:.1f}s · waiting for your approval", state="complete")
        else:
            used = f" · used {', '.join(dict.fromkeys(tools_used))}" if tools_used else " · no tools needed"
            trace.update(label=f"Agent trace · {step_count} steps · {elapsed:.1f}s{used}",
                         state="complete", expanded=False)

    answer = answer or fallback_answer
    if not answer:
        slot.empty()
        return ""
    placeholder.markdown(clean_markdown(answer))
    if show_sources:
        render_pdf_citations(pdf_citations)
        render_sources(web_results)
    return answer


# =====================================================================
# Widget callbacks (run before the next rerun)
# =====================================================================

def _start_prompt(prompt: str):
    st.session_state.pending_prompt = prompt


def _start_news(timeframe: str):
    st.session_state.IsFetchButtonClicked = True
    st.session_state.timeframe = timeframe


def _set_research_action(action: str, job_id: str):
    st.session_state.research_action = (action, job_id)


def _request_run_again(conversation_id: int):
    st.session_state.run_again = conversation_id


@st.fragment(run_every=1.0)
def _live_job_view(job_id: str):
    """
    Watches a background job and redraws only itself once a second. When the job stops running
    it reruns the whole page, which then shows the saved report, the plan to review or the error.
    """
    job = jobs.get(job_id)
    if job is None:
        return
    snap = job.snapshot()
    if snap["status"] != "running":
        st.rerun()
    if snap["progress_html"]:
        st.markdown(snap["progress_html"], unsafe_allow_html=True)
    label = f"Working in the background · {snap['elapsed']:.0f}s · {len(snap['trace'])} steps"
    with st.expander(label, icon=":material/progress_activity:", expanded=False):
        st.markdown(timeline_html(snap["trace"]) if snap["trace"] else "Starting…", unsafe_allow_html=True)
    with st.container(key="ai_msg_live_job"):
        st.markdown(AI_HEAD, unsafe_allow_html=True)
        st.markdown(THINKING_HTML, unsafe_allow_html=True)
        st.caption("This keeps running if you switch modes or chats. Come back any time: "
                   "the result is saved to this chat.")


def _on_feedback(conversation_id: int, index: int, key: str):
    value = st.session_state.get(key)
    if value is None:
        return
    db_utils.save_feedback(conversation_id, index, int(value))
    run_id = st.session_state.get("run_ids", {}).get(f"{conversation_id}:{index}")
    from src.langgraphagenticai.settings import tracing_enabled
    if run_id and tracing_enabled():
        try:
            from langsmith import Client
            Client().create_feedback(run_id, key="user_rating", score=int(value))
        except Exception:
            pass
    st.toast("Thanks for the feedback!" if value else "Thanks, noted.")


# =====================================================================
# Main view
# =====================================================================

class DisplayResultStreamlit:
    def __init__(self, usecase, graph, user_message):
        self.usecase = usecase
        self.graph = graph
        self.user_message = user_message
        self._last_run_id = None
        self._feedback = {}
        self._job = None             # latest background job of this chat (Deep Research / AI News)
        self._job_started = False

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

    # ---------------- persistence ----------------
    def _ensure_conversation(self, first_message: str):
        if st.session_state.current_conversation_id is None:
            user_id = st.session_state.authenticated_user["id"]
            title = db_utils.make_title(first_message)
            new_id = db_utils.create_conversation(user_id, self.usecase, title)
            st.session_state.current_conversation_id = new_id

    def _persist(self, role: str, content: str) -> int:
        st.session_state.chat_history.append((role, content))
        db_utils.add_message(st.session_state.current_conversation_id, role, content)
        return len(st.session_state.chat_history) - 1

    def _persist_answer(self, answer: str):
        """Save the assistant answer, remember its LangSmith run id, show its action row."""
        if not answer:
            return
        index = self._persist("assistant", answer)
        if self._last_run_id:
            st.session_state.run_ids[f"{st.session_state.current_conversation_id}:{index}"] = self._last_run_id
        self._render_actions(answer, index)

    def _next_card_key(self) -> str:
        # unique per stream (a research run can stream twice in one rerun: pause + auto-approve);
        # reports get the "ai_msg_report" prefix for the reading layout
        kind = "report_live" if self.usecase in REPORT_MODES else "live"
        return f"ai_msg_{kind}_{len(st.session_state.chat_history)}_{uuid.uuid4().hex[:6]}"

    # ---------------- rendering ----------------
    def _render_assistant(self, content: str, index: int):
        is_report = self.usecase in REPORT_MODES
        # sources are kept by the job that wrote this report (while the server keeps it in memory)
        sources = []
        if is_report and self._job is not None and self._job.status == "done" and self._job.answer == content:
            sources = unique_sources(self._job.sources)
        with st.container(key=f"ai_msg_{'report_' if is_report else ''}{index}"):
            st.markdown(AI_HEAD, unsafe_allow_html=True)
            if is_report:
                st.markdown(report_header_html(content, sources=len(sources)), unsafe_allow_html=True)
            st.markdown(clean_markdown(content))
        if sources:
            render_sources(sources)
        self._render_actions(content, index)

    def _render_actions(self, content: str, index: int):
        cid = st.session_state.current_conversation_id
        if cid is None:
            return
        with st.container(key=f"msgactions_{index}"):
            c1, c2, c3, _ = st.columns([1.4, 1.3, 2.4, 4.9], vertical_alignment="center")
            with c1:
                key = f"fb_{cid}_{index}"
                if key not in st.session_state and index in self._feedback:
                    st.session_state[key] = self._feedback[index]
                st.feedback("thumbs", key=key, on_change=_on_feedback, args=(cid, index, key))
            with c2:
                # Streamlit has no clipboard API; st.code shows the raw text with a built-in copy icon
                with st.popover("Copy", icon=":material/content_copy:"):
                    st.caption("Use the copy icon in the top-right corner of the box.")
                    st.code(content, language="markdown", wrap_lines=True)
            if self.usecase in REPORT_MODES:
                with c3:
                    st.download_button(
                        "Download report", data=content, file_name=f"netra-report-{cid}-{index}.md",
                        mime="text/markdown", icon=":material/download:", key=f"dl_{cid}_{index}",
                    )

    def _render_welcome(self):
        info = mode(self.usecase)
        user = st.session_state.get("authenticated_user") or {}
        first_name = html.escape(((user.get("name") or user.get("username") or "").split() or ["there"])[0])

        if self.usecase == "Netra Agent":
            title = f"Hi {first_name}, what can I help with?"
        elif self.usecase == "AI News":
            title = "Your AI news digest"
        else:
            title = info["label"]

        if self.usecase == "Netra Agent":   # highlight the second half of the greeting
            title = f'Hi {first_name}, <span class="hl">what can I help with?</span>'

        hint = ""
        if info.get("pdf"):
            hint = '<div class="hero-hint">Attach a PDF with the <b>📎 clip</b> in the message box below.</div>'
        caps = "".join(
            f'<span class="cap"><span class="material-symbols-outlined">{icon}</span>{html.escape(text)}</span>'
            for icon, text in info.get("caps", [])
        )

        # Built on ONE line on purpose: in Markdown, an indented line after a blank line
        # (e.g. when `hint` is empty) becomes a code block and shows raw "</div>".
        st.markdown(
            '<div class="hero">'
            f'<div class="hero-badge"><span class="material-symbols-outlined">{info["icon"]}</span></div>'
            f'<div class="hero-title">{title}</div>'
            f'<div class="hero-sub">{html.escape(info["tagline"])}</div>'
            + (f'<div class="caps">{caps}</div>' if caps else "")
            + f'{hint}'
            '</div>',
            unsafe_allow_html=True,
        )

        starters = info.get("starters", [])
        if not starters:
            return
        if self.usecase == "AI News":
            cols = st.columns(len(starters))
            for i, (icon, timeframe) in enumerate(starters):
                with cols[i]:
                    with st.container(key=f"starter_{i}"):
                        st.button(f"{timeframe} digest", icon=f":material/{icon}:", key=f"starter_btn_{i}",
                                  width="stretch", on_click=_start_news, args=(timeframe,))
            return

        _, middle, _ = st.columns([0.08, 1, 0.08])
        with middle:
            cols = st.columns(2)
            for i, (icon, prompt) in enumerate(starters):
                with cols[i % 2]:
                    with st.container(key=f"starter_{i}"):
                        st.button(prompt, icon=f":material/{icon}:", key=f"starter_btn_{i}",
                                  width="stretch", on_click=_start_prompt, args=(prompt,))

    def _render_news_again(self):
        st.markdown('<div class="sidebar-label" style="margin-left:2px">Get another digest</div>', unsafe_allow_html=True)
        cols = st.columns([1, 1, 1, 3])
        for i, (icon, timeframe) in enumerate(mode("AI News")["starters"]):
            with cols[i]:
                with st.container(key=f"starter_again_{i}"):
                    st.button(timeframe, icon=f":material/{icon}:", key=f"news_again_{i}",
                              width="stretch", on_click=_start_news, args=(timeframe,))

    def _render_plan_review(self, job):
        text_key = f"research_plan_text_{job.id}"
        if text_key not in st.session_state:
            st.session_state[text_key] = "\n".join(job.snapshot()["plan"])
        with st.container(key="plan_review"):
            st.markdown(html_block(
                """<div class="plan-title">🗺️  Research plan</div>
                <div class="plan-sub">Edit, add or remove questions (one per line). The researcher
                agents start in parallel when you approve.</div>"""),
                unsafe_allow_html=True,
            )
            st.text_area("Research plan", key=text_key, height=150, label_visibility="collapsed")
            c1, c2, _ = st.columns([2.2, 1.2, 4])
            with c1:
                st.button("Approve & research", type="primary", icon=":material/play_arrow:", key="plan_go",
                          on_click=_set_research_action, args=("approve", job.id), width="stretch")
            with c2:
                st.button("Cancel", key="plan_cancel", on_click=_set_research_action, args=("cancel", job.id),
                          width="stretch")

    # ---------------- entry point ----------------
    def display_result_on_ui(self):
        history = st.session_state.chat_history
        if self.usecase in BACKGROUND_MODES:
            self._job = jobs.latest_for(st.session_state.current_conversation_id)

        if not history and not self.user_message:
            self._render_welcome()
            return

        self._feedback = db_utils.get_feedback(st.session_state.current_conversation_id)
        for index, (role, message) in enumerate(history):
            if role == "user":
                render_user_message(message)
            else:
                self._render_assistant(message, index)

        handler = {
            "Netra Agent": self._run_netra_agent,
            "Basic Chatbot": self._run_basic_chatbot,
            "Chatbot With Web": self._run_web_search,
            "AI News": self._run_ai_news,
            "Chat with PDF": self._run_chat_with_pdf,
            "Deep Research": self._run_deep_research,
        }.get(self.usecase)
        if handler and self.graph is not None:   # graph is None when only showing saved history (no API key)
            handler()
        if self.usecase in BACKGROUND_MODES and not self._job_started:
            self._render_job_state()

        if self.usecase == "AI News" and st.session_state.chat_history:
            self._render_news_again()

    # ---------------- modes ----------------
    def _start_turn(self) -> bool:
        """Show + save the user's message. False if there is no new message."""
        if not self.user_message:
            return False
        render_user_message(self.user_message)
        self._ensure_conversation(self.user_message)
        self._persist("user", self.user_message)
        return True

    def _memory_note(self) -> str:
        user = st.session_state.get("authenticated_user") or {}
        memories = db_utils.get_memories(user.get("id"))
        if not memories:
            return ""
        return "\n\nWhat you know about the user:\n" + "\n".join(f"- {m['content']}" for m in memories)

    def _run_netra_agent(self):
        if not self._start_turn():
            return
        from src.langgraphagenticai.memory.checkpointer import agent_config

        user_id = st.session_state.authenticated_user["id"]
        config = self._run_config(agent_config(st.session_state.current_conversation_id, user_id))

        # The checkpointer already remembers this thread, so normally we send ONLY the
        # new message. If the thread has no checkpoint yet (e.g. a conversation saved
        # before memory existed), seed it once from the saved chat history.
        remembered = self.graph.get_state(config).values.get("messages")
        new_messages = [HumanMessage(content=self.user_message)] if remembered else self._history_as_messages()

        answer = stream_graph_answer(
            self.graph, {"messages": new_messages}, answer_nodes={"agent"}, config=config,
            show_sources=True, show_trace=True, card_key=self._next_card_key(),
        )
        self._persist_answer(answer)

    def _run_basic_chatbot(self):
        if not self._start_turn():
            return
        history = [SystemMessage(content=(
            "You are Netra, an intelligent agentic AI assistant. You remember everything the user "
            "shares with you and respond helpfully and concisely." + self._memory_note()
        ))] + self._history_as_messages()
        answer = stream_graph_answer(
            self.graph, {"messages": history}, answer_nodes={"chatbot"}, config=self._run_config(),
            card_key=self._next_card_key(),
        )
        self._persist_answer(answer)

    def _run_web_search(self):
        if not self._start_turn():
            return
        history = [SystemMessage(content=(
            "You are Netra, an intelligent agentic AI assistant with web search capability. "
            "Use search results to give accurate, up-to-date answers and cite sources as markdown links."
        ))] + self._history_as_messages()
        # Only this turn's answer is rendered/saved — old answers in `history` are not repeated.
        answer = stream_graph_answer(
            self.graph, {"messages": history}, answer_nodes={"chatbot"}, config=self._run_config(),
            show_sources=True, show_trace=True, card_key=self._next_card_key(),
        )
        self._persist_answer(answer)

    def _run_ai_news(self):
        if self._busy() or self._run_again(lambda text: self._start_job({"messages": [HumanMessage(content=text)]})):
            return
        if not self._start_turn():
            return
        self._start_job({"messages": [HumanMessage(content=self.user_message)]})

    def _run_chat_with_pdf(self):
        if not self.user_message:
            return
        from src.langgraphagenticai.rag import pdf_rag_utils
        if not pdf_rag_utils.has_index(st.session_state.current_conversation_id):
            st.info("📎 Attach a PDF with the clip in the message box first, then ask your question.")
            return
        if not self._start_turn():
            return
        answer = stream_graph_answer(
            self.graph, {"messages": self._history_as_messages()}, answer_nodes={"pdf_rag"},
            config=self._run_config(), show_sources=True, card_key=self._next_card_key(),
        )
        self._persist_answer(answer)

    def _run_deep_research(self):
        from langgraph.types import Command
        from src.langgraphagenticai.nodes.research_nodes import MAX_REVIEWED_QUESTIONS, parse_questions

        job = self._job
        action, action_job = st.session_state.pop("research_action", None) or (None, None)
        if job is not None and action_job == job.id and job.status == "paused":
            if action == "approve":
                edited = parse_questions(st.session_state.get(f"research_plan_text_{job.id}", ""),
                                         limit=MAX_REVIEWED_QUESTIONS) or job.plan
                self._start_research(Command(resume={"plan": edited}), job.thread_id,
                                     ResearchProgress(total=len(edited), resumed=True))
                return
            if action == "cancel":
                jobs.cancel(job)          # the job view below then offers "Run again"
                return

        if self._busy() or self._run_again(lambda text: self._new_research(text)):
            return
        if self.user_message and job is not None and job.status == "paused":
            jobs.cancel(job)              # a new topic replaces a plan that was waiting for approval
        if not self._start_turn():
            return
        self._new_research(self.user_message)

    def _new_research(self, topic: str):
        thread_id = f"research-{st.session_state.current_conversation_id}-{uuid.uuid4().hex[:8]}"
        self._start_research({"messages": [HumanMessage(content=topic)]}, thread_id, ResearchProgress())

    def _start_research(self, inputs, thread_id: str, progress: ResearchProgress):
        self._start_job(inputs, thread_id=thread_id, progress=progress,
                        auto_approve=not st.session_state.get("research_review", True))

    # ---------------- background jobs (Deep Research / AI News) ----------------
    def _start_job(self, inputs, thread_id: str = None, progress: ResearchProgress = None, auto_approve: bool = False):
        base = {"configurable": {"thread_id": thread_id}, "recursion_limit": 30} if thread_id else None
        job = jobs.start(self.graph, inputs, self._run_config(base), st.session_state.current_conversation_id,
                         self.usecase, thread_id=thread_id, progress=progress, auto_approve=auto_approve)
        self._job, self._job_started = job, True
        _live_job_view(job.id)

    def _busy(self) -> bool:
        """A new message while this chat's job is still running: say so instead of starting a second run."""
        if self.user_message and self._job is not None and self._job.status == "running":
            st.info("Netra is still working on the previous request in this chat. "
                    "It will appear here when it's done, or start a **New chat** to ask something else.")
            self.user_message = None
            return True
        return False

    def _run_again(self, start) -> bool:
        """'Run again' was clicked: re-run the last question of this chat (it is already saved)."""
        cid = st.session_state.current_conversation_id
        history = st.session_state.chat_history
        if cid is None or st.session_state.get("run_again") != cid or not history or history[-1][0] != "user":
            return False
        st.session_state.run_again = None
        start(history[-1][1])
        return True

    def _render_job_state(self):
        """Show what the chat's background job is doing, or offer to run an unanswered question again."""
        cid = st.session_state.current_conversation_id
        history = st.session_state.chat_history
        job = self._job
        snap = job.snapshot() if job is not None else None

        if snap and snap["status"] == "running":
            _live_job_view(job.id)
            return
        if snap and snap["status"] == "paused" and self.usecase == "Deep Research":
            if snap["progress_html"]:
                st.markdown(snap["progress_html"], unsafe_allow_html=True)
            self._render_plan_review(job)
            return
        if snap and snap["status"] == "done" and not job.delivered:
            job.delivered = True
            if not (history and history[-1] == ("assistant", snap["answer"])):   # reopened chats already have it
                history.append(("assistant", snap["answer"]))      # the worker already saved it to the DB
                if job.run_id:
                    st.session_state.run_ids[f"{cid}:{len(history) - 1}"] = job.run_id
                st.rerun()

        if not history or history[-1][0] != "user":
            return
        # the last question has no answer: the run failed, was cancelled, or was lost in an app restart
        if snap and snap["status"] == "error":
            st.error(snap["error"])
        elif snap and snap["status"] == "cancelled":
            st.info("Research cancelled.")
        else:
            st.info("This request didn't finish (the app may have restarted).")
        if self.graph is not None:
            st.button("Run again", icon=":material/refresh:", key=f"run_again_{cid}",
                      on_click=_request_run_again, args=(cid,))

    # ---------------- utils ----------------
    def _run_config(self, base: dict = None) -> dict:
        """
        RunnableConfig for a graph run. The run id, name, tags and metadata label each
        run in LangSmith (when LANGSMITH_TRACING is on), so traces can be filtered by
        feature, user or conversation, and 👍/👎 feedback attaches to the right run.
        """
        config = dict(base or {})
        self._last_run_id = uuid.uuid4()
        config["run_id"] = self._last_run_id
        config["run_name"] = f"netra · {self.usecase}"
        config["tags"] = ["netra", self.usecase]
        config["metadata"] = {
            "usecase": self.usecase,
            "user_id": (st.session_state.get("authenticated_user") or {}).get("id"),
            "conversation_id": st.session_state.get("current_conversation_id"),
            "model": st.session_state.get("selected_groq_model"),
        }
        return config

    def _history_as_messages(self):
        """Saved (role, text) history -> LangChain messages (includes the current question)."""
        return [
            HumanMessage(content=m) if r == "user" else AIMessage(content=m)
            for r, m in st.session_state.chat_history
        ]
