"""Unit tests for model-loading security fixes (GitHub issue #2031).

Covers:
- ``torch.load(..., weights_only=True)`` usage at every checkpoint load site.
- ``trust_remote_code`` disabled by default across services.
- g2p cache files are never loaded via raw ``pickle.load``; a restricted
  unpickler rejects malicious payloads and falls back to regeneration.
"""

from __future__ import annotations

import builtins
import os
import pickle

import pytest

# This suite exercises the melo TTS vendor, which imports torch at module
# import time. Skip cleanly (rather than aborting collection) in torch-free
# installs so the optional runtime-smoke suites can still run (issue #2054).
pytest.importorskip("torch")

from airunner_services.vendor.melo.text.language_base import (
    _load_g2p_cache_safe,
)


def _write_pickle(path: str, obj) -> None:
    with open(path, "wb") as handle:
        pickle.dump(obj, handle)


class _Malicious:
    """Object whose unpickle would execute arbitrary code."""

    def __reduce__(self):
        return (builtins.eval, ("__import__('os').getcwd()",))


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


def _services_root() -> str:
    """Return the services source root (workspace/services/src)."""
    workspace = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    return os.path.join(workspace, "services", "src")


def test_no_bare_pickle_load_in_language_base() -> None:
    """The g2p cache must never be loaded via raw pickle.load."""
    module_path = os.path.join(
        _services_root(),
        "airunner_services",
        "vendor",
        "melo",
        "text",
        "language_base.py",
    )
    with open(module_path, encoding="utf-8") as handle:
        source = handle.read()
    assert "pickle.load(" not in source


_TORCH_LOAD_FILES = [
    "airunner_services/vendor/melo/api.py",
    "airunner_services/vendor/openvoice/api.py",
    "airunner_services/vendor/openvoice/se_extractor.py",
    "airunner_services/runtimes/openvoice_model_manager.py",
    "airunner_services/vendor/melo/data_utils.py",
]


def test_all_torch_load_calls_use_weights_only() -> None:
    """Every torch.load call site passes weights_only=True."""
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


def test_trust_remote_code_disabled_by_default() -> None:
    """The core LLM/art model loaders must not enable remote code by default."""
    services_root = _services_root()
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
        full_path = os.path.join(services_root, relative_path)
        with open(full_path, encoding="utf-8") as handle:
            source = handle.read()
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
