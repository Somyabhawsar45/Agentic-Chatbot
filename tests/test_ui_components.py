"""The HTML builders behind the redesigned chat UI (pure functions, no Streamlit)."""
from src.langgraphagenticai.ui.streamlitui import components as c
from src.langgraphagenticai.ui.streamlitui.modes import MODES, NAV_ORDER


# ---------------- markdown clean-up ----------------

def test_br_in_tables_becomes_a_separator_and_elsewhere_a_line_break():
    md = ("| Use | Notes |\n|---|---|\n| RAG | • Q&A<br>• Fresh facts<BR/>• Docs |\n"
          "| 2019 | Early growth<br>Mostly P2P |\n"
          "Line one<br>Line two\n```\ncode <br> stays\n```")
    out = c.clean_markdown(md)
    assert "| RAG | • Q&A • Fresh facts • Docs |" in out          # before a bullet: just a space
    assert "| 2019 | Early growth; Mostly P2P |" in out           # otherwise: "; "
    assert "Line one  \nLine two" in out
    assert "code <br> stays" in out            # code blocks untouched
    assert c.clean_markdown("") == "" and c.clean_markdown(None) == ""


def test_inline_markdown_is_escaped_before_formatting():
    out = c.md_inline('**agent** called `search`(q="<script>x</script>")')
    assert out.startswith("<b>agent</b> called <code>search</code>")
    assert "<script>" not in out and "&lt;script&gt;" in out


# ---------------- links, sources, citations ----------------

def test_only_http_links_are_allowed():
    assert c.safe_url("https://example.com/a?b=1") == "https://example.com/a?b=1"
    for bad in ("javascript:alert(1)", "data:text/html,hi", "ftp://x.com", "", None, "notaurl"):
        assert c.safe_url(bad) is None


def test_source_pills_dedupe_number_escape_and_drop_unsafe_links():
    results = [
        {"title": 'A "quoted" <b>title</b>', "url": "https://www.example.com/a"},
        {"title": "dup", "url": "https://www.example.com/a"},
        {"title": "evil", "url": "javascript:alert(1)"},
        {"title": "B", "url": "https://news.test/b"},
    ]
    html_out = c.source_pills_html(results)
    assert html_out.count('class="src-pill"') == 2
    assert ">1</span>example.com</a>" in html_out and ">2</span>news.test</a>" in html_out
    assert "javascript:" not in html_out and "<b>title</b>" not in html_out
    assert 'rel="noopener noreferrer"' in html_out
    assert c.source_pills_html([]) == ""


def test_citation_chips_sorted_by_page_with_escaped_quotes():
    cites = [
        {"page": 7, "text": "Audit chair is Meera Iyer.", "source": "r.pdf"},
        {"page": 2, "text": "Revenue <i>grew</i> 18%.", "source": "r.pdf"},
        {"page": 2, "text": "Revenue <i>grew</i> 18%.", "source": "r.pdf"},     # duplicate
        {"page": None, "text": "no page", "source": ""},
    ]
    out = c.citation_chips_html(cites)
    assert out.count('class="cite-chip"') == 3
    assert out.index("p. 2") < out.index("p. 7") < out.index("passage")
    assert "<i>grew</i>" not in out and "&lt;i&gt;grew&lt;/i&gt;" in out
    assert c.citation_chips_html([]) == ""


# ---------------- trace timeline ----------------

def test_timeline_maps_emoji_to_icons_and_splits_out_the_duration():
    out = c.timeline_html(["🧠 **agent** decided to call `tavily_search`(query='x') · 1.2s",
                           "🔧 **tools** returned 2,000 characters"])
    assert out.count('class="tl-item"') == 2
    assert ">psychology<" in out and ">build<" in out
    assert '<span class="tl-time">1.2s</span>' in out
    assert "· 1.2s" not in out


# ---------------- Deep Research tracker ----------------

def test_research_progress_follows_the_graph():
    p = c.ResearchProgress()
    assert "Planning" in p.status_text()
    p.update("planner", {"plan": ["q1", "q2", "q3"]})
    p.pause()
    assert p.waiting and "approve" in p.status_text()
    assert 'class="rp-step wait"' in p.html() and 'class="rp-step done"' in p.html()

    resumed = c.ResearchProgress(total=3, resumed=True)
    resumed.update("researcher", {"findings": [{"query": "q1"}]})
    assert "1 of 3" in resumed.status_text() and "Research 1/3" in resumed.html()
    resumed.update("researcher", {"findings": [{"query": "q2"}]})
    resumed.update("researcher", {"findings": [{"query": "q3"}]})
    assert resumed.active == "writer"
    resumed.update("writer", {"draft": "..."})
    resumed.update("critic", {"critique": "- fix the intro"})
    assert resumed.active == "writer"                 # sent back for a revision
    resumed.update("writer", {"draft": "..."})
    resumed.update("critic", {"critique": "APPROVED"})
    resumed.update("finalize", {})
    assert resumed.finished and resumed.status_text() == "Report ready"
    assert resumed.html().count('class="rp-step done"') == len(c.ResearchProgress.STAGES)


# ---------------- report header ----------------

def test_report_outline_and_header():
    md = "# UPI report\n\n## Summary\nUPI grew fast. " + "word " * 400 + "\n\n## **Adoption**\nMore.\n### Details\n[x](https://a.com/very/long)"
    outline = c.report_outline(md)
    assert [t for _, t in outline["headings"]] == ["UPI report", "Summary", "Adoption", "Details"]
    assert outline["minutes"] == 2 and outline["words"] > 400
    head = c.report_header_html(md, sources=5)
    assert "min read" in head and "5 sources" in head
    assert '<span class="toc-chip">Summary</span>' in head and "UPI report</span>" not in head   # title skipped


# ---------------- modes ----------------

def test_every_mode_has_capability_pills():
    for usecase in NAV_ORDER:
        caps = MODES[usecase]["caps"]
        assert 2 <= len(caps) <= 4 and all(icon and text for icon, text in caps)
