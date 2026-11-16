"""
Create a demo PDF to try the server with (the fictional 'Meridian Payments' annual report
used by the evaluation harness).

    python -m mcp_server.make_sample                # -> ~/netra-docs/meridian_report.pdf
    python -m mcp_server.make_sample --docs-dir D   # -> D/meridian_report.pdf
"""
import argparse
from pathlib import Path

from evals.runner import load_pages
from mcp_server.simple_pdf import write_pdf
from mcp_server.store import default_docs_dir


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--docs-dir", help="where to write it (default: $NETRA_DOCS_DIR or ~/netra-docs)")
    args = parser.parse_args(argv)
    target = (Path(args.docs_dir) if args.docs_dir else default_docs_dir()) / "meridian_report.pdf"
    write_pdf(target, load_pages())
    print(f"Wrote {target.name} to {target.parent}")


if __name__ == "__main__":
    main()
