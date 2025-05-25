import os
import tempfile
import pytest
from unittest.mock import MagicMock

# Patch show_path before importing PathManager
import sys
from types import ModuleType

called = {}


def fake_show_path(path):
    called["path"] = path


# Patch the show_path function in sys.modules so that when PathManager is imported, it uses the fake
show_path_mod = ModuleType("airunner.handlers.llm.agent.actions.show_path")
show_path_mod.show_path = fake_show_path
sys.modules["airunner.handlers.llm.agent.actions.show_path"] = show_path_mod

from airunner.gui.windows.main.path_manager import PathManager


class DummyPathSettings:
    pdf_path = tempfile.gettempdir()
    webpages_path = tempfile.gettempdir()
    base_path = tempfile.gettempdir()

    def __getattr__(self, name):
        return tempfile.gettempdir()


def test_show_settings_path():
    global called
    called = {}
    pm = PathManager(DummyPathSettings())
    pm.show_settings_path("base_path")
    assert "path" in called


def test_download_url_and_pdf(tmp_path):
    pm = PathManager(DummyPathSettings())
    # Use a local file as a fake URL response
    html = "<html><title>Test Title</title><body>Content</body></html>"
    pdf_content = b"%PDF-1.4 test pdf"

    # Patch requests.get
    class DummyResponse:
        def __init__(self, content):
            self.content = content

    def fake_get(url):
        if url.endswith(".pdf"):
            return DummyResponse(pdf_content)
        return DummyResponse(html.encode())

    import airunner.gui.windows.main.path_manager as pm_mod

    pm_mod.requests.get = fake_get
    pm_mod.BeautifulSoup = lambda content, _: type(
        "Soup", (), {"title": type("Title", (), {"string": "Test Title"})}
    )()
    # Test download_url
    filename = pm.download_url("http://example.com", str(tmp_path))
    assert os.path.exists(os.path.join(tmp_path, filename))
    # Test download_pdf
    filename = pm.download_pdf("http://example.com/test.pdf", str(tmp_path))
    assert os.path.exists(os.path.join(tmp_path, filename))


def test_on_navigate_to_url(monkeypatch):
    pm = PathManager(DummyPathSettings())
    dummy_main_window = MagicMock()
    dummy_main_window.update_chatbot = MagicMock()
    dummy_main_window.api = MagicMock()
    dummy_main_window.chatbot = MagicMock(target_files=["file"])
    # Patch QInputDialog.getText to simulate user input
    monkeypatch.setattr(
        "PySide6.QtWidgets.QInputDialog.getText",
        lambda *a, **kw: ("http://example.com", True),
    )
    # Patch download_url and download_pdf
    pm.download_url = lambda url, path: "file.html"
    pm.download_pdf = lambda url, path: "file.pdf"
    pm.on_navigate_to_url(dummy_main_window)
    assert dummy_main_window.update_chatbot.called
    assert dummy_main_window.api.llm.reload_rag.called
    assert dummy_main_window.api.llm.send_request.called
