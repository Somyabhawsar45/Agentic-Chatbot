"""
Small HTML builders for the chat UI.

Pure functions (no Streamlit), so they are easy to test. Everything that comes from a model,
a web page, a PDF or a user is escaped here, and only http(s) links are ever emitted.
Keep this file Python 3.11 compatible (Streamlit Cloud): no backslashes inside f-string braces.
"""
import html
import json
import re
from urllib.parse import urlparse

from langchain_core.messages import AIMessage, ToolMessage

# =====================================================================
# Text helpers
# =====================================================================

_JUNK_PATTERNS = [
    r"^edit this at", r"^#\s+", r"^←|^→|^↑|^↓", r"back to homepage",
    r"^jump to", r"^contents", r"^\s*\d+\s*$", r"retrieved from",
    r"wikipedia", r"wikidata", r"this page was last",
    r"categories\s*:", r"external links", r"see also", r"references",
]


def clean_snippet(text: str, max_len: int = 200) -> str:
    """Readable one-paragraph excerpt of a web page / PDF passage."""
    if not text:
        return ""
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not any(re.match(p, stripped.lower()) for p in _JUNK_PATTERNS):
            lines.append(stripped)
    clean = " ".join(lines)
    if len(clean) > max_len:
        cut = clean[:max_len]
        last_period = cut.rfind(".")
        clean = cut[: last_period + 1] if last_period > max_len * 0.6 else cut.rstrip() + "…"
    return clean


def get_domain(url: str) -> str:
    match = re.search(r"https?://(?:www\.)?([^/]+)", str(url or ""))
    return match.group(1) if match else str(url or "")


def safe_url(url):
    """The URL if it is a plain http(s) link, else None (blocks javascript:, data:, ...)."""
    try:
        parsed = urlparse(str(url or "").strip())
    except ValueError:
        return None
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return parsed.geturl()
    return None


_BR = re.compile(r"\s*<br\s*/?>\s*", re.IGNORECASE)
_BR_BEFORE_BULLET = re.compile(r"\s*<br\s*/?>\s*(?=[•\-*–])", re.IGNORECASE)


def _clean_table_row(line: str) -> str:
    # "• A<br>• B" -> "• A • B";  "Early growth<br>Mostly P2P" -> "Early growth; Mostly P2P"
    return _BR.sub("; ", _BR_BEFORE_BULLET.sub(" ", line))


# gpt-oss sometimes leaks its raw tool-call markup into the answer text, e.g.
# "【assistant to=tavily_search<|channel|>commentary <|constrain|>json<|message|>{...}". Cut it off.
_LEAKED_TOOL_CALL = re.compile(r"\s*(?:【\s*)?(?:assistant\s+)?to=[\w.]+\s*<\|channel\|>.*$", re.DOTALL)
_SPECIAL_TOKEN = re.compile(r"<\|[a-z_]+\|>")
# ...and its internal citation markers like "【7b2fcb-00】" or "【4†source】" (meaningless to readers)
_CITATION_MARK = re.compile(r"\s?【[^】\n]{1,60}】")


# ...but a bracket holding a real link becomes a small clickable source: "【https://x.org/a】" -> " ([x.org](https://x.org/a))"
_CITATION_LINK = re.compile(r"\s?【\s*(https?://[^\s】]+)\s*】")


def _citation_link(match) -> str:
    url = safe_url(match.group(1))
    return f" ([{get_domain(url)}]({url}))" if url else ""


def strip_leaked_tool_calls(text: str) -> str:
    text = _LEAKED_TOOL_CALL.sub("", text or "")
    text = _CITATION_LINK.sub(_citation_link, text)
    text = _CITATION_MARK.sub("", text)
    return _SPECIAL_TOKEN.sub("", text).rstrip()


def clean_markdown(text: str) -> str:
    """
    Models often put <br> inside markdown tables. Streamlit (rightly) doesn't render raw HTML,
    so the tag showed up as text. In table rows it becomes a separator; elsewhere a line break.
    Code blocks are left untouched.
    """
    if not text:
        return text or ""
    text = strip_leaked_tool_calls(text)
    out, in_code = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_code = not in_code
            out.append(line)
        elif in_code:
            out.append(line)
        elif line.lstrip().startswith("|"):
            out.append(_clean_table_row(line))
        else:
            out.append(_BR.sub("  \n", line))
    return "\n".join(out)


def md_inline(text: str) -> str:
    """Escape, then allow just **bold** and `code` (used for trace lines)."""
    escaped = html.escape(str(text or ""))
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)


# =====================================================================
# Sources & citations
# =====================================================================

def dedupe_citations(citations: list) -> list:
    seen, unique = set(), []
    for c in citations or []:
        key = (c.get("page"), (c.get("text") or "")[:80])
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


def unique_sources(results: list) -> list:
    """Web results with a safe, not-yet-seen URL, in order."""
    seen, unique = set(), []
    for r in results or []:
        url = safe_url(r.get("url"))
        if url and url not in seen:
            seen.add(url)
            unique.append({**r, "url": url})
    return unique


def favicon_html(url: str) -> str:
    """
    The site's icon in a small circle. Under the icon sits the site's first letter on a colour
    picked from the domain, so a site without an icon (or offline) still gets a neat badge.
    """
    domain = get_domain(url)
    letter = html.escape((domain[:1] or "?").upper())
    hue = sum(ord(ch) for ch in domain) * 37 % 360
    icon = html.escape(f"https://www.google.com/s2/favicons?domain={domain}&sz=64", quote=True)
    return (f'<span class="fav" style="--fav-h:{hue}">{letter}'
            f'<img src="{icon}" alt="" loading="lazy" referrerpolicy="no-referrer"></span>')


def source_pills_html(results: list, limit: int = 8) -> str:
    """Stacked site icons with a count, then one pill per source (icon + domain) linking to it."""
    sources = unique_sources(results)
    pills = []
    for r in sources[:limit]:
        url = html.escape(r["url"], quote=True)
        title = html.escape(r.get("title") or get_domain(r["url"]), quote=True)
        domain = html.escape(get_domain(r["url"]))
        pills.append(
            f'<a class="src-pill" href="{url}" target="_blank" rel="noopener noreferrer" title="{title}">'
            f'{favicon_html(r["url"])}{domain}</a>'
        )
    if not pills:
        return ""
    distinct = list(dict.fromkeys(get_domain(r["url"]) for r in sources))
    stack = "".join(favicon_html("https://" + d) for d in distinct[:4])
    count = f'{len(sources)} source{"" if len(sources) == 1 else "s"}'
    return (f'<div class="src-row"><span class="src-stack">{stack}</span><span class="src-count">{count}</span>'
            + "".join(pills) + "</div>")


# =====================================================================
# Typing effects (pure CSS: no scripts, nothing to load)
# =====================================================================

_HL_FROM, _HL_TO = (0x9D, 0xC0, 0xFF), (0x4F, 0x8E, 0xF7)   # the greeting's light-to-accent blue


def _blend(i: int, n: int) -> str:
    t = i / max(1, n - 1)
    return "#" + "".join(f"{round(a + (b - a) * t):02x}" for a, b in zip(_HL_FROM, _HL_TO))


def typed_html(plain: str, highlight: str = "", step_ms: int = 38, start_ms: int = 250) -> str:
    """
    A heading that types itself out once: every letter fades in a moment after the one before,
    then a cursor blinks a few times and disappears. The `highlight` part gets the blue gradient
    (coloured letter by letter, since a gradient clipped to text can't fade in per letter).
    Words are kept whole so a line never breaks in the middle of one.
    """
    out, i = [], 0
    for part, colourful in ((plain, False), (highlight, True)):
        letters = [ch for ch in part if not ch.isspace()]
        n_col, k = len(letters), 0
        for word in re.split(r"(\s+)", part):
            if not word:
                continue
            if word.isspace():
                out.append(" ")
                i += 1
                continue
            spans = []
            for ch in word:
                colour = f";color:{_blend(k, n_col)}" if colourful else ""
                spans.append(f'<span class="ch" style="--d:{start_ms + i * step_ms}ms{colour}">{html.escape(ch)}</span>')
                i += 1
                k += 1
            out.append(f'<span class="tw">{"".join(spans)}</span>')
    done = start_ms + i * step_ms
    label = html.escape(f"{plain}{highlight}", quote=True)
    return (f'<span class="typed" role="text" aria-label="{label}"><span aria-hidden="true">{"".join(out)}'
            f'<span class="type-cur" style="--d:{done}ms"></span></span></span>')


def css_string(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def typing_hints_css(hints: list, type_ms: int = 55, hold_ms: int = 1700, gap_ms: int = 350) -> str:
    """
    While the message box is empty, it types example questions one after another (then clears
    and types the next). Built as CSS keyframes that switch the text letter by letter; people
    who prefer reduced motion just see the first example.
    """
    hints = [h.strip() for h in hints if h and h.strip()][:5]
    if not hints:
        return ""
    frames, t = [], 0
    for hint in hints:
        for n in range(1, len(hint) + 1):
            frames.append((t, hint[:n] + "▏"))
            t += type_ms
        frames.append((t, hint))
        t += hold_ms
        frames.append((t, ""))
        t += gap_ms
    body = "".join(f"{100 * at / t:.3f}%{{content:{css_string(txt)}}}" for at, txt in frames)
    target = '[data-testid="stChatInput"] div:has(> textarea:placeholder-shown)'
    return (
        "<style>"
        f"@keyframes netraHints{{{body}100%{{content:\"\"}}}}"
        f'{target} textarea::placeholder{{color:transparent !important;}}'
        f'{target}::after{{content:{css_string(hints[0])};animation:netraHints {t}ms step-end infinite;}}'
        f"@media (prefers-reduced-motion: reduce){{{target}::after{{animation:none !important;"
        f"content:{css_string(hints[0])};}}}}"
        "</style>"
    )


def _page_label(page) -> str:
    return f"p. {int(page)}" if str(page).isdigit() else "passage"


_PAGE_REF = re.compile(r"\b(?:pp?\.|pages?)\s*(\d+(?:\s*(?:[-–,]|and)\s*\d+)*)", re.IGNORECASE)


def cited_pages(answer: str) -> set:
    """Page numbers the answer itself cites: "(p. 2)", "pp. 3–5", "page 4 and 6" -> {2, 3, 4, 5, 6}."""
    pages = set()
    for group in _PAGE_REF.findall(answer or ""):
        numbers = [int(n) for n in re.findall(r"\d+", group)]
        if re.search(r"\d\s*[-–]\s*\d", group) and len(numbers) == 2 and 0 < numbers[1] - numbers[0] <= 20:
            pages.update(range(numbers[0], numbers[1] + 1))      # a range like pp. 3–5
        else:
            pages.update(numbers)
    return pages


def _chip(c: dict, extra_class: str = "") -> str:
    quote = html.escape(clean_snippet(c.get("text", ""), max_len=320))
    source = html.escape(c.get("source") or "")
    return (f'<details class="cite-chip{extra_class}"><summary>'
            '<span class="material-symbols-outlined">description</span>'
            f'{_page_label(c.get("page"))}</summary>'
            f'<div class="cite-pop">“{quote}”<div class="cite-src">{source}</div></div></details>')


def citation_chips_html(citations: list, answer: str = "") -> str:
    """
    'p. 7' chips under a PDF answer; clicking one opens the exact quoted passage. The pages the
    answer actually cites come first; the other pages Netra looked at follow, quieter, under
    "Also checked".
    """
    unique = dedupe_citations(citations)
    if not unique:
        return ""
    unique.sort(key=lambda c: (not str(c.get("page")).isdigit(), int(c["page"]) if str(c.get("page")).isdigit() else 0))
    cited = cited_pages(answer)
    is_cited = lambda c: str(c.get("page")).isdigit() and int(c["page"]) in cited   # noqa: E731
    used = [c for c in unique if is_cited(c)]
    if not used:      # the answer names no page we retrieved: show them all, as before
        return ('<div class="cite-row"><span class="src-label">From your PDF</span>'
                + "".join(_chip(c) for c in unique) + "</div>")
    others = [c for c in unique if not is_cited(c)]
    row = '<div class="cite-row"><span class="src-label">From your PDF</span>' + "".join(_chip(c) for c in used)
    if others:
        row += '<span class="src-label cite-also-label">Also checked</span>' + "".join(_chip(c, " also") for c in others)
    return row + "</div>"


# =====================================================================
# Agent trace timeline
# =====================================================================

_TRACE_ICONS = [("🧠", "psychology"), ("🔧", "build"), ("💾", "bookmark_added"), ("🔎", "travel_explore"),
                ("📄", "description"), ("⚙️", "settings"), ("⚙", "settings")]
_DURATION = re.compile(r" · (\d+(?:\.\d+)?s)$")


def timeline_item_html(line: str) -> str:
    icon, text = "radio_button_checked", str(line)
    for emoji, name in _TRACE_ICONS:
        if text.startswith(emoji):
            icon, text = name, text[len(emoji):].strip()
            break
    duration = ""
    match = _DURATION.search(text)
    if match:
        duration = f'<span class="tl-time">{match.group(1)}</span>'
        text = text[: match.start()]
    return (f'<div class="tl-item"><span class="tl-dot"><span class="material-symbols-outlined">{icon}</span></span>'
            f'<div class="tl-text">{md_inline(text)}</div>{duration}</div>')


def timeline_html(lines: list) -> str:
    return '<div class="timeline">' + "".join(timeline_item_html(line) for line in lines) + "</div>"


# =====================================================================
# Deep Research progress tracker
# =====================================================================

class ResearchProgress:
    """
    Follows the Deep Research graph node by node and draws it as a live agent map:
    Planner -> one card per parallel Researcher (with its question) -> Writer <-> Critic -> Report.
    Cards light up while their agent works and get a tick when it is done.
    """

    STAGES = [
        ("planner", "Plan", "edit_note"),
        ("human_review", "Your review", "fact_check"),
        ("researcher", "Research", "travel_explore"),
        ("writer", "Write", "draw"),
        ("critic", "Critique", "rate_review"),
    ]
    MAX_CARDS = 6

    def __init__(self, total: int = 0, resumed: bool = False, plan: list = None):
        self.plan = [str(q) for q in (plan or [])]
        self.total = total or len(self.plan)
        self.researched = 0
        self.done_queries = set()
        self.revisions = 0
        self.done = {"planner", "human_review"} if resumed else set()
        self.active = "researcher" if resumed else "planner"
        self.waiting = False
        self.finished = False

    def update(self, node: str, output: dict) -> None:
        output = output or {}
        if node in ("planner", "human_review"):
            if output.get("plan"):
                self.plan = [str(q) for q in output["plan"]]
            self.total = len(self.plan) or self.total
            self.done.add(node)
            self.active = "human_review" if node == "planner" else "researcher"
        elif node == "researcher":
            findings = output.get("findings") or []
            self.researched += max(1, len(findings))
            self.done_queries.update(str(f.get("query")) for f in findings if isinstance(f, dict) and f.get("query"))
            if self.total and self.researched >= self.total:
                self.done.add("researcher")
                self.active = "writer"
        elif node == "writer":
            self.done.update({"researcher", "writer"})
            self.active = "critic"
        elif node == "critic":
            self.done.add("critic")
            approved = str(output.get("critique", "")).strip().upper().startswith("APPROVED")
            if not approved:
                self.revisions += 1
            self.active = "finalize" if approved else "writer"
        elif node == "finalize":
            self.done.update(stage for stage, _, _ in self.STAGES)
            self.finished = True
            self.active = None

    def pause(self) -> None:
        self.waiting = True
        self.active = "human_review"

    def status_text(self) -> str:
        if self.finished:
            return "Report ready"
        if self.waiting:
            return "Waiting for you to approve the plan"
        return {
            "planner": "Planning the research questions…",
            "human_review": "Plan approved, starting researchers…",
            "researcher": f"Researching in parallel · {self.researched} of {self.total or '?'} done",
            "writer": "Writing the report…" if not self.revisions else f"Revising the report (round {self.revisions + 1})…",
            "critic": "A critic is reviewing the draft…",
            "finalize": "Finishing up…",
        }.get(self.active, "Working…")

    # ---------------- drawing ----------------
    def _state(self, stage: str) -> str:
        if stage == self.active:
            return "wait" if self.waiting else "active"
        return "done" if stage in self.done or self.finished else "todo"

    @staticmethod
    def _card(state: str, icon: str, title: str, sub: str = "") -> str:
        glyph = "check" if state == "done" else icon
        sub_html = f'<div class="am-sub" title="{html.escape(sub, quote=True)}">{html.escape(sub)}</div>' if sub else ""
        return (f'<div class="am-node {state}"><span class="am-ic material-symbols-outlined">{glyph}</span>'
                f'<div class="am-text"><div class="am-title">{html.escape(title)}</div>{sub_html}</div></div>')

    @staticmethod
    def _edge(lit: bool, flowing: bool) -> str:
        return f'<div class="am-edge{" on" if lit else ""}{" flow" if flowing else ""}"></div>'

    def _researcher_cards(self) -> str:
        n = min(max(self.total, len(self.plan)), self.MAX_CARDS)
        stage = self._state("researcher")
        if not n:   # still planning: three faint placeholder researchers
            return "".join(self._card("todo", "travel_explore", f"Researcher {i}", "waiting for the plan")
                           for i in (1, 2, 3))
        cards = []
        for i in range(n):
            question = self.plan[i] if i < len(self.plan) else ""
            finished = (question in self.done_queries) if question and self.done_queries else i < self.researched
            if stage == "done" or self.finished or finished:
                state = "done"
            elif stage in ("active",):
                state = "active"
            elif self.waiting:
                state = "wait"
            else:
                state = "todo"
            cards.append(self._card(state, "travel_explore", f"Researcher {i + 1}", question or "web search"))
        return "".join(cards)

    def html(self) -> str:
        planner = self._state("planner")
        planner_sub = f"{self.total} questions" if self.total else "breaking the topic down"
        if self.waiting:
            planner, planner_sub = "wait", "waiting for your OK"
        researching = self._state("researcher")
        writer, critic = self._state("writer"), self._state("critic")
        report = "done" if self.finished else ("active" if self.active == "finalize" else "todo")
        writer_sub = f"revision {self.revisions}" if self.revisions else "drafts the report"
        critic_sub = "checks facts & gaps"
        parts = [
            '<div class="am-col">', self._card(planner, "edit_note", "Planner", planner_sub), "</div>",
            self._edge(planner == "done", researching == "active"),
            '<div class="am-col am-fan">', self._researcher_cards(), "</div>",
            self._edge(researching == "done", writer == "active"),
            '<div class="am-col">', self._card(writer, "draw", "Writer", writer_sub), "</div>",
            self._edge(writer == "done" or critic != "todo", critic == "active" or (writer == "active" and self.revisions > 0)),
            '<div class="am-col">', self._card(critic, "rate_review", "Critic", critic_sub), "</div>",
            self._edge(report != "todo", report == "active"),
            '<div class="am-col">', self._card(report, "article", "Report", "with sources"), "</div>",
        ]
        return (f'<div class="rp"><div class="amap">{"".join(parts)}</div>'
                f'<div class="rp-status">{html.escape(self.status_text())}</div></div>')


# =====================================================================
# Report view
# =====================================================================

_HEADING = re.compile(r"^(#{1,3})\s+(.+?)\s*#*\s*$", re.MULTILINE)


def report_outline(markdown: str) -> dict:
    """Headings, word count and reading time of a markdown report."""
    text = markdown or ""
    headings = [(len(h), re.sub(r"[*_`]", "", t).strip()) for h, t in _HEADING.findall(text)]
    words = len(re.findall(r"\w+", re.sub(r"https?://\S+", "", text)))
    return {"headings": headings, "words": words, "minutes": max(1, round(words / 200))}


def share_title(markdown: str, limit: int = 80) -> str:
    """A short title for a shared answer: its first heading, else its first line."""
    outline = report_outline(markdown)
    if outline["headings"]:
        title = outline["headings"][0][1]
    else:
        first = next((line.strip() for line in (markdown or "").splitlines() if line.strip()), "")
        title = re.sub(r"[*_`#>]", "", first).strip()
    title = title or "Netra answer"
    return title if len(title) <= limit else title[: limit - 1].rstrip() + "…"


def share_url(page_url: str, token: str) -> str:
    """Public link for a share token, built from the app's own address (query string dropped)."""
    base = str(page_url or "").split("?")[0].split("#")[0]
    if not base.endswith("/"):
        base += "/"
    return f"{base}?share={token}"


def report_header_html(markdown: str, sources: int = 0) -> str:
    """Card above a report: size, reading time and a contents strip."""
    outline = report_outline(markdown)
    sections = [t for level, t in outline["headings"] if level >= 2][:8]
    meta = f'{outline["words"]:,} words · {outline["minutes"]} min read'
    if sources:
        meta += f" · {sources} sources"
    contents = "".join(f'<span class="toc-chip">{html.escape(t)}</span>' for t in sections)
    return ('<div class="report-head"><div class="report-title">'
            '<span class="material-symbols-outlined">summarize</span>Report</div>'
            f'<div class="report-meta">{meta}</div>'
            + (f'<div class="toc">{contents}</div>' if contents else "") + "</div>")


# =====================================================================
# Errors and trace lines (also used by the background job runner, so no Streamlit here)
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


def _short(value, n: int = 80) -> str:
    text = str(value).replace("\n", " ")
    return text if len(text) <= n else text[: n - 1] + "…"


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


# =====================================================================
# One-click copy
# =====================================================================

def copy_button_html(text: str, uid: str, label: str = "Copy") -> str:
    """
    A small button that copies `text` to the clipboard and briefly says "Copied". Rendered with
    st.html(unsafe_allow_javascript=True). The text is embedded as a JSON string with "</" escaped,
    so it can never close the <script> tag early.
    """
    bid = "cp-" + re.sub(r"[^A-Za-z0-9_-]", "", str(uid))
    payload = json.dumps(text or "").replace("</", r"<\/")
    return (
        f'<button class="copy-btn" id="{bid}" type="button" title="{html.escape(label, quote=True)}">'
        f'<span class="material-symbols-outlined">content_copy</span><span class="cp-label">{html.escape(label)}</span>'
        "</button><script>(function(){"
        f'const b=document.getElementById("{bid}");if(!b||b.dataset.ready)return;b.dataset.ready="1";'
        f"const t={payload};const l=b.querySelector('.cp-label');"
        "b.addEventListener('click',async function(){"
        "try{await navigator.clipboard.writeText(t);}catch(e){const a=document.createElement('textarea');"
        "a.value=t;document.body.appendChild(a);a.select();document.execCommand('copy');a.remove();}"
        f"b.classList.add('done');l.textContent='Copied';setTimeout(function(){{b.classList.remove('done');l.textContent={json.dumps(label)};}},1500);"
        "});})();</script>"
    )
