"""The daemon imports the optional ML runtime only when constructing its app."""

from __future__ import annotations

import builtins
import sys

import pytest


def test_missing_ml_runtime_is_reported_at_app_creation(monkeypatch) -> None:
    from airunner_services.daemon import AIRunnerDaemon

    monkeypatch.delitem(sys.modules, "airunner_services.app", raising=False)
    real_import = builtins.__import__

    def reject_app(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "airunner_services.app":
            raise ModuleNotFoundError("No module named 'torch'", name="torch")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", reject_app)
    with pytest.raises(ModuleNotFoundError) as excinfo:
        AIRunnerDaemon._create_headless_app(None)

    error = excinfo.value
    assert error.__cause__ is not None
    assert error.__cause__.name == "torch"
    assert "optional ML runtime" in str(error)
    assert "--generate-config" in str(error)


def test_unrelated_import_error_propagates_unchanged(monkeypatch) -> None:
    from airunner_services.daemon import AIRunnerDaemon

    monkeypatch.delitem(sys.modules, "airunner_services.app", raising=False)
    original = ModuleNotFoundError("No module named 'pygments'", name="pygments")
    real_import = builtins.__import__

    def reject_pygments(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "airunner_services.app":
            raise original
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", reject_pygments)
    with pytest.raises(ModuleNotFoundError) as excinfo:
        AIRunnerDaemon._create_headless_app(None)

    assert excinfo.value is original
