"""Regression test for issue #2190.

The vendored MeloTTS/OpenVoice fork under
services/src/airunner_services/vendor previously imported the
application's enums, settings, database models, logger and memory
helper directly. A vendored third-party library should depend on
nothing from this project, so its own repository extraction (a later
phase of #2185) is possible and so upstream diffs stay readable.
"""

from __future__ import annotations

import re
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_VENDOR_ROOT = (
    _PROJECT_ROOT
    / "services"
    / "src"
    / "airunner_services"
    / "vendor"
)

_APP_IMPORT_PATTERN = re.compile(
    r"^\s*(?:from|import)\s+"
    r"(airunner\.|airunner_common\.|airunner_services\.(?!vendor\.))",
    re.MULTILINE,
)


def test_vendor_tree_imports_nothing_from_this_project():
    offenders = []
    for path in _VENDOR_ROOT.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text()
        match = _APP_IMPORT_PATTERN.search(text)
        if match:
            offenders.append((str(path), match.group(0).strip()))
    assert offenders == []


def test_melo_and_openvoice_language_enums_match_the_app_enum():
    """The vendor fork's own Language enum must stay a same-valued copy.

    airunner_common.contract_enums.AvailableLanguage duck-types across
    this boundary (see _normalize_language in melo/api.py), which only
    works while the members and values agree.
    """
    import sys

    sys.path[:0] = [
        str(_PROJECT_ROOT / "services" / "src"),
        str(_PROJECT_ROOT / "shared"),
    ]
    from airunner_common.contract_enums import AvailableLanguage
    from airunner_services.vendor.melo.language import Language as Melo
    from airunner_services.vendor.openvoice.language import (
        Language as OpenVoice,
    )

    app_members = {m.name: m.value for m in AvailableLanguage}
    for vendor_enum in (Melo, OpenVoice):
        vendor_members = {m.name: m.value for m in vendor_enum}
        assert vendor_members == app_members, vendor_enum


def _load_runtime_support_fresh():
    """Load runtime_support.py directly from its file path.

    test_model_load_security.py replaces
    sys.modules["...vendor.melo.runtime_support"] with a minimal stub
    (to test language_base.py's pure-Python unpickler without pulling
    in torch) and never restores it, so a plain `import` here can
    silently pick up that stub depending on test collection order.
    Loading straight from the file sidesteps sys.modules entirely.
    """
    import importlib.util

    module_path = (
        _VENDOR_ROOT / "melo" / "runtime_support.py"
    )
    spec = importlib.util.spec_from_file_location(
        "airunner_services.vendor.melo.runtime_support_under_test",
        module_path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_resolve_tts_model_root_priority_chain(monkeypatch):
    import sys

    sys.path[:0] = [
        str(_PROJECT_ROOT / "services" / "src"),
        str(_PROJECT_ROOT / "shared"),
    ]
    rs = _load_runtime_support_fresh()

    monkeypatch.delenv("AIRUNNER_TTS_MODEL_PATH", raising=False)
    rs.set_tts_model_root_resolver(lambda: None)
    rs.set_tts_model_base_resolver(lambda: None)
    rs.set_cache_base_resolver(lambda: None)

    # No resolver returns a value -> the vendor's own default.
    assert rs.resolve_tts_model_root() == rs._default_tts_model_root()

    # Base resolver provides the default "text/models/tts" root.
    rs.set_tts_model_base_resolver(lambda: "/tmp/base")
    assert (
        rs.resolve_tts_model_root() == "/tmp/base/text/models/tts"
    )

    # An explicit override resolver takes priority over the base one.
    rs.set_tts_model_root_resolver(lambda: "/tmp/override/openvoice")
    assert rs.resolve_tts_model_root() == "/tmp/override"

    # The environment variable takes priority over every resolver.
    monkeypatch.setenv("AIRUNNER_TTS_MODEL_PATH", "/tmp/env")
    assert rs.resolve_tts_model_root() == "/tmp/env"
