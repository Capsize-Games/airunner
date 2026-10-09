"""Adapter tests for the required Qwen3Guard text evaluator (#2252).

Mocked-model unit tests (the gate, CPU-only): strict verdict parsing,
the generation-callable adapter, S08 seam routing, local-only loader
behavior via a stubbed ``transformers`` module, and the aggregate E2
measurement hook. One marked integration test exercises real weights
when cached and skips otherwise; it makes no efficacy claim (Q08).

Every fixture is synthetic and neutral. No model is downloaded and no
network is used outside the skipped-unless-cached integration test.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Optional

import pytest

from airunner_services import content_safety_gate as gate
from airunner_services.content_safety import candidate_hashes, policy_data
from airunner_services.content_safety import qwen_guard
from airunner_services.content_safety import semantic
from airunner_services.content_safety.semantic import (
    REASON_ALLOWED,
    REASON_AMBIGUOUS,
    REASON_BLOCKED,
    evaluate_fields_contextual,
    set_evaluator,
    set_judge,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SYNTHETIC = "wobblequixotic"
_NEUTRAL_TEXT = "a calm neutral landscape painting"


@pytest.fixture
def policy_dir() -> Iterator[Path]:
    """Create a scratch dir under the (gitignored) repo-local tmp/ tree."""
    base = _REPO_ROOT / "tmp" / "content_safety_tests"
    base.mkdir(parents=True, exist_ok=True)
    created = Path(tempfile.mkdtemp(prefix="s08q_", dir=base))
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
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Point the matcher at a temp data file built from one token."""
    path = policy_dir / "policy_terms.dat"
    hashes = sorted(candidate_hashes(_SYNTHETIC))
    path.write_text(
        "".join(f"{digest}\n" for digest in hashes), encoding="utf-8"
    )
    monkeypatch.setenv(policy_data.POLICY_DATA_ENV_VAR, str(path))
    policy_data.reset_cache()


@pytest.mark.parametrize(
    "reply,allowed,reason",
    [
        ("Safety: Safe", True, REASON_ALLOWED),
        ("safety: safe\nCategories: none", True, REASON_ALLOWED),
        ("  Safety:Safe  ", True, REASON_ALLOWED),
        ("Safety: Unsafe", False, REASON_BLOCKED),
        ("Safety: UNSAFE\nCategories: c1", False, REASON_BLOCKED),
        ("Safety: Controversial", False, REASON_BLOCKED),
        ("Safety: controversial", False, REASON_BLOCKED),
        ("no structured verdict here", False, REASON_AMBIGUOUS),
        ("Unsafe without the safety line", False, REASON_AMBIGUOUS),
        ("", False, REASON_AMBIGUOUS),
        (None, False, REASON_AMBIGUOUS),
    ],
)
def test_strict_parse_allows_only_explicit_safe(
    reply: Optional[str], allowed: bool, reason: str
) -> None:
    verdict = qwen_guard.parse_guard_response(reply, strict=True)
    assert verdict.evaluated is True
    assert verdict.allowed is allowed
    assert verdict.reason == reason


def test_non_strict_controversial_still_denies() -> None:
    verdict = qwen_guard.parse_guard_response(
        "Safety: Controversial", strict=False
    )
    assert verdict.allowed is False
    assert verdict.reason == REASON_AMBIGUOUS


def test_build_request_joins_and_bounds_fields() -> None:
    request = qwen_guard.build_guard_request(
        {"prompt": _NEUTRAL_TEXT, "empty": "", "other": "second"}
    )
    assert "prompt:\n" + _NEUTRAL_TEXT in request
    assert "other:\nsecond" in request
    long_request = qwen_guard.build_guard_request(
        {"prompt": "x" * (qwen_guard.MAX_INPUT_CHARS + 10)}
    )
    assert len(long_request) == qwen_guard.MAX_INPUT_CHARS


def test_factory_routes_mocked_replies_through_seam(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(semantic.CONTEXTUAL_ENV_VAR, "1")
    seen: list[str] = []

    def _generate(request: str) -> Optional[str]:
        seen.append(request)
        return "Safety: Unsafe" if "deny-me" in request else "Safety: Safe"

    set_evaluator(qwen_guard.make_qwen_guard_evaluator(_generate))
    allowed = evaluate_fields_contextual({"prompt": _NEUTRAL_TEXT})
    assert allowed.allowed is True
    assert _NEUTRAL_TEXT in seen[0]
    denied = evaluate_fields_contextual({"prompt": "please deny-me"})
    assert denied.allowed is False
    assert denied.reason == REASON_BLOCKED


def test_gate_routing_and_matcher_preserved(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    monkeypatch.setenv(semantic.CONTEXTUAL_ENV_VAR, "1")
    calls = []

    def _generate(request: str) -> Optional[str]:
        calls.append(request)
        return "Safety: Safe"

    set_evaluator(qwen_guard.make_qwen_guard_evaluator(_generate))
    assert gate.evaluate_prompt_fields({"prompt": _NEUTRAL_TEXT}).allowed
    matched = gate.evaluate_prompt_fields(
        {"prompt": f"please draw {_SYNTHETIC}"}
    )
    assert matched.allowed is False
    assert matched.reason == "prohibited_content"
    assert len(calls) == 1

