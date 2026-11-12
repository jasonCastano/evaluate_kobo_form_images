"""Command-line launcher: ``uv run evaluate-kobo-images [streamlit options]``."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    """Start the Streamlit app, forwarding any extra command-line arguments."""
    from streamlit.web import cli as stcli

    app = Path(__file__).with_name("app.py")
    sys.argv = ["streamlit", "run", str(app), *sys.argv[1:]]
    sys.exit(stcli.main())
