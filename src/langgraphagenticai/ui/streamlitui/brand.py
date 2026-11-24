"""
The Netra eye: one small, cached copy of the logo and the HTML for the "living" (blinking) eye.

The original logo.png is 1024 px / ~870 KB. Embedding it in the page on every rerun sent over a
megabyte each time anyone clicked anything, so pages now get a resized copy (a few KB), made once.
"""
import base64
import io
from functools import lru_cache
from pathlib import Path

LOGO_PATH = Path(__file__).resolve().parents[4] / "assets" / "logo.png"


@lru_cache(maxsize=8)
def logo_data_uri(px: int = 128) -> str:
    """The logo as a small PNG data URI ("" if the file is missing)."""
    if not LOGO_PATH.exists():
        return ""
    from PIL import Image
    with Image.open(LOGO_PATH) as im:
        small = im.convert("RGB").resize((px, px), Image.LANCZOS)
        buf = io.BytesIO()
        small.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


@lru_cache(maxsize=8)
def logo_image(px: int = 128):
    """A small PIL image of the logo for the browser tab icon (None if missing)."""
    if not LOGO_PATH.exists():
        return None
    from PIL import Image
    with Image.open(LOGO_PATH) as im:
        return im.convert("RGB").resize((px, px), Image.LANCZOS)


def eye_html(size: int = 28, extra_class: str = "", px: int = 128) -> str:
    """
    The blinking Netra eye: the logo with two eyelids (CSS) that close every few seconds.
    `extra_class` adds e.g. "eye-scan" for the rotating ring shown while Netra thinks.
    """
    src = logo_data_uri(px)
    if not src:
        return ""
    return (f'<span class="netra-eye {extra_class}" style="--eye:{int(size)}px">'
            f'<img src="{src}" alt="Netra" /></span>')
