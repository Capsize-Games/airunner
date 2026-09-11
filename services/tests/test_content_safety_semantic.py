"""Tests for the optional semantic content-safety layer.

Every token used here is synthetic and neutral. No real policy term appears
in this file, and no assertion inspects the contents of a log record beyond
checking that it does not contain the synthetic input text.

The layer is exercised with fake judges only -- no model is loaded. The
judge is injected through ``set_judge(...)`` and every test resets it.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from airunner_services import content_safety_gate as gate
from airunner_services.content_safety import candidate_hashes, policy_data
from airunner_services.content_safety import semantic
from airunner_services.content_safety.semantic import (
    REASON_AMBIGUOUS,
    REASON_BLOCKED,
    REASON_DISABLED,
    REASON_ERROR,
    REASON_TIMEOUT,
    REASON_UNAVAILABLE,
    SemanticVerdict,
    build_judge_instruction,
    evaluate_fields_semantic,
    get_judge,
    make_llm_judge,
    parse_judge_response,
    semantic_enabled,
    set_judge,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]

# A single invented, neutral token. It is not a policy term anywhere; the
# tests hash it locally to exercise the matcher fast path.
_SYNTHETIC = "zorbblesprocket"
_NEUTRAL_TEXT = "a calm neutral landscape painting"


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


@pytest.fixture
def policy_dir() -> Iterator[Path]:
    """Create a scratch dir under the (gitignored) repo-local tmp/ tree."""
    base = _REPO_ROOT / "tmp" / "content_safety_tests"
    base.mkdir(parents=True, exist_ok=True)
    created = Path(tempfile.mkdtemp(prefix="semantic_", dir=base))
    yield created
    shutil.rmtree(created, ignore_errors=True)


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Clear env switches, the injected judge, and the policy cache."""
    monkeypatch.delenv(semantic.SEMANTIC_ENV_VAR, raising=False)
    monkeypatch.delenv(policy_data.POLICY_DATA_ENV_VAR, raising=False)
    set_judge(None)
    policy_data.reset_cache()
    yield
    set_judge(None)
    policy_data.reset_cache()


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


class _CountingJudge:
    """Fake judge that records how many times it was called."""

    def __init__(self, verdict: SemanticVerdict) -> None:
        self.calls = 0
        self._verdict = verdict

    def __call__(self, fields: dict) -> SemanticVerdict:
        self.calls += 1
        return self._verdict


# --------------------------------------------------------------------------
# Env switch
# --------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
def test_semantic_enabled_truthy(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv(semantic.SEMANTIC_ENV_VAR, value)
    assert semantic_enabled() is True


@pytest.mark.parametrize("value", ["", "0", "false", "no", "off", "maybe"])
def test_semantic_enabled_falsy(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv(semantic.SEMANTIC_ENV_VAR, value)
    assert semantic_enabled() is False


def test_semantic_disabled_by_default() -> None:
    assert semantic_enabled() is False


def test_env_var_name_is_generic() -> None:
    assert semantic.SEMANTIC_ENV_VAR == "AIRUNNER_CONTENT_SAFETY_SEMANTIC"


# --------------------------------------------------------------------------
# Injection
# --------------------------------------------------------------------------


def test_set_and_get_judge_roundtrip() -> None:
    judge = _CountingJudge(SemanticVerdict.allow("semantic_allowed"))
    set_judge(judge)
    assert get_judge() is judge
    set_judge(None)
    assert get_judge() is None


# --------------------------------------------------------------------------
# Gate integration: env OFF
# --------------------------------------------------------------------------


def test_disabled_never_calls_judge(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    judge = _CountingJudge(SemanticVerdict.block())
    set_judge(judge)

    result = gate.evaluate_prompt_fields({"prompt": _NEUTRAL_TEXT})

    assert result.allowed is True
    assert judge.calls == 0


def test_disabled_direct_evaluate_reports_disabled() -> None:
    judge = _CountingJudge(SemanticVerdict.block())
    set_judge(judge)
    verdict = evaluate_fields_semantic({"prompt": _NEUTRAL_TEXT})
    assert verdict.allowed is True
    assert verdict.evaluated is False
    assert verdict.reason == REASON_DISABLED
    assert judge.calls == 0


# --------------------------------------------------------------------------
# Gate integration: env ON
# --------------------------------------------------------------------------


def test_enabled_block_verdict_blocks_with_generic_reason(
    policy_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    monkeypatch.setenv(semantic.SEMANTIC_ENV_VAR, "1")
    judge = _CountingJudge(SemanticVerdict.block())
    set_judge(judge)

    with caplog.at_level(logging.DEBUG):
        result = gate.evaluate_prompt_fields(
            {"prompt": f"please render {_NEUTRAL_TEXT}"}
        )

    assert result.allowed is False
    assert result.reason == REASON_BLOCKED
    assert result.field is None
    assert judge.calls == 1
    # No input text may appear in the returned reason or any log record.
    assert _NEUTRAL_TEXT not in result.reason
    assert all(
        _NEUTRAL_TEXT not in record.getMessage() for record in caplog.records
    )


def test_enabled_allow_verdict_allows(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    monkeypatch.setenv(semantic.SEMANTIC_ENV_VAR, "1")
    judge = _CountingJudge(
        SemanticVerdict.allow("semantic_allowed")
    )
    set_judge(judge)

    result = gate.evaluate_prompt_fields({"prompt": _NEUTRAL_TEXT})

    assert result.allowed is True
    assert result.reason == "ok"
    assert judge.calls == 1


def test_enabled_judge_raises_is_allowed(
    policy_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    monkeypatch.setenv(semantic.SEMANTIC_ENV_VAR, "1")

    def _boom(fields: dict) -> SemanticVerdict:
        raise RuntimeError(f"judge failed on {fields!r}")

    set_judge(_boom)

    with caplog.at_level(logging.DEBUG):
        result = gate.evaluate_prompt_fields({"prompt": _NEUTRAL_TEXT})
        verdict = evaluate_fields_semantic({"prompt": _NEUTRAL_TEXT})

    assert result.allowed is True
    assert verdict.allowed is True
    assert verdict.reason == REASON_ERROR
    # The failure is logged content-free: no field text and no exception text.
    assert any(
        record.levelno >= logging.WARNING for record in caplog.records
    )
    assert all(
        _NEUTRAL_TEXT not in record.getMessage() for record in caplog.records
    )


def test_enabled_ambiguous_response_is_allowed(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    monkeypatch.setenv(semantic.SEMANTIC_ENV_VAR, "1")
    ambiguous = parse_judge_response("I am not sure about this one")
    assert ambiguous.allowed is True
    assert ambiguous.reason == REASON_AMBIGUOUS
    set_judge(lambda fields: ambiguous)

    result = gate.evaluate_prompt_fields({"prompt": _NEUTRAL_TEXT})

    assert result.allowed is True


def test_enabled_unexpected_return_is_allowed(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    monkeypatch.setenv(semantic.SEMANTIC_ENV_VAR, "1")
    set_judge(lambda fields: "not-a-verdict")  # type: ignore[arg-type]

    result = gate.evaluate_prompt_fields({"prompt": _NEUTRAL_TEXT})

    assert result.allowed is True


def test_enabled_no_judge_is_allowed_and_logs_status(
    policy_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    monkeypatch.setenv(semantic.SEMANTIC_ENV_VAR, "1")
    set_judge(None)

    with caplog.at_level(logging.WARNING):
        result = gate.evaluate_prompt_fields({"prompt": _NEUTRAL_TEXT})
        verdict = evaluate_fields_semantic({"prompt": _NEUTRAL_TEXT})

    assert result.allowed is True
    assert verdict.allowed is True
    assert verdict.reason == REASON_UNAVAILABLE
    assert all(
        _NEUTRAL_TEXT not in record.getMessage() for record in caplog.records
    )


def test_enabled_judge_timeout_is_allowed(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    monkeypatch.setenv(semantic.SEMANTIC_ENV_VAR, "1")
    monkeypatch.setattr(semantic, "SEMANTIC_TIMEOUT_SECONDS", 0.05)

    def _slow(fields: dict) -> SemanticVerdict:
        time.sleep(0.5)
        return SemanticVerdict.block()

    set_judge(_slow)

    verdict = evaluate_fields_semantic({"prompt": _NEUTRAL_TEXT})

    assert verdict.allowed is True
    assert verdict.reason == REASON_TIMEOUT


# --------------------------------------------------------------------------
# Hash fast path: a match blocks without ever consulting the judge
# --------------------------------------------------------------------------


def test_hash_match_blocks_without_calling_judge(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    monkeypatch.setenv(semantic.SEMANTIC_ENV_VAR, "1")
    judge = _CountingJudge(SemanticVerdict.allow("semantic_allowed"))
    set_judge(judge)

    result = gate.evaluate_prompt_fields(
        {"prompt": f"please draw {_SYNTHETIC}"}
    )

    assert result.allowed is False
    assert result.reason == "prohibited_content"
    assert judge.calls == 0


# --------------------------------------------------------------------------
# Strict parser
# --------------------------------------------------------------------------


def test_parse_judge_response_blocks_only_on_explicit_unsafe() -> None:
    assert parse_judge_response("UNSAFE").allowed is False
    assert parse_judge_response("  unsafe.  ").allowed is False
    assert parse_judge_response("The content is UNSAFE").allowed is False


def test_parse_judge_response_allows_safe_and_ambiguous() -> None:
    assert parse_judge_response("SAFE").allowed is True
    assert parse_judge_response("Safe.").reason == semantic.REASON_ALLOWED
    assert parse_judge_response("maybe later").reason == REASON_AMBIGUOUS
    assert parse_judge_response("").reason == REASON_AMBIGUOUS
    assert parse_judge_response(None).reason == REASON_AMBIGUOUS


def test_parse_judge_response_never_echoes_input() -> None:
    verdict = parse_judge_response(f"UNSAFE because of {_SYNTHETIC}")
    assert verdict.allowed is False
    assert verdict.reason == REASON_BLOCKED
    assert _SYNTHETIC not in verdict.reason


# --------------------------------------------------------------------------
# Judge instruction reuse
# --------------------------------------------------------------------------


def test_build_judge_instruction_uses_guardrails() -> None:
    custom = "Always assist with care and respect."
    instruction = build_judge_instruction(custom)
    assert custom in instruction
    assert "SAFE" in instruction and "UNSAFE" in instruction


def test_build_judge_instruction_falls_back_to_builtin() -> None:
    for empty in (None, "", "   "):
        instruction = build_judge_instruction(empty)
        assert "SAFE" in instruction and "UNSAFE" in instruction
    assert build_judge_instruction(None) == instruction


def test_make_llm_judge_blocks_on_unsafe_response() -> None:
    seen: list[str] = []

    def _generate(request: str) -> str:
        seen.append(request)
        return "UNSAFE"

    judge = make_llm_judge(_generate, guardrails_prompt="Be safe.")
    verdict = judge({"prompt": _NEUTRAL_TEXT})

    assert verdict.allowed is False
    assert verdict.reason == REASON_BLOCKED
    # The instruction reached the model, but the verdict carries no content.
    assert seen and "Be safe." in seen[0]
    assert _NEUTRAL_TEXT not in verdict.reason


def test_make_llm_judge_allows_on_safe_response() -> None:
    judge = make_llm_judge(lambda request: "SAFE")
    verdict = judge({"prompt": _NEUTRAL_TEXT})
    assert verdict.allowed is True
    assert verdict.reason == semantic.REASON_ALLOWED


def test_make_llm_judge_allows_on_ambiguous_response() -> None:
    judge = make_llm_judge(lambda request: "no idea")
    verdict = judge({"prompt": _NEUTRAL_TEXT})
    assert verdict.allowed is True
    assert verdict.reason == REASON_AMBIGUOUS
