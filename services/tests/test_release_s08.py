"""Release regression tests for issue #2106 (S08).

Required offline contextual safety adapter behind allow/deny/unavailable
results: local-only, bounded, and fail-closed on timeout/error/ambiguity.
Matcher denials are preserved.

The S07 evaluator selection
(``release-planning/linux-v1/safety-evaluation.md``) is a DRAFT: the text
slot has no approved evaluator and the §4 thresholds are unapproved. These
tests cover adapter plumbing with fake doubles only -- allowed, blocked,
unavailable, timeout, and bounded worker count -- not evaluator efficacy.
Private evaluation is still a separate gate, not satisfied by this file.

Every token used here is synthetic and neutral. No model is loaded and no
network is used; the evaluator is injected through ``set_evaluator`` (or
the approved ``set_judge`` seam) and every test resets it.
"""

from __future__ import annotations

import logging
import shutil
import sys
import tempfile
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from airunner_services import content_safety_gate as gate
from airunner_services.content_safety import candidate_hashes, policy_data
from airunner_services.content_safety import semantic
from airunner_services.content_safety.semantic import (
    REASON_ALLOWED,
    REASON_AMBIGUOUS,
    REASON_BLOCKED,
    REASON_DISABLED,
    REASON_ERROR,
    REASON_TIMEOUT,
    REASON_UNAVAILABLE,
    SemanticVerdict,
    evaluate_fields_contextual,
    parse_judge_response,
    set_evaluator,
    set_judge,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]

_SYNTHETIC = "wobblequixotic"
_NEUTRAL_TEXT = "a calm neutral landscape painting"

# Modules that must never appear as a side effect of inference: remote
# providers, HTTP stacks, and model runtimes (no implicit downloads).
_FORBIDDEN_INFERENCE_MODULES = frozenset(
    {
        "aiohttp",
        "httpx",
        "requests",
        "socket",
        "ssl",
        "torch",
        "transformers",
        "urllib3",
    }
)


@pytest.fixture
def policy_dir() -> Iterator[Path]:
    """Create a scratch dir under the (gitignored) repo-local tmp/ tree."""
    base = _REPO_ROOT / "tmp" / "content_safety_tests"
    base.mkdir(parents=True, exist_ok=True)
    created = Path(tempfile.mkdtemp(prefix="s08_", dir=base))
    yield created
    shutil.rmtree(created, ignore_errors=True)


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Clear env switches, injected doubles, policy cache, and workers."""
    monkeypatch.delenv(semantic.CONTEXTUAL_ENV_VAR, raising=False)
    monkeypatch.delenv(semantic.SEMANTIC_ENV_VAR, raising=False)
    monkeypatch.delenv(policy_data.POLICY_DATA_ENV_VAR, raising=False)
    set_judge(None)
    set_evaluator(None)
    policy_data.reset_cache()
    semantic.reset_contextual_workers()
    yield
    set_judge(None)
    set_evaluator(None)
    policy_data.reset_cache()
    semantic.reset_contextual_workers()


def _load_synthetic_policy(
    policy_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    token: str = _SYNTHETIC,
) -> Path:
    """Point the matcher at a temp data file built from ``token``."""
    path = policy_dir / "policy_terms.dat"
    hashes = sorted(candidate_hashes(token))
    path.write_text(
        "".join(f"{digest}\n" for digest in hashes),
        encoding="utf-8",
    )
    monkeypatch.setenv(policy_data.POLICY_DATA_ENV_VAR, str(path))
    policy_data.reset_cache()
    return path


def _enable_contextual(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(semantic.CONTEXTUAL_ENV_VAR, "1")


class _CountingEvaluator:
    """Fake evaluator that records how many times it was called."""

    def __init__(self, verdict: SemanticVerdict) -> None:
        self.calls = 0
        self._verdict = verdict

    def __call__(self, fields: dict) -> SemanticVerdict:
        self.calls += 1
        return self._verdict


def _safety_threads() -> list[threading.Thread]:
    return [
        thread
        for thread in threading.enumerate()
        if thread.name.startswith("airunner-safety")
    ]


def test_contextual_disabled_by_default_allows(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    assert semantic.contextual_enabled() is False
    verdict = evaluate_fields_contextual({"prompt": _NEUTRAL_TEXT})
    assert verdict.allowed is True
    assert verdict.evaluated is False
    assert verdict.reason == REASON_DISABLED
    result = gate.evaluate_prompt_fields({"prompt": _NEUTRAL_TEXT})
    assert result.allowed is True


def test_enabled_allow_double_allows(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    _enable_contextual(monkeypatch)
    set_evaluator(_CountingEvaluator(SemanticVerdict.allow(REASON_ALLOWED)))
    result = gate.evaluate_prompt_fields({"prompt": _NEUTRAL_TEXT})
    assert result.allowed is True
    assert result.reason == "ok"


def test_enabled_block_double_denies_with_generic_reason(
    policy_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    _enable_contextual(monkeypatch)
    set_evaluator(_CountingEvaluator(SemanticVerdict.block()))
    with caplog.at_level(logging.DEBUG):
        result = gate.evaluate_prompt_fields({"prompt": _NEUTRAL_TEXT})
    assert result.allowed is False
    assert result.reason == REASON_BLOCKED
    assert result.field is None
    assert gate.rejection_message(result) == gate.GENERIC_REJECTION_MESSAGE
    assert all(
        _NEUTRAL_TEXT not in record.getMessage() for record in caplog.records
    )


def test_enabled_unavailable_denies_fail_closed(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    _enable_contextual(monkeypatch)
    set_evaluator(None)
    set_judge(None)
    verdict = evaluate_fields_contextual({"prompt": _NEUTRAL_TEXT})
    assert verdict.allowed is False
    assert verdict.evaluated is False
    assert verdict.reason == REASON_UNAVAILABLE
    result = gate.evaluate_prompt_fields({"prompt": _NEUTRAL_TEXT})
    assert result.allowed is False
    assert result.reason == REASON_UNAVAILABLE
    assert gate.rejection_message(result) == gate.GENERIC_REJECTION_MESSAGE


def test_enabled_error_and_unexpected_return_deny(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    _enable_contextual(monkeypatch)

    def _boom(fields: dict) -> SemanticVerdict:
        raise RuntimeError("evaluator failed")

    set_evaluator(_boom)
    verdict = evaluate_fields_contextual({"prompt": _NEUTRAL_TEXT})
    assert verdict.allowed is False
    assert verdict.reason == REASON_ERROR
    assert (
        gate.evaluate_prompt_fields({"prompt": _NEUTRAL_TEXT}).allowed is False
    )

    set_evaluator(lambda fields: "not-a-verdict")  # type: ignore[arg-type]
    verdict = evaluate_fields_contextual({"prompt": _NEUTRAL_TEXT})
    assert verdict.allowed is False
    assert verdict.reason == REASON_AMBIGUOUS


def test_enabled_ambiguous_outcome_denies(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    _enable_contextual(monkeypatch)
    ambiguous = parse_judge_response("no idea either way")
    assert ambiguous.reason == REASON_AMBIGUOUS
    set_evaluator(lambda fields: ambiguous)
    verdict = evaluate_fields_contextual({"prompt": _NEUTRAL_TEXT})
    assert verdict.allowed is False
    assert verdict.reason == REASON_AMBIGUOUS
    result = gate.evaluate_prompt_fields({"prompt": _NEUTRAL_TEXT})
    assert result.allowed is False


def test_evaluator_falls_back_to_judge_seam(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    _enable_contextual(monkeypatch)
    judge = _CountingEvaluator(SemanticVerdict.allow(REASON_ALLOWED))
    set_judge(judge)
    assert semantic.get_evaluator() is None
    result = gate.evaluate_prompt_fields({"prompt": _NEUTRAL_TEXT})
    assert result.allowed is True
    assert judge.calls == 1
    evaluator = _CountingEvaluator(SemanticVerdict.block())
    set_evaluator(evaluator)
    result = gate.evaluate_prompt_fields({"prompt": _NEUTRAL_TEXT})
    assert result.allowed is False
    assert evaluator.calls == 1
    assert judge.calls == 1


def test_hash_match_preserved_without_evaluator_call(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    _enable_contextual(monkeypatch)
    evaluator = _CountingEvaluator(SemanticVerdict.allow(REASON_ALLOWED))
    set_evaluator(evaluator)
    result = gate.evaluate_prompt_fields(
        {"prompt": f"please draw {_SYNTHETIC}"}
    )
    assert result.allowed is False
    assert result.reason == "prohibited_content"
    assert evaluator.calls == 0


def test_worker_count_is_bounded(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    _enable_contextual(monkeypatch)
    assert semantic.CONTEXTUAL_MAX_WORKERS == 1
    assert semantic.contextual_max_workers() == 1
    set_evaluator(_CountingEvaluator(SemanticVerdict.allow(REASON_ALLOWED)))
    for _ in range(3):
        verdict = evaluate_fields_contextual({"prompt": _NEUTRAL_TEXT})
        assert verdict.allowed is True
    assert len(_safety_threads()) == 1
    monkeypatch.setattr(semantic, "CONTEXTUAL_TIMEOUT_SECONDS", 0.05)

    def _slow(fields: dict) -> SemanticVerdict:
        time.sleep(0.3)
        return SemanticVerdict.block()

    set_evaluator(_slow)
    verdict = evaluate_fields_contextual({"prompt": _NEUTRAL_TEXT})
    assert verdict.allowed is False
    assert verdict.reason == REASON_TIMEOUT
    assert len(_safety_threads()) == 1


def test_enabled_timeout_denies_through_gate(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    _enable_contextual(monkeypatch)
    monkeypatch.setattr(semantic, "CONTEXTUAL_TIMEOUT_SECONDS", 0.05)

    def _slow(fields: dict) -> SemanticVerdict:
        time.sleep(0.3)
        return SemanticVerdict.block()

    set_evaluator(_slow)
    result = gate.evaluate_prompt_fields({"prompt": _NEUTRAL_TEXT})
    assert result.allowed is False
    assert result.reason == REASON_TIMEOUT


def test_inference_loads_no_remote_or_model_modules(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    _enable_contextual(monkeypatch)
    set_evaluator(_CountingEvaluator(SemanticVerdict.allow(REASON_ALLOWED)))
    before = set(sys.modules)
    gate.evaluate_prompt_fields({"prompt": _NEUTRAL_TEXT})
    set_evaluator(_CountingEvaluator(SemanticVerdict.block()))
    gate.evaluate_prompt_fields({"prompt": _NEUTRAL_TEXT})
    set_evaluator(None)
    set_judge(None)
    gate.evaluate_prompt_fields({"prompt": _NEUTRAL_TEXT})
    introduced = set(sys.modules) - before
    assert not (introduced & _FORBIDDEN_INFERENCE_MODULES)
