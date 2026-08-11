"""Launches the local translation dashboard and opens it in the browser.

Usage:
    python -m app.webui
"""
from __future__ import annotations

import threading
import time
import webbrowser

import uvicorn
from dotenv import load_dotenv

from app.cli.translate import configure_logging

_HOST = "127.0.0.1"
_PORT = 8420


def _open_browser_when_ready() -> None:
    time.sleep(1.0)
    webbrowser.open(f"http://{_HOST}:{_PORT}")


def main() -> None:
    load_dotenv()
    configure_logging()

    threading.Thread(target=_open_browser_when_ready, daemon=True).start()
    print(f"GNSS AI Translation Engine dashboard: http://{_HOST}:{_PORT}  (local only -- Ctrl+C to stop)")
    uvicorn.run("app.webui.server:app", host=_HOST, port=_PORT, log_level="warning")


if __name__ == "__main__":
    main()
