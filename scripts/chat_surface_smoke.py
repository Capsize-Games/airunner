"""Render smoke check for the desktop chat surface host (#2230, B4a).

Starts the real daemon app with the built client bundle mounted, hosts the
bundle in the app's own ``ChatSurfaceWidget`` (not a throwaway harness),
and reports what the page actually rendered plus whether the loopback
token reached the ``/api/v1/events`` WebSocket handshake.

    AIRUNNER_BASE_PATH=$PWD/tmp/airunner-base \
      AIRUNNER_CLIENT_BUNDLE=<path to the built dist> \
      DISPLAY=:0.0 venv/bin/python scripts/chat_surface_smoke.py

Writes ``tmp/desktop_chat_surface.png`` and prints the page text. Needs a
display: QtWebEngine has no supported offscreen platform plugin.
"""

from __future__ import annotations

import os
import socket
import sys
import threading
from pathlib import Path
from typing import Callable, Dict, Optional

import requests
import uvicorn
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from airunner.components.chat.gui.chat_surface_endpoint import (
    ChatSurfaceEndpoint,
)
from airunner.components.chat.gui.widgets.chat_surface_widget import (
    ChatSurfaceWidget,
)
from airunner_services.api.loopback_token import get_or_create_loopback_token
from airunner_services.api.server import create_app

REPO_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOT = REPO_ROOT / "tmp" / "desktop_chat_surface.png"
PROBE_JS = (
    "(function(){window.__probe='pending';"
    "var ws=new WebSocket('ws://'+location.host+'/api/v1/events');"
    "ws.onmessage=function(e){window.__probe="
    "'frame '+String(e.data).slice(0,50);};"
    "ws.onerror=function(){window.__probe='error';};"
    "ws.onclose=function(e){if(window.__probe==='pending')"
    "{window.__probe='closed:'+e.code;}};return 'started';})()"
)
PROBE_RESULT_JS = "window.__probe"
TEXT_JS = "document.body ? document.body.innerText : ''"


def bundle_directory() -> Path:
    """Return the built client bundle directory, or exit with a message."""
    raw = (os.environ.get("AIRUNNER_CLIENT_BUNDLE") or "").strip()
    if not raw:
        raise SystemExit(
            "AIRUNNER_CLIENT_BUNDLE must point at the built client dist"
        )
    directory = Path(raw).expanduser()
    if not (directory / "index.html").is_file():
        raise SystemExit(f"no index.html under {directory}")
    return directory


def free_port() -> int:
    """Return an unused loopback port."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def start_daemon(port: int) -> None:
    """Serve the real daemon app on loopback in a daemon thread."""
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(), host="127.0.0.1", port=port, log_level="warning"
        )
    )
    threading.Thread(target=server.run, daemon=True).start()


def wait_for_daemon(port: int, attempts: int = 80) -> bool:
    """Poll the health route until the daemon answers."""
    url = f"http://127.0.0.1:{port}/api/v1/health"
    for _ in range(attempts):
        try:
            if requests.get(url, timeout=1).status_code == 200:
                return True
        except requests.RequestException:
            pass
        threading.Event().wait(0.25)
    return False


def read(surface: ChatSurfaceWidget, script: str, sink: Callable) -> None:
    """Run one JavaScript snippet on the hosted page."""
    surface.view.page().runJavaScript(script, sink)


def _ignore(_value: object) -> None:
    """Drop one JavaScript result."""


def capture(surface: ChatSurfaceWidget) -> None:
    """Save a grab of the surface."""
    SCREENSHOT.parent.mkdir(parents=True, exist_ok=True)
    pixmap = surface.grab()
    pixmap.save(str(SCREENSHOT))
    print(f"screenshot: {SCREENSHOT} ({pixmap.width()}x{pixmap.height()})")


def main() -> int:
    """Host the built surface, report what rendered, and exit."""
    bundle_directory()
    port = free_port()
    start_daemon(port)
    if not wait_for_daemon(port):
        print("daemon did not become reachable", file=sys.stderr)
        return 2
    state: Dict[str, Optional[str]] = {"text": None, "probe": None}
    app = QApplication(sys.argv)
    surface = ChatSurfaceWidget(
        endpoint=ChatSurfaceEndpoint(
            base_url=f"http://127.0.0.1:{port}",
            token=get_or_create_loopback_token(),
        )
    )
    surface.resize(1100, 760)
    surface.load()
    surface.show()
    QTimer.singleShot(9000, lambda: read(surface, PROBE_JS, _ignore))
    QTimer.singleShot(
        14000,
        lambda: read(
            surface, PROBE_RESULT_JS, lambda v: state.update(probe=str(v))
        ),
    )
    QTimer.singleShot(
        17000,
        lambda: read(surface, TEXT_JS, lambda v: state.update(text=str(v))),
    )
    QTimer.singleShot(19000, lambda: capture(surface))
    QTimer.singleShot(20000, surface.reload)
    QTimer.singleShot(21000, app.quit)
    app.exec()
    text = state["text"] or ""
    print(f"events socket probe: {state['probe']}")
    print("--- page text ---")
    print(text[:1500])
    if not text.strip():
        print("surface rendered no text", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
