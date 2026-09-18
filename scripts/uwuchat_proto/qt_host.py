"""Qt host for the #2230 prototype.

Runs the loopback shim (uvicorn) in a background thread, loads it in a
QtWebEngine view, enforces loopback-only egress with a request
interceptor, drives one streamed conversation, and writes a screenshot.

Run from ``airunnerdesktop/scripts``:

    AIRUNNER_BASE_PATH=tmp/airunner-base \
      ../venv/bin/python -m uwuchat_proto.qt_host
"""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

import uvicorn
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWebEngineCore import (
    QWebEngineUrlRequestInfo,
    QWebEngineUrlRequestInterceptor,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication

from uwuchat_proto.shim_app import app as shim_app

LOOPBACK = {"127.0.0.1", "localhost", "::1"}
SEND_JS = "window.__prototypeSend && window.__prototypeSend();"


class LoopbackOnlyInterceptor(QWebEngineUrlRequestInterceptor):
    """Block every request whose host is not loopback (#2083 egress)."""

    def interceptRequest(self, info: QWebEngineUrlRequestInfo) -> None:
        url = info.requestUrl()
        if url.scheme() in ("http", "https", "ws", "wss"):
            if url.host() not in LOOPBACK:
                info.block(True)


def start_shim(port: int) -> None:
    """Run the shim daemon in a daemon thread."""
    config = uvicorn.Config(
        shim_app, host="127.0.0.1", port=port, log_level="warning"
    )
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()


def _mostly_blank(pixmap: QPixmap) -> bool:
    """Return True when a grab shows no real content (all near-black)."""
    image = pixmap.toImage()
    if image.isNull():
        return True
    step = max(1, image.width() // 8)
    for x in range(0, image.width(), step):
        for y in range(0, image.height(), step):
            if image.pixelColor(x, y).lightness() > 24:
                return False
    return True


def _capture(view: QWebEngineView, path: Path) -> None:
    """Save a view grab, falling back to a screen grab, and dump the log."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pixmap = view.grab()
    if _mostly_blank(pixmap):
        screen = QGuiApplication.primaryScreen()
        pixmap = screen.grabWindow(0)
    pixmap.save(str(path))
    print(f"screenshot: {path} ({pixmap.width()}x{pixmap.height()})")
    view.page().runJavaScript(
        "document.body ? document.body.innerText : ''",
        lambda text: print("--- page text ---\n" + str(text)[:2000]),
    )


def main() -> int:
    """Launch the shim, host the page, drive a stream, screenshot, exit."""
    port = int(os.environ.get("PROTO_PORT", "8765"))
    out = Path(os.environ.get("PROTO_SHOT", "tmp/uwuchat_proto.png"))
    start_shim(port)
    app = QApplication(sys.argv)
    view = QWebEngineView()
    view.page().setUrlRequestInterceptor(LoopbackOnlyInterceptor())
    view.resize(1100, 760)
    view.setWindowTitle("UwUChat prototype (stubbed)")
    view.setUrl(QUrl(f"http://127.0.0.1:{port}/"))
    view.show()
    QTimer.singleShot(2500, lambda: view.page().runJavaScript(SEND_JS))
    QTimer.singleShot(8000, lambda: _capture(view, out))
    QTimer.singleShot(9500, app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
