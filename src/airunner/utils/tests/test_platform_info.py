"""
Unit tests for airunner.utils.application.platform_info
"""

import sys
import importlib
import pytest


def test_get_platform_name_linux(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    from airunner.utils import get_platform_name

    assert get_platform_name() == "linux"


def test_is_linux(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    from airunner.utils import is_linux

    assert is_linux() is True


def test_is_bsd(monkeypatch):
    monkeypatch.setattr(sys, "platform", "freebsd")
    import airunner.utils.application.platform_info as platinfo

    importlib.reload(platinfo)
    assert platinfo.is_bsd() is True


def test_is_darwin(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    import airunner.utils.application.platform_info as platinfo

    importlib.reload(platinfo)
    assert platinfo.is_darwin() is True


def test_is_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    import airunner.utils.application.platform_info as platinfo

    importlib.reload(platinfo)
    assert platinfo.is_windows() is True


def test_get_platform_name_unknown(monkeypatch):
    import sys

    monkeypatch.setattr(sys, "platform", "solaris")
    from airunner.utils.application.platform_info import get_platform_name

    assert get_platform_name() == "unknown"
