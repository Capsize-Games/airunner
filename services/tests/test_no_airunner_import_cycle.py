"""Regression test for issue #2186.

``airunner_services`` must never import ``airunner`` (the Qt desktop
distribution): the root ``setup.py`` declares
``airunner-services==VERSION`` as a dependency of ``airunner``, so a
services -> airunner import is an install-breaking cycle, not just a style
problem. The normal test environment (see ``conftest.py``) puts both
``src`` and ``services/src`` on ``sys.path`` together, which is exactly why
this class of bug previously went unnoticed: it only surfaces on a
services-only install with ``airunner`` genuinely absent.

This test spawns a subprocess with ``src`` excluded from ``sys.path`` and
imports the modules issue #2186 touched, so it exercises real absence
rather than a mock.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

# The vendored openvoice modules this used to also cover moved to their
# own repository along with the rest of airunner_services.vendor (issue
# #2195), which asserts the same no-airunner-import property itself
# (see that repository's tests/test_no_app_dependency.py).
_IMPORTABLE_WITHOUT_AIRUNNER = [
    "airunner_services.daemon_client.resource_store",
    "airunner_services.database.models.application_settings",
]


def test_services_import_without_airunner_on_path():
    """The touched modules must import with ``airunner`` unimportable."""
    _desktop_src = str(_PROJECT_ROOT / "src")
    script = (
        "import sys; "
        f"sys.path[:] = [p for p in sys.path if p != {_desktop_src!r}]; "
        "import importlib; "
        + "; ".join(
            f"importlib.import_module({mod!r})"
            for mod in _IMPORTABLE_WITHOUT_AIRUNNER
        )
        + "; "
        "import pytest as _pytest; "
        "_pytest.raises(ImportError, importlib.import_module, 'airunner')"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=_PROJECT_ROOT,
        env={
            "PATH": "/usr/bin:/bin",
            "PYTHONPATH": ":".join(
                [
                    str(_PROJECT_ROOT / "services" / "src"),
                ]
            ),
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
