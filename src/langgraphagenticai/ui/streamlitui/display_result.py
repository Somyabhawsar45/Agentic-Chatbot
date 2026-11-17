import html
import json
import re
import time
import uuid

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk, ToolMessage, SystemMessage

from src.langgraphagenticai.database import db_utils
from src.langgraphagenticai.ui.streamlitui.modes import mode
from src.langgraphagenticai.ui.streamlitui.theme import html_block

REPORT_MODES = ("Deep Research", "AI News")   # answers that get a "Download report" button

AI_HEAD = html_block("""<div class="ai-head"><div class="ai-avatar">
<span class="material-symbols-outlined">auto_awesome</span></div>
<span class="ai-name">Netra</span></div>""")


# =====================================================================
# Small helpers
# =====================================================================

def friendly_error(e: Exception) -> str:
    """Readable message for the errors users actually hit; anything else keeps its own text."""
    text = str(e)
    lowered = text.lower()
    if "429" in text or "rate limit" in lowered or "rate_limit" in lowered:
        wait = re.search(r"try again in ([\d.]+)\s*(ms|s)\b", text)
        seconds = None
        if wait:
            seconds = float(wait.group(1)) / (1000 if wait.group(2) == "ms" else 1)
        n = max(1, round(seconds)) if seconds is not None else None
        hint = "a minute" if n is None else f"about {n} second{'s' if n != 1 else ''}"
        return (f"The AI provider's rate limit was reached (the demo key is shared and the free tier is small). "
                f"Please wait {hint} and try again, or add your own free Groq key in ⚙ Settings.")
    if "401" in text or "invalid api key" in lowered or "invalid_api_key" in lowered:
        return "The Groq API key was rejected. Check the key in ⚙ Settings."
    return f"Something went wrong: {e}"


def clean_snippet(text: str, max_len: int = 200) -> str:
    if not text:
        return ""
    junk_patterns = [
        r"^edit this at", r"^#\s+", r"^←|^→|^↑|^↓", r"back to homepage",
        r"^jump to", r"^contents", r"^\s*\d+\s*$", r"retrieved from",
        r"wikipedia", r"wikidata", r"this page was last",
        r"categories\s*:", r"external links", r"see also", r"references",
    ]
    clean_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(re.match(p, stripped.lower()) for p in junk_patterns):
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


def _short(value, n: int = 80) -> str:
    text = str(value).replace("\n", " ")
    return text if len(text) <= n else text[: n - 1] + "…"


def render_thinking(placeholder):
    placeholder.markdown(html_block(
        """<div class="thinking-dots"><span></span><span></span><span></span></div>"""),
        unsafe_allow_html=True,
    )


def render_user_message(content: str):
    safe = html.escape(content or "").replace("\n", "<br>")
    st.markdown(f'<div class="msg-user"><div class="bubble-user">{safe}</div></div>', unsafe_allow_html=True)


# =====================================================================
# Sources & citations
# =====================================================================

def render_search_results(results: list):
    for i, r in enumerate(results[:6], 1):
        title = html.escape(r.get("title") or "Untitled")
        url = r.get("url") or "#"
        safe_url = html.escape(url, quote=True)
        snippet = html.escape(clean_snippet(r.get("content", ""), max_len=200))
        domain = html.escape(get_domain(url))
        st.markdown(html_block(
            f"""<div style="background:var(--bg-raised);border:1px solid var(--border);border-left:3px solid var(--accent);
            border-radius:12px;padding:12px 16px;margin-bottom:10px;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
            <span style="background:var(--accent-soft);color:var(--accent-2);font-size:11px;font-weight:700;
            padding:2px 8px;border-radius:20px;">{i}</span>
            <span style="color:var(--text-4);font-size:11.5px;">{domain}</span></div>
            <a href="{safe_url}" target="_blank" style="color:var(--text);font-weight:600;font-size:13.5px;
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
    """One collapsible 'Sources' box under the answer (deduplicated by URL)."""
    seen, unique = set(), []
    for r in results:
        url = r.get("url")
        if url and url not in seen:
            seen.add(url)
            unique.append(r)
    if unique:
        with st.expander(f"🌐  Sources · {len(unique)}", expanded=False):
            render_search_results(unique)


def dedupe_citations(citations: list) -> list:
    seen, unique = set(), []
    for c in citations:
        key = (c.get("page"), (c.get("text") or "")[:80])
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


def render_pdf_citations(citations: list):
    """'From your PDF' box: page number + the exact passage the answer used."""
    unique = dedupe_citations(citations)
    if not unique:
        return
    unique.sort(key=lambda c: (c.get("page") is None, c.get("page") or 0))
    with st.expander(f"📄  From your PDF · {len(unique)} passages", expanded=False):
        for c in unique:
            page = f"Page {c['page']}" if c.get("page") else "Passage"
            source = html.escape(c.get("source") or "")
            quote = html.escape(clean_snippet(c.get("text", ""), max_len=320))
            st.markdown(html_block(
                f"""<div style="background:var(--bg-raised);border:1px solid var(--border);border-left:3px solid var(--accent);
                border-radius:12px;padding:12px 16px;margin-bottom:10px;">
                <div style="color:var(--accent-2);font-size:12px;font-weight:700;margin-bottom:6px;">{page}
                <span style="color:var(--text-4);font-weight:400;"> · {source}</span></div>
                <div style="color:var(--text-2);font-size:13px;line-height:1.6;font-style:italic;">“{quote}”</div>
                </div>"""),
                unsafe_allow_html=True,
            )


# =====================================================================
# Live execution trace
# =====================================================================

def describe_step(node: str, output: dict, seconds: float) -> list:
    """Turn one node's output into human-readable trace lines (real data, not hardcoded)."""
    lines = []
    msgs = output.get("messages", [])
    if not isinstance(msgs, list):
        msgs = [msgs]

    for m in msgs:
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            for tc in m.tool_calls:
                args = ", ".join(f"{k}={_short(v, 60)!r}" for k, v in tc.get("args", {}).items())
                lines.append(f"🧠 **{node}** decided to call `{tc['name']}`({args})")
        elif isinstance(m, AIMessage) and m.content:
            lines.append(f"🧠 **{node}** wrote the answer")
        elif isinstance(m, ToolMessage):
            if m.name == "save_memory":
                lines.append(f"💾 **save_memory** → {_short(m.content, 70)}")
            else:
                lines.append(f"🔧 **{m.name or node}** returned {len(str(m.content)):,} characters")

    # non-message state updates (e.g. AI News / Deep Research pipelines)
    for key, value in output.items():
        if key in ("messages", "context"):
            continue
        if key == "findings" and isinstance(value, list):
            for f in value:
                lines.append(f"🔎 **{node}** researched “{_short(f.get('query', ''), 60)}” "
                             f"({len(f.get('sources', []))} sources)")
        elif key == "citations" and isinstance(value, list):
            pages = sorted({c.get("page") for c in value if c.get("page")})
            lines.append(f"📄 **{node}** retrieved {len(value)} passages"
                         + (f" (pages {', '.join(map(str, pages))})" if pages else ""))
        elif isinstance(value, list) and value and all(isinstance(v, str) for v in value):
            lines.append(f"⚙️ **{node}** → `{key}`: " + "; ".join(_short(v, 50) for v in value))
        elif isinstance(value, list):
            lines.append(f"⚙️ **{node}** → `{key}`: {len(value)} items")
        elif isinstance(value, str) and value:
            lines.append(f"⚙️ **{node}** → `{key}`: {_short(value, 60)}")

    if not lines:
        lines.append(f"⚙️ **{node}** finished")
    lines[-1] += f" · {seconds:.1f}s"
    return lines


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
    """
    trace = st.status("Thinking…", expanded=False) if show_trace else None
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
                    placeholder.markdown(answer + " ▌")
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
                    for line in describe_step(node, node_output, now - last_step):
                        trace.markdown(line)
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
    placeholder.markdown(answer)
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


def _set_research_action(action: str):
    st.session_state.research_action = action


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
        # unique per stream (a research run can stream twice in one rerun: pause + auto-approve)
        return f"ai_msg_live_{len(st.session_state.chat_history)}_{uuid.uuid4().hex[:6]}"

    # ---------------- rendering ----------------
    def _render_assistant(self, content: str, index: int):
        with st.container(key=f"ai_msg_{index}"):
            st.markdown(AI_HEAD, unsafe_allow_html=True)
            st.markdown(content)
        self._render_actions(content, index)

    def _render_actions(self, content: str, index: int):
        cid = st.session_state.current_conversation_id
        if cid is None:
            return
        with st.container(key=f"msgactions_{index}"):
            c1, c2, _ = st.columns([1.4, 2.4, 6], vertical_alignment="center")
            with c1:
                key = f"fb_{cid}_{index}"
                if key not in st.session_state and index in self._feedback:
                    st.session_state[key] = self._feedback[index]
                st.feedback("thumbs", key=key, on_change=_on_feedback, args=(cid, index, key))
            if self.usecase in REPORT_MODES:
                with c2:
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

        hint = ""
        if info.get("pdf"):
            hint = '<div class="hero-hint">Attach a PDF with the <b>📎 clip</b> in the message box below.</div>'

        # Built on ONE line on purpose: in Markdown, an indented line after a blank line
        # (e.g. when `hint` is empty) becomes a code block and shows raw "</div>".
        st.markdown(
            '<div class="hero">'
            f'<div class="hero-badge"><span class="material-symbols-outlined">{info["icon"]}</span></div>'
            f'<div class="hero-title">{title}</div>'
            f'<div class="hero-sub">{html.escape(info["tagline"])}</div>'
            f'{hint}'
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
                                  use_container_width=True, on_click=_start_news, args=(timeframe,))
            return

        _, middle, _ = st.columns([0.08, 1, 0.08])
        with middle:
            cols = st.columns(2)
            for i, (icon, prompt) in enumerate(starters):
                with cols[i % 2]:
                    with st.container(key=f"starter_{i}"):
                        st.button(prompt, icon=f":material/{icon}:", key=f"starter_btn_{i}",
                                  use_container_width=True, on_click=_start_prompt, args=(prompt,))

    def _render_news_again(self):
        st.markdown('<div class="sidebar-label" style="margin-left:2px">Get another digest</div>', unsafe_allow_html=True)
        cols = st.columns([1, 1, 1, 3])
        for i, (icon, timeframe) in enumerate(mode("AI News")["starters"]):
            with cols[i]:
                with st.container(key=f"starter_again_{i}"):
                    st.button(timeframe, icon=f":material/{icon}:", key=f"news_again_{i}",
                              use_container_width=True, on_click=_start_news, args=(timeframe,))

    def _render_plan_review(self):
        with st.container(key="plan_review"):
            st.markdown(html_block(
                """<div class="plan-title">🗺️  Research plan</div>
                <div class="plan-sub">Edit, add or remove questions (one per line). The researcher
                agents start in parallel when you approve.</div>"""),
                unsafe_allow_html=True,
            )
            st.text_area("Research plan", key="research_plan_text", height=150, label_visibility="collapsed")
            c1, c2, _ = st.columns([2.2, 1.2, 4])
            with c1:
                st.button("Approve & research", type="primary", icon=":material/play_arrow:", key="plan_go",
                          on_click=_set_research_action, args=("approve",), use_container_width=True)
            with c2:
                st.button("Cancel", key="plan_cancel", on_click=_set_research_action, args=("cancel",),
                          use_container_width=True)

    # ---------------- entry point ----------------
    def display_result_on_ui(self):
        history = st.session_state.chat_history
        pending_research = self.usecase == "Deep Research" and st.session_state.get("research_pending")

        if not history and not self.user_message and not pending_research:
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
        if handler:
            handler()

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
        if not self._start_turn():
            return
        # answer_nodes is empty: the many map-step LLM calls aren't shown as tokens;
        # the final report arrives as the save_result node's message.
        report = stream_graph_answer(
            self.graph, {"messages": [HumanMessage(content=self.user_message)]}, answer_nodes=set(),
            config=self._run_config(), show_trace=True, card_key=self._next_card_key(),
        )
        self._persist_answer(report)

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

        pending = st.session_state.get("research_pending")
        action = st.session_state.pop("research_action", None)

        if pending and self.user_message and action is None:
            # a new topic was typed while a plan was waiting: drop the old plan
            st.session_state.research_pending = pending = None

        if pending and action == "approve":
            edited = parse_questions(st.session_state.get("research_plan_text", ""), limit=MAX_REVIEWED_QUESTIONS)
            st.session_state.research_pending = None
            self._research(Command(resume={"plan": edited or pending["plan"]}), pending["thread_id"])
            return
        if pending and action == "cancel":
            st.session_state.research_pending = None
            st.info("Research cancelled. Enter a new topic whenever you're ready.")
            return
        if pending:
            self._render_plan_review()
            return

        if not self._start_turn():
            return
        thread_id = f"research-{st.session_state.current_conversation_id}-{uuid.uuid4().hex[:8]}"
        self._research({"messages": [HumanMessage(content=self.user_message)]}, thread_id)

    def _research(self, inputs, thread_id: str):
        """Run (or resume) the research graph; pause for plan review when enabled."""
        from langgraph.types import Command

        config = self._run_config({"configurable": {"thread_id": thread_id}, "recursion_limit": 30})
        report = stream_graph_answer(
            self.graph, inputs, answer_nodes=set(), config=config,
            show_sources=True, show_trace=True, card_key=self._next_card_key(),
        )

        snapshot = self.graph.get_state(config)
        if snapshot.next:  # paused at human_review
            plan = snapshot.values.get("plan", [])
            if st.session_state.get("research_review", True):
                st.session_state.research_pending = {"thread_id": thread_id, "plan": plan}
                st.session_state.research_plan_text = "\n".join(plan)
                self._render_plan_review()
            else:
                self._research(Command(resume={"plan": plan}), thread_id)  # auto-approve
            return
        self._persist_answer(report)

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
