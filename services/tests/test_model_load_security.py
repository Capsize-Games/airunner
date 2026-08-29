"""Unit tests for model-loading security fixes (GitHub issue #2031).

Covers:
- ``torch.load(..., weights_only=True)`` usage at every checkpoint load site.
- ``trust_remote_code`` disabled by default across services, with the
  tokenizer mixin gated on an explicit ``ApplicationSettings.trust_remote_code``
  opt-in (issue #2031 / #2032 CI coverage).
- g2p cache files are never loaded via raw ``pickle.load``; a restricted
  unpickler rejects malicious payloads and falls back to regeneration.

CI note (issue #2054 / security-coverage): the source-scan and pure-Python
assertions below run in the lean ``[development]`` install used by
``Hybrid Runtime CI``. Only the genuinely torch-dependent assertions are
guarded by a scoped ``importorskip`` (see ``_TorchOnlyTests``).
"""

from __future__ import annotations

import builtins
import importlib.util
import os
import pickle
import sys
from types import ModuleType
from unittest import mock

import pytest

from airunner_services.database.models.application_settings import (
    ApplicationSettings,
)


# ---------------------------------------------------------------------------
# Source-scan helpers (no heavy dependencies)
# ---------------------------------------------------------------------------


def _services_root() -> str:
    """Return the services source root (workspace/services/src)."""
    workspace = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    return os.path.join(workspace, "services", "src")


def _read_source(relative_path: str) -> str:
    """Read one services source file."""
    full_path = os.path.join(_services_root(), relative_path)
    with open(full_path, encoding="utf-8") as handle:
        return handle.read()


def _write_pickle(path: str, obj) -> None:
    with open(path, "wb") as handle:
        pickle.dump(obj, handle)


class _Malicious:
    """Object whose unpickle would execute arbitrary code."""

    def __reduce__(self):
        return (builtins.eval, ("__import__('os').getcwd()",))


def _load_language_base_pure() -> ModuleType:
    """Import ``language_base`` without importing the torch-dependent melo API.

    The ``_SafeG2PUnpickler`` class is pure Python (``pickle.Unpickler``
    subclass); importing the whole ``melo.api`` chain pulls in torch. We load
    the module directly via ``importlib`` with the torch-dependent
    ``runtime_support`` dependency satisfied by a lightweight stub so the
    lean CI install can still exercise the restricted unpickler.
    """
    module_path = os.path.join(
        _services_root(),
        "airunner_services",
        "vendor",
        "melo",
        "text",
        "language_base.py",
    )
    runtime_support = ModuleType("airunner_services.vendor.melo.runtime_support")
    runtime_support.get_melo_logger = lambda *a, **k: None
    runtime_support.resolve_tts_model_path = lambda *a, **k: ""
    sys.modules[
        "airunner_services.vendor.melo.runtime_support"
    ] = runtime_support

    # The vendor module imports torch/transformers at module level but the
    # restricted unpickler we test is pure Python; stub the heavy imports so
    # the lean CI install can still exercise it. ``airunner_common.settings``
    # is left real (it imports cleanly and other modules rely on it).
    sys.modules.setdefault("torch", ModuleType("torch"))
    sys.modules.setdefault("transformers", ModuleType("transformers"))
    transformers_stub = sys.modules["transformers"]
    transformers_stub.AutoTokenizer = object
    transformers_stub.AutoModelForMaskedLM = object

    spec = importlib.util.spec_from_file_location(
        "airunner_services.vendor.melo.text.language_base",
        module_path,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


_language_base_pure = _load_language_base_pure()
_load_g2p_cache_safe = _language_base_pure._load_g2p_cache_safe


# ---------------------------------------------------------------------------
# Restricted unpickler (pure Python; runs in the lean install)
# ---------------------------------------------------------------------------


def test_safe_g2p_cache_accepts_plain_dict(tmp_path) -> None:
    cache = str(tmp_path / "cmudict_cache.pickle")
    _write_pickle(
        cache,
        {"hello": [["HH", "AH0", "L", "OW1"]]},
    )
    assert _load_g2p_cache_safe(cache) == {
        "hello": [["HH", "AH0", "L", "OW1"]]
    }


def test_safe_g2p_cache_rejects_malicious_object(tmp_path) -> None:
    cache = str(tmp_path / "cmudict_cache.pickle")
    _write_pickle(cache, _Malicious())
    assert _load_g2p_cache_safe(cache) is None


def test_safe_g2p_cache_rejects_non_dict(tmp_path) -> None:
    cache = str(tmp_path / "cmudict_cache.pickle")
    _write_pickle(cache, ["not", "a", "dict"])
    assert _load_g2p_cache_safe(cache) is None


def test_safe_g2p_cache_rejects_corrupt_file(tmp_path) -> None:
    cache = str(tmp_path / "cmudict_cache.pickle")
    with open(cache, "wb") as handle:
        handle.write(b"\x00\x01garbage not a pickle")
    assert _load_g2p_cache_safe(cache) is None


def test_no_bare_pickle_load_in_language_base() -> None:
    """The g2p cache must never be loaded via raw pickle.load."""
    source = _read_source(
        "airunner_services/vendor/melo/text/language_base.py"
    )
    assert "pickle.load(" not in source


# ---------------------------------------------------------------------------
# Source-scan: trust_remote_code is gated by an explicit opt-in
# ---------------------------------------------------------------------------


def test_trust_remote_code_disabled_by_default() -> None:
    """The core LLM/art model loaders must not enable remote code by default."""
    files = [
        "airunner_services/llm/managers/mixins/model_loader_mixin.py",
        "airunner_services/llm/quantization_mixin.py",
        (
            "airunner_services/art/managers/zimage/native/"
            "zimage_text_encoder_loader_helper.py"
        ),
        (
            "airunner_services/art/managers/zimage/native/"
            "zimage_tokenizer.py"
        ),
    ]
    for relative_path in files:
        source = _read_source(relative_path)
        # Bare occurrences (no justification comment on a preceding line)
        # must not exist. Every remaining trust_remote_code=True must be
        # preceded by a line containing 'trust_remote_code' in a comment.
        lines = source.splitlines()
        for index, line in enumerate(lines, start=1):
            code = line.split("#", 1)[0]
            if "trust_remote_code=True" not in code:
                continue
            # Look back up to 6 lines for a justification comment.
            justified = False
            for prior in lines[max(0, index - 7): index]:
                stripped = prior.strip()
                if stripped.startswith("#") and "trust_remote_code" in stripped:
                    justified = True
                    break
            assert justified, (
                f"bare trust_remote_code=True in {relative_path}:{index}"
            )


def _load_tokenizer_mixin() -> ModuleType:
    """Import the tokenizer mixin module in isolation (lean CI safe).

    The ``airunner_services.llm.managers.mixins`` package ``__init__`` pulls
    in langchain-core-dependent modules, so the module is loaded directly via
    ``importlib`` with the ``transformers`` import stubbed out.
    """
    module_path = os.path.join(
        _services_root(),
        "airunner_services",
        "llm",
        "managers",
        "mixins",
        "tokenizer_loader_mixin.py",
    )
    transformers_stub = ModuleType("transformers")
    transformers_stub.AutoTokenizer = object
    transformers_stub.AutoConfig = object
    sys.modules["transformers"] = transformers_stub

    spec = importlib.util.spec_from_file_location(
        "tokenizer_loader_mixin_under_test",
        module_path,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def test_tokenizer_mixin_has_no_unconditional_remote_code() -> None:
    """Every trust_remote_code=True in the tokenizer mixin must be guarded by
    ``_remote_code_allowed()`` (fail-closed opt-in, issue #2031)."""
    import ast

    source = _read_source(
        "airunner_services/llm/managers/mixins/tokenizer_loader_mixin.py"
    )
    tree = ast.parse(source)
    assert "_remote_code_allowed" in source

    def enclosing_function(node: ast.AST) -> ast.FunctionDef | None:
        for fn in ast.walk(tree):
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end = fn.end_lineno or fn.lineno
                if fn.lineno <= node.lineno <= end and fn != node:
                    return fn
        return None

    found = 0
    for call in ast.walk(tree):
        if not isinstance(call, ast.Call):
            continue
        for kw in call.keywords:
            if (
                kw.arg == "trust_remote_code"
                and isinstance(kw.value, ast.Constant)
                and kw.value.value is True
            ):
                found += 1
                fn = enclosing_function(call)
                assert fn is not None, (
                    f"trust_remote_code=True at line {call.lineno} is outside "
                    "any function"
                )
                fn_source = ast.get_source_segment(source, fn) or ""
                assert "_remote_code_allowed()" in fn_source, (
                    f"trust_remote_code=True at line {call.lineno} in "
                    f"{fn.name} is not guarded by _remote_code_allowed()"
                )
    assert found == 3, f"expected 3 gated call sites, found {found}"


def test_remote_code_allowed_false_by_default() -> None:
    """With no settings row / no opt-in, remote code must never be allowed."""
    _remote_code_allowed = _load_tokenizer_mixin()._remote_code_allowed

    # No settings row (objects.first returns None, get_or_create raises).
    with mock.patch.object(
        ApplicationSettings, "objects"
    ) as fake_objects:
        fake_objects.first.return_value = None
        fake_objects.get_or_create.side_effect = RuntimeError("no db")
        assert _remote_code_allowed() is False

    # Explicit False row.
    with mock.patch.object(
        ApplicationSettings, "objects"
    ) as fake_objects:
        fake_objects.first.return_value = mock.Mock(
            trust_remote_code=False
        )
        assert _remote_code_allowed() is False

    # Explicit True row.
    with mock.patch.object(
        ApplicationSettings, "objects"
    ) as fake_objects:
        fake_objects.first.return_value = mock.Mock(
            trust_remote_code=True
        )
        assert _remote_code_allowed() is True


def test_load_model_config_passes_false_first() -> None:
    """``_load_model_config`` must attempt trust_remote_code=False first and
    never pass True when the opt-in flag is False (issue #2031)."""
    mixin_module = _load_tokenizer_mixin()
    TokenizerLoaderMixin = mixin_module.TokenizerLoaderMixin
    _load_model_config = TokenizerLoaderMixin._load_model_config
    patch_target = mixin_module.__name__

    manager = mock.Mock()
    manager.model_path = "/models/example"
    manager._apply_context_settings = mock.Mock()

    with mock.patch(f"{patch_target}.AutoConfig") as auto_config:
        with mock.patch(
            f"{patch_target}._remote_code_allowed",
            return_value=False,
        ) as allowed_spy:
            auto_config.from_pretrained.side_effect = RuntimeError(
                "needs remote code"
            )
            with pytest.raises(RuntimeError):
                _load_model_config(manager)

    assert auto_config.from_pretrained.call_count == 1
    _, kwargs = auto_config.from_pretrained.call_args
    assert kwargs["trust_remote_code"] is False
    allowed_spy.assert_called_once()


def test_load_model_config_retries_true_only_when_opted_in() -> None:
    """With the opt-in enabled, a failed False attempt retries with True."""
    mixin_module = _load_tokenizer_mixin()
    TokenizerLoaderMixin = mixin_module.TokenizerLoaderMixin
    _load_model_config = TokenizerLoaderMixin._load_model_config
    patch_target = mixin_module.__name__

    manager = mock.Mock()
    manager.model_path = "/models/example"
    manager._apply_context_settings = mock.Mock()

    with mock.patch(f"{patch_target}.AutoConfig") as auto_config:
        with mock.patch(
            f"{patch_target}._remote_code_allowed",
            return_value=True,
        ):
            auto_config.from_pretrained.side_effect = [
                RuntimeError("needs remote code"),
                mock.Mock(),
            ]
            _load_model_config(manager)

    calls = [call[1] for call in auto_config.from_pretrained.call_args_list]
    assert calls[0]["trust_remote_code"] is False
    assert calls[1]["trust_remote_code"] is True


def test_tokenizer_fallback_methods_raise_without_opt_in() -> None:
    """The fallback loaders must raise instead of calling from_pretrained
    with trust_remote_code=True when the opt-in flag is False (issue #2031)."""
    mixin_module = _load_tokenizer_mixin()
    TokenizerLoaderMixin = mixin_module.TokenizerLoaderMixin
    patch_target = mixin_module.__name__

    manager = mock.Mock(spec=TokenizerLoaderMixin)
    manager.model_path = "/models/example"
    manager.logger = mock.Mock()

    for method_name in (
        "_load_tokenizer_with_trust_remote_code",
        "_load_slow_tokenizer",
    ):
        with mock.patch(f"{patch_target}.AutoTokenizer") as auto_tokenizer:
            with mock.patch(
                f"{patch_target}._remote_code_allowed",
                return_value=False,
            ):
                method = getattr(TokenizerLoaderMixin, method_name)
                with pytest.raises(RuntimeError, match="Trust remote code"):
                    method(manager)
        auto_tokenizer.from_pretrained.assert_not_called()


def test_tokenizer_fallback_methods_run_when_opted_in() -> None:
    """With the opt-in enabled the fallback loaders proceed normally."""
    mixin_module = _load_tokenizer_mixin()
    TokenizerLoaderMixin = mixin_module.TokenizerLoaderMixin
    patch_target = mixin_module.__name__

    manager = mock.Mock(spec=TokenizerLoaderMixin)
    manager.model_path = "/models/example"
    manager.logger = mock.Mock()

    with mock.patch(f"{patch_target}.AutoTokenizer") as auto_tokenizer:
        with mock.patch(
            f"{patch_target}._remote_code_allowed",
            return_value=True,
        ):
            auto_tokenizer.from_pretrained.return_value = mock.Mock()
            TokenizerLoaderMixin._load_tokenizer_with_trust_remote_code(
                manager
            )
            TokenizerLoaderMixin._load_slow_tokenizer(manager)

    kwargs_list = [
        call[1]
        for call in auto_tokenizer.from_pretrained.call_args_list
    ]
    assert all(kwargs["trust_remote_code"] is True for kwargs in kwargs_list)


# ---------------------------------------------------------------------------
# Torch-dependent source scans (only run when torch is installed)
# ---------------------------------------------------------------------------


_TORCH_LOAD_FILES = [
    "airunner_services/vendor/melo/api.py",
    "airunner_services/vendor/openvoice/api.py",
    "airunner_services/vendor/openvoice/se_extractor.py",
    "airunner_services/runtimes/openvoice_model_manager.py",
    "airunner_services/vendor/melo/data_utils.py",
]


class TestTorchOnlySourceScans:
    """Assertions that require torch (skipped in the lean CI install)."""

    def test_all_torch_load_calls_use_weights_only(self) -> None:
        """Every torch.load call site passes weights_only=True."""
        pytest.importorskip("torch")
        services_root = _services_root()
        for relative_path in _TORCH_LOAD_FILES:
            full_path = os.path.join(services_root, relative_path)
            with open(full_path, encoding="utf-8") as handle:
                source = handle.read()
            # Strip comments so a mention in prose does not count as a call.
            code_lines = [
                line.split("#", 1)[0]
                for line in source.splitlines()
            ]
            for line_number, code in enumerate(code_lines, start=1):
                if "torch.load(" not in code:
                    continue
                # Find the call block and ensure weights_only=True appears
                # within the same statement (multi-line calls included).
                block_lines = []
                depth = 0
                started = False
                for index in range(line_number - 1, len(code_lines)):
                    candidate = code_lines[index]
                    block_lines.append(candidate)
                    depth += candidate.count("(") - candidate.count(")")
                    if not started:
                        started = True
                        if depth <= 0:
                            break
                    elif depth <= 0:
                        break
                joined = "\n".join(block_lines)
                assert "weights_only=True" in joined, (
                    f"torch.load in {relative_path}:{line_number} "
                    "missing weights_only=True"
                )
