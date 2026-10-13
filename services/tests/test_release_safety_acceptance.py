"""Release acceptance fixtures for the safety-layer composition.

Fake doubles and neutral synthetic tokens only (no model, no
network). Pins: semantic OFF by default and block-only-adds; S08
contextual closed-only-if-enabled and fail-closed when enabled;
enablement solely behind explicit flags (no latch-on); S07
selection evidence as code pins. Efficacy (E1-E3/L1-L4) stays a
pending specialist gate, NOT claimed here.
"""

from __future__ import annotations

import shutil
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from airunner_services import content_safety_gate as gate
from airunner_services.content_safety import (
    candidate_hashes,
    falconsai,
    image_verdict,
    policy_data,
    qwen_guard,
)
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
    set_evaluator,
    set_judge,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]

_SYNTHETIC = "quixoticwobble"
_NEUTRAL_TEXT = "a calm neutral landscape painting"


@pytest.fixture
def policy_dir() -> Iterator[Path]:
    """Create a scratch dir under the (gitignored) repo-local tmp/."""
    base = _REPO_ROOT / "tmp" / "content_safety_tests"
    base.mkdir(parents=True, exist_ok=True)
    created = Path(tempfile.mkdtemp(prefix="accept_", dir=base))
    yield created
    shutil.rmtree(created, ignore_errors=True)


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Clear env switches, injected doubles, policy cache, workers."""
    monkeypatch.delenv(semantic.SEMANTIC_ENV_VAR, raising=False)
    monkeypatch.delenv(semantic.CONTEXTUAL_ENV_VAR, raising=False)
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


class _CountingDouble:
    """Fake judge/evaluator returning a fixed verdict, counting calls."""

    def __init__(self, verdict: SemanticVerdict) -> None:
        self.calls = 0
        self._verdict = verdict

    def __call__(self, fields: dict) -> SemanticVerdict:
        self.calls += 1
        return self._verdict


def test_both_layers_default_off_without_calls(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    assert semantic.semantic_enabled() is False
    assert semantic.contextual_enabled() is False
    judge = _CountingDouble(SemanticVerdict.block())
    evaluator = _CountingDouble(SemanticVerdict.block())
    set_judge(judge)
    set_evaluator(evaluator)
    result = gate.evaluate_prompt_fields({"prompt": _NEUTRAL_TEXT})
    assert result.allowed is True
    assert judge.calls == 0
    assert evaluator.calls == 0


def test_semantic_only_adds_blocks(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    monkeypatch.setenv(semantic.SEMANTIC_ENV_VAR, "1")
    # An allowing judge never clears a matcher denial.
    set_judge(_CountingDouble(SemanticVerdict.allow(REASON_ALLOWED)))
    result = gate.evaluate_prompt_fields(
        {"prompt": f"please draw {_SYNTHETIC}"}
    )
    assert result.allowed is False
    assert result.reason == "prohibited_content"
    # A blocking judge adds a denial on matcher-clean traffic.
    set_judge(_CountingDouble(SemanticVerdict.block()))
    result = gate.evaluate_prompt_fields({"prompt": _NEUTRAL_TEXT})
    assert result.allowed is False
    assert result.reason == REASON_BLOCKED
    # An allowing judge on clean traffic stays allowed.
    set_judge(_CountingDouble(SemanticVerdict.allow(REASON_ALLOWED)))
    result = gate.evaluate_prompt_fields({"prompt": _NEUTRAL_TEXT})
    assert result.allowed is True
    assert result.reason == "ok"


def test_contextual_closed_only_if_enabled(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    evaluator = _CountingDouble(SemanticVerdict.block())
    set_evaluator(evaluator)
    # Registered but OFF: the gate stays open and never calls out.
    verdict = evaluate_fields_contextual({"prompt": _NEUTRAL_TEXT})
    assert verdict.allowed is True
    assert verdict.evaluated is False
    assert verdict.reason == REASON_DISABLED
    assert evaluator.calls == 0


def test_contextual_fail_closed_when_enabled(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    monkeypatch.setenv(semantic.CONTEXTUAL_ENV_VAR, "1")
    set_evaluator(None)
    set_judge(None)
    verdict = evaluate_fields_contextual({"prompt": _NEUTRAL_TEXT})
    assert verdict.allowed is False
    assert verdict.reason == REASON_UNAVAILABLE

    def _boom(fields: dict) -> SemanticVerdict:
        raise RuntimeError("evaluator failed")

    set_evaluator(_boom)
    verdict = evaluate_fields_contextual({"prompt": _NEUTRAL_TEXT})
    assert verdict.allowed is False
    assert verdict.reason == REASON_ERROR
    ambiguous = SemanticVerdict(
        evaluated=True, allowed=True, reason="custom-reason"
    )
    set_evaluator(lambda fields: ambiguous)
    verdict = evaluate_fields_contextual({"prompt": _NEUTRAL_TEXT})
    assert verdict.allowed is False
    assert verdict.reason == REASON_AMBIGUOUS
    monkeypatch.setattr(semantic, "CONTEXTUAL_TIMEOUT_SECONDS", 0.05)

    def _slow(fields: dict) -> SemanticVerdict:
        time.sleep(0.3)
        return SemanticVerdict.block()

    set_evaluator(_slow)
    verdict = evaluate_fields_contextual({"prompt": _NEUTRAL_TEXT})
    assert verdict.allowed is False
    assert verdict.reason == REASON_TIMEOUT


def test_enablement_needs_explicit_flag_without_latch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert semantic.semantic_enabled() is False
    assert semantic.contextual_enabled() is False
    monkeypatch.setenv(semantic.SEMANTIC_ENV_VAR, "1")
    monkeypatch.setenv(semantic.CONTEXTUAL_ENV_VAR, "1")
    assert semantic.semantic_enabled() is True
    assert semantic.contextual_enabled() is True
    monkeypatch.delenv(semantic.SEMANTIC_ENV_VAR)
    monkeypatch.delenv(semantic.CONTEXTUAL_ENV_VAR)
    assert semantic.semantic_enabled() is False
    assert semantic.contextual_enabled() is False


def test_s07_text_selection_evidence() -> None:
    assert qwen_guard.MODEL_ID == "Qwen/Qwen3Guard-Gen-0.6B"
    assert qwen_guard.MODEL_REVISION is None
    assert qwen_guard.MAX_NEW_TOKENS <= 128
    # Strict default: the middle verdict denies (fail-closed seam).
    strict = qwen_guard.parse_guard_response("Safety: Controversial")
    assert strict.allowed is False
    assert strict.reason == REASON_BLOCKED
    safe = qwen_guard.parse_guard_response("Safety: Safe")
    assert safe.allowed is True
    assert safe.reason == REASON_ALLOWED
    assert qwen_guard.parse_guard_response(None).allowed is False
    assert qwen_guard.parse_guard_response("").allowed is False


def test_s07_image_selection_evidence() -> None:
    assert falconsai.MODEL_ID == "Falconsai/nsfw_image_detection"
    assert falconsai.MODEL_REVISION is None
    # Provisional operating point: floats only, calibrated by the
    # specialist at E1; uncertainty band interior withholds.
    assert isinstance(falconsai.DEFAULT_THRESHOLD, float)
    assert isinstance(falconsai.DEFAULT_BAND, float)
    assert falconsai.score_to_outcome(1.0, threshold=0.5, band=0.2) is True
    assert falconsai.score_to_outcome(0.0, threshold=0.5, band=0.2) is False
    assert falconsai.score_to_outcome(0.5, threshold=0.5, band=0.2) is None
    status = image_verdict.EVALUATOR_SELECTION_STATUS
    assert "Falconsai" in status
    assert "superseded" in status


def test_safety_budgets_and_switch_names() -> None:
    assert semantic.SEMANTIC_TIMEOUT_SECONDS == 5.0
    assert semantic.CONTEXTUAL_TIMEOUT_SECONDS == 5.0
    assert semantic.CONTEXTUAL_MAX_WORKERS == 1
    assert semantic.contextual_max_workers() == 1
    assert semantic.SEMANTIC_ENV_VAR == "AIRUNNER_CONTENT_SAFETY_SEMANTIC"
    assert semantic.CONTEXTUAL_ENV_VAR == (
        "AIRUNNER_CONTENT_SAFETY_CONTEXTUAL"
    )
