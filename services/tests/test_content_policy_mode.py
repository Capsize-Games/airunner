"""Integration coverage for the optional application content policy."""

from __future__ import annotations

import pytest

from airunner_services import content_safety_gate as gate
from airunner_services.content_safety import candidate_hashes, policy_data, semantic
from airunner_services.content_safety import image_verdict
from airunner_services.content_safety.config import (
    CONTENT_POLICY_MODE_ENV_VAR,
    ContentPolicyConfigurationError,
    resolve_content_policy_mode,
)
from airunner_services.content_safety.image_verdict import (
    REASON_DISABLED,
    REASON_UNAVAILABLE,
    evaluate_image_batch,
    evaluate_images,
)
from airunner_services.content_safety.matcher import REASON_POLICY_UNAVAILABLE
from airunner_services.content_safety.semantic import SemanticVerdict


@pytest.fixture(autouse=True)
def _clean_policy_state(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(CONTENT_POLICY_MODE_ENV_VAR, raising=False)
    monkeypatch.delenv(policy_data.POLICY_DATA_ENV_VAR, raising=False)
    monkeypatch.delenv(semantic.SEMANTIC_ENV_VAR, raising=False)
    policy_data.reset_cache()
    semantic.set_judge(None)
    image_verdict.set_evaluator(None)
    yield
    policy_data.reset_cache()
    semantic.set_judge(None)
    image_verdict.set_evaluator(None)


def test_default_mode_skips_text_matcher_and_semantic_callbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert resolve_content_policy_mode() == "disabled"

    def _unexpected(*_args, **_kwargs):
        raise AssertionError("disabled mode invoked a policy callback")

    monkeypatch.setattr(gate, "check_prompt_fields", _unexpected)
    monkeypatch.setattr(gate, "evaluate_fields_semantic", _unexpected)
    monkeypatch.setattr(gate, "evaluate_fields_contextual", _unexpected)
    fields = {"prompt": "a neutral synthetic request"}
    assert gate.evaluate_prompt_fields(fields).allowed
    assert gate.evaluate_publication_fields(fields).allowed
    gate.enforce_prompt_fields(fields)


def test_default_mode_allows_images_without_calling_evaluator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[int] = []
    evaluator = lambda images: calls.append(len(images)) or [True] * len(images)
    image_verdict.set_evaluator(evaluator)
    verdict = evaluate_image_batch([object(), object()], evaluator)
    registered = evaluate_images([object()])
    assert verdict.all_allowed and registered.all_allowed
    assert verdict.reasons == [REASON_DISABLED, REASON_DISABLED]
    assert not any(item.evaluated for item in verdict.verdicts)
    assert calls == []


def test_enforcement_fails_closed_without_policy_or_image_evaluator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(CONTENT_POLICY_MODE_ENV_VAR, "enforce")
    policy_data.reset_cache()
    text = gate.evaluate_prompt_fields({"prompt": "neutral test input"})
    images = evaluate_image_batch([object()], None)
    assert not text.allowed
    assert text.reason == REASON_POLICY_UNAVAILABLE
    assert images.withheld == [True]
    assert images.reasons == [REASON_UNAVAILABLE]


def test_enforcement_uses_matcher_then_registered_semantic_callback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv(CONTENT_POLICY_MODE_ENV_VAR, "enforce")
    monkeypatch.setenv(semantic.SEMANTIC_ENV_VAR, "1")
    token = "synthetic-neutral-callback-token"
    policy_file = tmp_path / "policy_terms.dat"
    policy_file.write_text(
        "".join(f"{digest}\n" for digest in sorted(candidate_hashes("unrelated"))),
        encoding="utf-8",
    )
    monkeypatch.setenv(policy_data.POLICY_DATA_ENV_VAR, str(policy_file))
    policy_data.reset_cache()
    seen: list[dict[str, str]] = []

    def _deny(fields: dict[str, str]) -> SemanticVerdict:
        seen.append(fields)
        return SemanticVerdict.block()

    semantic.set_judge(_deny)
    result = gate.evaluate_prompt_fields({"prompt": token})
    assert not result.allowed
    assert result.reason == gate.SEMANTIC_BLOCKED_REASON
    assert seen == [{"prompt": token}]


@pytest.mark.parametrize("value", ["", "true", "on", "Disabled", "disabled ", " enforce "])
def test_invalid_mode_values_are_rejected(value: str, monkeypatch) -> None:
    monkeypatch.setenv(CONTENT_POLICY_MODE_ENV_VAR, value)
    with pytest.raises(ContentPolicyConfigurationError):
        resolve_content_policy_mode()
