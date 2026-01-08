import os
import platform
import subprocess

import pytest

from airunner.components.llm.managers.fara_controller import FaraActionExecutor


def test_open_application_windows_uses_startfile(monkeypatch: pytest.MonkeyPatch):
    executor = FaraActionExecutor(use_pyautogui=False)

    monkeypatch.setattr(platform, "system", lambda: "Windows")

    startfile_calls: list[str] = []

    def fake_startfile(path: str):
        startfile_calls.append(path)

    monkeypatch.setattr(os, "startfile", fake_startfile, raising=False)

    def popen_should_not_be_called(*args, **kwargs):
        raise AssertionError("subprocess.Popen should not be used on Windows")

    monkeypatch.setattr(subprocess, "Popen", popen_should_not_be_called)

    res = executor._execute_open_application({"application": "calc.exe"})
    assert res.success is True
    assert startfile_calls == ["calc.exe"]
