"""Regression test for issue #2196's install-isolation requirement.

The repo-split tracker's plan for extracting ``native/`` into its own
repository requires ``airunner_native`` to install and import with only
``airunner-common`` present (its own package, not this monolith's
``airunner`` or ``airunner_services``). ``launcher.py``'s app-specific
imports (``airunner.components...``, ``airunner.main``, the headless
server's ``main``) are already all function-scoped, so they don't run at
import time -- except one that wasn't: a module-level
``from airunner_services.utils.application.get_logger import get_logger``,
pulled in only to pick up a logger factory that's identical to
``airunner_common.get_logger``'s own. The headless entry point already
re-registers its own database-backed log-path resolver when it actually
runs (``airunner_headless.py``'s ``_configure_logging``), so nothing
observable was lost by importing the shared base implementation directly
instead.

This test spawns a subprocess with only ``native/src`` and ``shared`` on
``sys.path`` (mirroring test_no_airunner_import_cycle.py's pattern) and
imports ``airunner_native.launcher``, so it exercises real absence of
``airunner`` and ``airunner_services`` rather than a mock.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_launcher_imports_without_airunner_or_services_on_path():
    """``airunner_native.launcher`` must import with only airunner_common.

    Both ``airunner`` and ``airunner_services`` are editable-installed in
    the test environment, which inserts their ``src`` directories into
    ``sys.path`` regardless of ``PYTHONPATH`` (see
    test_no_airunner_import_cycle.py for the same gotcha) -- so this must
    strip those exact paths at runtime, not just omit them from the
    subprocess's ``PYTHONPATH``.
    """
    _desktop_src = str(_PROJECT_ROOT / "src")
    _services_src = str(_PROJECT_ROOT / "services" / "src")
    script = (
        "import sys; "
        f"sys.path[:] = [p for p in sys.path "
        f"if p not in ({_desktop_src!r}, {_services_src!r})]; "
        "import importlib; "
        "importlib.import_module('airunner_native.launcher'); "
        "import pytest as _pytest; "
        "_pytest.raises(ImportError, importlib.import_module, 'airunner'); "
        "_pytest.raises("
        "ImportError, importlib.import_module, 'airunner_services'"
        ")"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=_PROJECT_ROOT,
        env={
            "PATH": "/usr/bin:/bin",
            "PYTHONPATH": ":".join(
                [
                    str(_PROJECT_ROOT / "native" / "src"),
                    str(_PROJECT_ROOT / "shared"),
                ]
            ),
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
