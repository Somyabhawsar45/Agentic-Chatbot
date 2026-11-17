"""
Small HTML builders for the chat UI.

Pure functions (no Streamlit), so they are easy to test. Everything that comes from a model,
a web page, a PDF or a user is escaped here, and only http(s) links are ever emitted.
Keep this file Python 3.11 compatible (Streamlit Cloud): no backslashes inside f-string braces.
"""
import html
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


def clean_markdown(text: str) -> str:
    """
    Models often put <br> inside markdown tables. Streamlit (rightly) doesn't render raw HTML,
    so the tag showed up as text. In table rows it becomes a separator; elsewhere a line break.
    Code blocks are left untouched.
    """
    if not text:
        return text or ""
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


def source_pills_html(results: list, limit: int = 8) -> str:
    """A row of numbered domain pills linking to the sources used for the answer."""
    pills = []
    for n, r in enumerate(unique_sources(results)[:limit], 1):
        url = html.escape(r["url"], quote=True)
        title = html.escape(r.get("title") or get_domain(r["url"]), quote=True)
        domain = html.escape(get_domain(r["url"]))
        pills.append(
            f'<a class="src-pill" href="{url}" target="_blank" rel="noopener noreferrer" title="{title}">'
            f'<span class="src-num">{n}</span>{domain}</a>'
        )
    if not pills:
        return ""
    return '<div class="src-row"><span class="src-label">Sources</span>' + "".join(pills) + "</div>"


def _page_label(page) -> str:
    return f"p. {int(page)}" if str(page).isdigit() else "passage"


def citation_chips_html(citations: list) -> str:
    """'p. 7' chips under a PDF answer; clicking one opens the exact quoted passage."""
    unique = dedupe_citations(citations)
    if not unique:
        return ""
    unique.sort(key=lambda c: (not str(c.get("page")).isdigit(), int(c["page"]) if str(c.get("page")).isdigit() else 0))
    chips = []
    for c in unique:
        quote = html.escape(clean_snippet(c.get("text", ""), max_len=320))
        source = html.escape(c.get("source") or "")
        chips.append(
            '<details class="cite-chip"><summary>'
            '<span class="material-symbols-outlined">description</span>'
            f'{_page_label(c.get("page"))}</summary>'
            f'<div class="cite-pop">“{quote}”<div class="cite-src">{source}</div></div></details>'
        )
    return '<div class="cite-row"><span class="src-label">From your PDF</span>' + "".join(chips) + "</div>"


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
    """Follows the Deep Research graph node by node and draws a stage tracker."""

    STAGES = [
        ("planner", "Plan", "edit_note"),
        ("human_review", "Your review", "fact_check"),
        ("researcher", "Research", "travel_explore"),
        ("writer", "Write", "draw"),
        ("critic", "Critique", "rate_review"),
    ]

    def __init__(self, total: int = 0, resumed: bool = False):
        self.total = total
        self.researched = 0
        self.done = {"planner", "human_review"} if resumed else set()
        self.active = "researcher" if resumed else "planner"
        self.waiting = False
        self.finished = False

    def update(self, node: str, output: dict) -> None:
        output = output or {}
        if node in ("planner", "human_review"):
            self.total = len(output.get("plan") or []) or self.total
            self.done.add(node)
            self.active = "human_review" if node == "planner" else "researcher"
        elif node == "researcher":
            self.researched += max(1, len(output.get("findings") or []))
            if self.total and self.researched >= self.total:
                self.done.add("researcher")
                self.active = "writer"
        elif node == "writer":
            self.done.update({"researcher", "writer"})
            self.active = "critic"
        elif node == "critic":
            self.done.add("critic")
            approved = str(output.get("critique", "")).strip().upper().startswith("APPROVED")
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
            "writer": "Writing the report…",
            "critic": "A critic is reviewing the draft…",
            "finalize": "Finishing up…",
        }.get(self.active, "Working…")

    def html(self) -> str:
        steps = []
        for i, (stage, label, icon) in enumerate(self.STAGES):
            if stage in self.done and stage != self.active:
                state, glyph = "done", "check"
            elif stage == self.active:
                state, glyph = ("wait" if self.waiting else "active"), icon
            else:
                state, glyph = "todo", icon
            if stage == "researcher" and self.total:
                label = f"Research {min(self.researched, self.total)}/{self.total}"
            if i:
                steps.append(f'<div class="rp-bar {"done" if stage in self.done or stage == self.active else ""}"></div>')
            steps.append(f'<div class="rp-step {state}"><span class="rp-icon material-symbols-outlined">{glyph}</span>'
                         f'<span class="rp-label">{html.escape(label)}</span></div>')
        return (f'<div class="rp"><div class="rp-steps">{"".join(steps)}</div>'
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
