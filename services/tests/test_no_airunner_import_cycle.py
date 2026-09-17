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

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

# openvoice/api.py and se_extractor.py additionally require torch/librosa,
# which are not part of the "development" test profile this suite runs
# under (see issue #2184's pattern for optional-dependency exclusions), so
# they are covered separately by a static AST check below rather than a
# subprocess import.
_IMPORTABLE_WITHOUT_AIRUNNER = [
    "airunner_services.daemon_client.resource_store",
    "airunner_services.database.models.application_settings",
    "airunner_services.vendor.openvoice.utils",
]

_MODULE_PATHS_WITHOUT_TORCH_DEPS = [
    "services/src/airunner_services/vendor/openvoice/api.py",
    "services/src/airunner_services/vendor/openvoice/se_extractor.py",
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


@pytest.mark.parametrize("relative_path", _MODULE_PATHS_WITHOUT_TORCH_DEPS)
def test_vendored_openvoice_modules_have_no_airunner_import(relative_path):
    """Static check for the two modules a subprocess import can't reach.

    ``api.py`` and ``se_extractor.py`` require torch/librosa, which are not
    installed under the "development" test profile, so this asserts the
    fixed import line statically instead of executing the module.
    """
    import ast

    tree = ast.parse((_PROJECT_ROOT / relative_path).read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not (
                node.module == "airunner"
                or node.module.startswith("airunner.")
            ), f"{relative_path} imports {node.module}"
