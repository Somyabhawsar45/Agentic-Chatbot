"""
Minimal PDF writer (plain Helvetica text, one string per page). Used by the tests and by
`python -m mcp_server.make_sample` so the project needs no PDF-generation dependency.
"""
import textwrap
from pathlib import Path

PAGE_W, PAGE_H = 612, 792
MARGIN, FONT_SIZE, LEADING = 54, 10, 13
WRAP_COLUMNS = 95
MAX_LINES = (PAGE_H - 2 * MARGIN) // LEADING


def _escape(line: str) -> bytes:
    data = line.encode("latin-1", errors="replace")
    return data.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _page_stream(text: str) -> bytes:
    lines = []
    for paragraph in text.splitlines() or [""]:
        lines.extend(textwrap.wrap(paragraph, WRAP_COLUMNS) or [""])
    if len(lines) > MAX_LINES:
        raise ValueError(f"page text needs {len(lines)} lines but a page fits {MAX_LINES}")
    if not any(line.strip() for line in lines):
        return b"BT ET"      # a page with no text (like a scanned page)
    body = b"\n".join(b"(" + _escape(line) + b") Tj T*" for line in lines)
    return f"BT /F1 {FONT_SIZE} Tf {MARGIN} {PAGE_H - MARGIN} Td {LEADING} TL\n".encode() + body + b"\nET"


def write_pdf(path, pages: list) -> Path:
    """Write `pages` (list of strings) as a PDF and return its path."""
    count = len(pages)
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(count))
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {count} >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    for i, text in enumerate(pages):
        stream = _page_stream(text)
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {5 + 2 * i} 0 R >>".encode())
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode() + b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(out))
    return path
