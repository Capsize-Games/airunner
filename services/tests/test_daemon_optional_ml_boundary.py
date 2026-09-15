"""The daemon's optional-ML boundary must tell the truth about what is wrong.

Two distinct situations meet at the same `import airunner_services.app`:

1. The documented optional ML runtime is absent. That is expected on a base
   install and deserves feature-level guidance.
2. Something else is missing -- an undeclared dependency, a bad merge, a typo
   in an internal import. Reporting that as "install the ML extra" sends the
   user to fix the wrong thing, which is how the pygments failure stayed
   confusing in 6.1.3.

These tests pin that the two are not conflated, and that the original exception
survives in both cases.
"""

from __future__ import annotations

import builtins
import sys
import types

import pytest


def _load_daemon_module(monkeypatch: pytest.MonkeyPatch, missing: str):
    """Import daemon.py with ``missing`` unimportable.

    The ML stack is not installed in this test environment, so rather than
    uninstalling anything we make the named module raise on import and let the
    real boundary code run.
    """
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        root = name.split(".")[0]
        if root == "airunner_services" and name.endswith(".app"):
            raise ModuleNotFoundError(f"No module named {missing!r}", name=missing)
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    # daemon.py must already be importable without the ML stack; that is the
    # property the rest of this PR establishes.
    for mod in [m for m in sys.modules if m.startswith("airunner_services.daemon")]:
        sys.modules.pop(mod, None)
    import airunner_services.daemon as daemon

    return daemon


def test_absent_ml_runtime_gets_feature_guidance(monkeypatch: pytest.MonkeyPatch):
    daemon = _load_daemon_module(monkeypatch, "torch")

    with pytest.raises(ModuleNotFoundError) as excinfo:
        daemon.AIRunnerDaemon._create_headless_app(None)

    message = str(excinfo.value)
    # Behaviour, not branding: it must name the absent module, say the runtime
    # is optional, and say what still works without it.
    assert "torch" in message
    assert "optional" in message.lower()
    assert "--generate-config" in message
    # It must NOT quote an install command, because no verified one exists:
    # the ml extra pins CUDA builds that are not on PyPI and have no CPU
    # equivalent at the same pin.
    assert "pip install" not in message.replace(
        "A base `pip install airunner` deliberately omits it.", ""
    )
    # The original cause is preserved, not swallowed.
    assert isinstance(excinfo.value.__cause__, ModuleNotFoundError)
    assert excinfo.value.__cause__.name == "torch"


@pytest.mark.parametrize("missing", ["pygments", "sqlalchemy", "some_internal_mod"])
def test_unrelated_missing_module_is_not_misdiagnosed(
    monkeypatch: pytest.MonkeyPatch,
    missing: str,
):
    """A non-ML import failure must propagate unchanged.

    `pygments` is the concrete regression this PR fixes: in 6.1.3 it was an
    undeclared hard dependency, not an optional feature. If the boundary
    relabelled it, a user would go install a 5 GB ML stack to fix a 1.3 MB
    packaging bug.
    """
    daemon = _load_daemon_module(monkeypatch, missing)

    with pytest.raises(ModuleNotFoundError) as excinfo:
        daemon.AIRunnerDaemon._create_headless_app(None)

    message = str(excinfo.value)
    assert message == f"No module named {missing!r}"
    assert "optional" not in message.lower()
    assert "ml" not in message.lower().split()
    # Re-raised as-is, so nothing was wrapped.
    assert excinfo.value.__cause__ is None


def test_optional_ml_modules_matches_the_ml_extra():
    """The classifier must track what the `ml` extra actually installs."""
    import airunner_services.daemon as daemon

    assert daemon.OPTIONAL_ML_MODULES == frozenset(
        {"torch", "torchvision", "torchaudio"}
    )
