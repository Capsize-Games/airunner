"""
Unit tests for app_installer.py to achieve 100% coverage.
"""

import os
import sys
import types
import pytest
from unittest.mock import patch, MagicMock
import signal

import airunner.app_installer as app_installer
from airunner.app_installer import AppInstaller
from unittest.mock import MagicMock, patch
import types
import sys
import pytest


def test_do_show_setup_wizard_true(monkeypatch):
    ai = AppInstaller.__new__(AppInstaller)
    # Patch application_settings property
    type(ai).application_settings = property(
        lambda self: types.SimpleNamespace(
            user_agreement_checked=True,
            stable_diffusion_agreement_checked=True,
            airunner_agreement_checked=True,
        )
    )
    # Prevent any accidental UI logic
    ai.wizard = MagicMock()
    ai.download_wizard = MagicMock()
    ai.close_on_cancel = False
    monkeypatch.setattr("sys.exit", lambda code=0: None)
    assert ai.do_show_setup_wizard is True


def test_do_show_setup_wizard_false(monkeypatch):
    ai = AppInstaller.__new__(AppInstaller)
    type(ai).application_settings = property(
        lambda self: types.SimpleNamespace(
            user_agreement_checked=False,
            stable_diffusion_agreement_checked=True,
            airunner_agreement_checked=True,
        )
    )
    ai.wizard = MagicMock()
    ai.download_wizard = MagicMock()
    ai.close_on_cancel = False
    monkeypatch.setattr("sys.exit", lambda code=0: None)
    assert ai.do_show_setup_wizard is False


def test_signal_handler_calls_quit(monkeypatch):
    monkeypatch.setattr(
        AppInstaller, "quit", lambda: (_ for _ in ()).throw(SystemExit(0))
    )
    with pytest.raises(SystemExit):
        AppInstaller.signal_handler(signal.SIGINT, None)


def test_cancel_closes(monkeypatch):
    ai = AppInstaller.__new__(AppInstaller)
    ai.wizard = MagicMock()
    ai.download_wizard = MagicMock()
    ai.close_on_cancel = True
    monkeypatch.setattr(AppInstaller, "quit", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(
        sys, "exit", lambda code=0: (_ for _ in ()).throw(SystemExit(code))
    )
    with pytest.raises(SystemExit):
        ai.cancel()
    ai.wizard.close.assert_called_once()
    ai.download_wizard.close.assert_called_once()


def test_quit_calls_app(monkeypatch):
    class DummyApp:
        def __init__(self):
            self.called = False

        def quit(self):
            self.called = True

        def processEvents(self):
            pass

    dummy_app = DummyApp()
    monkeypatch.setattr("PySide6.QtWidgets.QApplication.instance", lambda: dummy_app)
    AppInstaller.quit()
    assert dummy_app.called
