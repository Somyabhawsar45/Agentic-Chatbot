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


def test_source_pills_dedupe_icons_escape_and_drop_unsafe_links():
    results = [
        {"title": 'A "quoted" <b>title</b>', "url": "https://www.example.com/a"},
        {"title": "dup", "url": "https://www.example.com/a"},
        {"title": "evil", "url": "javascript:alert(1)"},
        {"title": "B", "url": "https://news.test/b"},
    ]
    html_out = c.source_pills_html(results)
    assert html_out.count('class="src-pill"') == 2
    assert '<span class="src-count">2 sources</span>' in html_out
    assert html_out.count('class="fav"') == 4                 # 2 in the stack + 1 per pill
    assert "domain=example.com&amp;sz=64" in html_out and ">E<img" in html_out   # icon over a letter badge
    assert "</span>example.com</a>" in html_out and "</span>news.test</a>" in html_out
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
    assert p.html().count("Researcher") == 3 and "waiting for the plan" in p.html()   # placeholders
    p.update("planner", {"plan": ["q1", "q2", "q3"]})
    p.pause()
    assert p.waiting and "approve" in p.status_text()
    out = p.html()
    assert "waiting for your OK" in out and out.count('class="am-node wait"') == 4   # planner + 3 queued

    resumed = c.ResearchProgress(total=3, resumed=True, plan=["q1", "q2 <b>", "q3"])
    resumed.update("researcher", {"findings": [{"query": "q2 <b>"}]})
    out = resumed.html()
    assert "1 of 3" in resumed.status_text()
    assert out.count('class="am-node done"') == 2                     # the planner + researcher 2
    assert out.count('class="am-node active"') == 2                    # researchers 1 and 3 still working
    assert "q2 &lt;b&gt;" in out and "<b>" not in out                  # questions are escaped
    assert 'am-edge on flow' in out                                    # planner -> researchers is flowing
    resumed.update("researcher", {"findings": [{"query": "q1"}]})
    resumed.update("researcher", {"findings": [{"query": "q3"}]})
    assert resumed.active == "writer"
    resumed.update("writer", {"draft": "..."})
    resumed.update("critic", {"critique": "- fix the intro"})
    assert resumed.active == "writer" and "revision 1" in resumed.html()   # sent back for a revision
    resumed.update("writer", {"draft": "..."})
    resumed.update("critic", {"critique": "APPROVED"})
    resumed.update("finalize", {})
    assert resumed.finished and resumed.status_text() == "Report ready"
    assert resumed.html().count('class="am-node done"') == 1 + 3 + 3   # planner, 3 researchers, writer/critic/report


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


def test_leaked_tool_call_markup_is_removed():
    leaked = ("Revenue grew 18% (p. 2).\n\nSource: report【assistant to=tavily_search<|channel|>commentary "
              '<|constrain|>json<|message|>{"query":"x"}')
    assert c.clean_markdown(leaked) == "Revenue grew 18% (p. 2).\n\nSource: report"
    assert c.strip_leaked_tool_calls("ok <|end|>") == "ok"
    assert c.clean_markdown("Use `to=` in code") == "Use `to=` in code"   # normal text untouched


def test_copy_button_embeds_text_safely():
    out = c.copy_button_html('Report with </script><script>alert(1)</script> and "quotes"', "7-3")
    assert 'id="cp-7-3"' in out and "navigator.clipboard.writeText" in out
    assert out.count("</script>") == 1                     # only the button's own closing tag
    assert r"<\/script>" in out                            # the answer's tag is neutralised
    assert c.copy_button_html("x", 'bad"id<>').count('id="cp-badid"') == 1
    assert ">Copy link<" in c.copy_button_html("https://x", "l", "Copy link")


def test_model_citation_markers_are_removed():
    assert c.clean_markdown("Python 3.15 is out 【7b2fcb-00】. See【4†source】 docs.") == "Python 3.15 is out. See docs."


def test_link_citations_become_small_clickable_sources():
    text = "UPI launched in 2016【https://www.npci.org.in/what-we-do/upi/product-overview】. Grew fast【javascript:alert(1)】."
    assert c.clean_markdown(text) == ("UPI launched in 2016 ([npci.org.in](https://www.npci.org.in/what-we-do/upi/product-overview)). "
                                      "Grew fast.")


def test_cited_pages_are_read_from_the_answer():
    assert c.cited_pages("Revenue was INR 4,820 crore (p. 2).") == {2}
    assert c.cited_pages("See pp. 3–5 and page 9, also p.12") == {3, 4, 5, 9, 12}
    assert c.cited_pages("pages 4 and 6") == {4, 6}
    assert c.cited_pages("The app. 2 and step 3 are fine") == set()     # not page references
    assert c.cited_pages("") == set()


def test_cited_page_chips_come_first_and_the_rest_are_quieter():
    cites = [{"page": p, "text": f"passage {p}", "source": "r.pdf"} for p in (1, 2, 4, 6)]
    out = c.citation_chips_html(cites, "Revenue grew 18% (p. 2) and margins improved (p. 6).")
    first_also = out.index("Also checked")
    assert out.index("p. 2") < out.index("p. 6") < first_also < out.index("p. 1") < out.index("p. 4")
    assert out.count('class="cite-chip also"') == 2
    # no page named in the answer: every chip shows normally, as before
    plain = c.citation_chips_html(cites, "No page mentioned.")
    assert "Also checked" not in plain and plain.count('class="cite-chip"') == 4
