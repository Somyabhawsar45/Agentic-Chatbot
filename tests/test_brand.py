"""The living Netra eye and the small cached logo."""
import base64

from src.langgraphagenticai.ui.streamlitui import brand


def test_pages_get_a_small_logo_not_the_870kb_original():
    uri = brand.logo_data_uri(128)
    assert uri.startswith("data:image/png;base64,")
    size = len(base64.b64decode(uri.split(",", 1)[1]))
    assert size < 60_000, f"logo sent to the page is {size} bytes"
    assert brand.LOGO_PATH.stat().st_size > 10 * size        # far smaller than the original file
    assert brand.logo_data_uri(128) is uri                   # made once, then cached


def test_eye_html_has_the_blinking_wrapper_and_size():
    html = brand.eye_html(28, "extra")
    assert html.startswith('<span class="netra-eye extra" style="--eye:28px">')
    assert '<img src="data:image/png;base64,' in html and 'alt="Netra"' in html


def test_tab_icon_is_small():
    icon = brand.logo_image(64)
    assert icon is not None and icon.size == (64, 64)


def test_missing_logo_degrades_gracefully(tmp_path, monkeypatch):
    monkeypatch.setattr(brand, "LOGO_PATH", tmp_path / "nope.png")
    brand.logo_data_uri.cache_clear()
    brand.logo_image.cache_clear()
    try:
        assert brand.logo_data_uri(64) == "" and brand.eye_html(28) == "" and brand.logo_image(32) is None
    finally:
        brand.logo_data_uri.cache_clear()
        brand.logo_image.cache_clear()


def test_thinking_indicator_uses_the_scanning_eye():
    from src.langgraphagenticai.ui.streamlitui.display_result import BUSY_HTML, thinking_html
    html = thinking_html()
    assert '<span class="eye-ring"><span class="netra-eye' in html and "Thinking…" in html
    assert BUSY_HTML == '<span class="netra-busy"></span>'


def test_busy_marker_is_never_drawn_together_with_visible_content():
    # the element holding .netra-busy is hidden by CSS, so anything drawn with it would vanish too
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "src/langgraphagenticai/ui/streamlitui/display_result.py").read_text(encoding="utf-8")
    assert "+ BUSY_HTML" not in src and "{BUSY_HTML}" not in src and "BUSY_HTML +" not in src
