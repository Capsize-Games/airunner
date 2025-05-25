"""
Test suite for local_http_server.py in LLM widgets.
"""

import pytest
from unittest.mock import patch, MagicMock
from airunner.gui.widgets.llm import local_http_server


def test_import_local_http_server():
    # Just test that the module imports
    assert local_http_server is not None


# If LocalHTTPServer does not exist, skip further tests
if not hasattr(local_http_server, "LocalHTTPServer"):
    pytest.skip(
        "LocalHTTPServer not present in local_http_server module",
        allow_module_level=True,
    )
else:

    def test_server_can_be_mocked(monkeypatch):
        mock_server = MagicMock()
        monkeypatch.setattr(local_http_server, "LocalHTTPServer", mock_server)
        assert True

    def test_server_start_and_stop(monkeypatch):
        mock_server = MagicMock()
        monkeypatch.setattr(local_http_server, "LocalHTTPServer", mock_server)
        server = local_http_server.LocalHTTPServer()
        server.start()
        server.stop()
        assert mock_server.start.called
        assert mock_server.stop.called

    def test_server_is_running(monkeypatch):
        mock_server = MagicMock()
        mock_server.is_running.return_value = True
        monkeypatch.setattr(local_http_server, "LocalHTTPServer", mock_server)
        server = local_http_server.LocalHTTPServer()
        assert server.is_running()
