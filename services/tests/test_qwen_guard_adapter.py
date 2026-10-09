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

import logging
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Optional

import pytest

from airunner_services import content_safety_gate as gate
from airunner_services.content_safety import candidate_hashes, policy_data
from airunner_services.content_safety import qwen_guard
from airunner_services.content_safety import semantic
from airunner_services.content_safety.qwen_guard import (
    GuardCorpusCase,
    evaluate_guard_corpus,
)
from airunner_services.content_safety.semantic import (
    REASON_ALLOWED,
    REASON_AMBIGUOUS,
    REASON_BLOCKED,
    SemanticVerdict,
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


class _StubTokenizer:
    def __init__(self) -> None:
        self.messages: list = []

    def apply_chat_template(
        self, messages, tokenize=False, add_generation_prompt=True
    ):
        self.messages.append(messages)
        assert tokenize is False
        assert add_generation_prompt is True
        return "TEMPLATED:" + messages[0]["content"]


class _StubClassifier:
    def __init__(self, reply: str) -> None:
        self.tokenizer = _StubTokenizer()
        self.calls: list = []
        self._reply = reply

    def __call__(self, prompt, max_new_tokens=0, return_full_text=True):
        self.calls.append((prompt, max_new_tokens, return_full_text))
        return [{"generated_text": self._reply}]


class _StubPipelines:
    def __init__(self, reply: str) -> None:
        self.kwargs: dict = {}
        self.classifier = _StubClassifier(reply)

    def __call__(self, task, **kwargs):
        self.kwargs = {"task": task, **kwargs}
        return self.classifier


def _install_stub_transformers(
    monkeypatch: pytest.MonkeyPatch, reply: str
) -> _StubPipelines:
    fake = ModuleType("transformers")
    pipelines = _StubPipelines(reply)
    setattr(fake, "pipeline", pipelines)
    monkeypatch.setitem(sys.modules, "transformers", fake)
    return pipelines


def test_loader_is_local_only_and_parses_strict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pipelines = _install_stub_transformers(
        monkeypatch, "Safety: Unsafe\nCategories: withheld"
    )
    evaluator = qwen_guard.load_qwen_guard_evaluator()
    assert pipelines.kwargs["task"] == "text-generation"
    assert pipelines.kwargs["model"] == qwen_guard.MODEL_ID
    assert pipelines.kwargs["revision"] is None
    assert pipelines.kwargs["local_files_only"] is True
    assert pipelines.kwargs["trust_remote_code"] is False
    verdict = evaluator({"prompt": _NEUTRAL_TEXT})
    assert verdict.allowed is False
    assert verdict.reason == REASON_BLOCKED
    prompt, max_tokens, full = pipelines.classifier.calls[0]
    assert prompt.startswith("TEMPLATED:")
    assert max_tokens == qwen_guard.MAX_NEW_TOKENS
    assert full is False


def test_loader_passes_revision_pin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pipelines = _install_stub_transformers(monkeypatch, "Safety: Safe")
    evaluator = qwen_guard.load_qwen_guard_evaluator(revision="abc123")
    assert pipelines.kwargs["revision"] == "abc123"
    verdict = evaluator({"prompt": _NEUTRAL_TEXT})
    assert verdict.allowed is True


def test_loader_failure_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = ModuleType("transformers")

    def _boom(task, **kwargs):
        raise OSError("no cached weights")

    setattr(fake, "pipeline", _boom)
    monkeypatch.setitem(sys.modules, "transformers", fake)
    with pytest.raises(qwen_guard.QwenGuardUnavailableError):
        qwen_guard.load_qwen_guard_evaluator()


def test_missing_transformers_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "transformers", None)
    with pytest.raises(qwen_guard.QwenGuardUnavailableError):
        qwen_guard.load_qwen_guard_evaluator()


def test_register_installs_evaluator_on_seam(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _install_stub_transformers(monkeypatch, "Safety: Safe")
    with caplog.at_level(logging.INFO):
        evaluator = qwen_guard.register_qwen_guard_evaluator()
    assert semantic.get_evaluator() is evaluator
    assert all(
        _NEUTRAL_TEXT not in record.getMessage() for record in caplog.records
    )


def test_corpus_metrics_count_only_aggregates() -> None:
    verdicts = {
        "tn": SemanticVerdict.allow(REASON_ALLOWED),
        "tp": SemanticVerdict.block(),
        "fp": SemanticVerdict.block(),
        "fn": SemanticVerdict.allow(REASON_ALLOWED),
        "amb": SemanticVerdict(
            evaluated=True, allowed=False, reason=REASON_AMBIGUOUS
        ),
    }

    def _scripted(fields: dict) -> SemanticVerdict:
        return verdicts[fields["key"]]

    cases = [
        GuardCorpusCase({"key": "tn"}, True),
        GuardCorpusCase({"key": "tp"}, False),
        GuardCorpusCase({"key": "fp"}, True),
        GuardCorpusCase({"key": "fn"}, False),
        GuardCorpusCase({"key": "amb"}, False),
    ]
    metrics = evaluate_guard_corpus(cases, _scripted)
    assert metrics.cases == 5
    assert metrics.denied == 3
    assert metrics.denied_ambiguous == 1
    assert metrics.true_positives == 2
    assert metrics.false_positives == 1
    assert metrics.false_negatives == 1
    assert metrics.precision == pytest.approx(2 / 3)
    assert metrics.recall == pytest.approx(2 / 3)
    assert metrics.f1 == pytest.approx(2 / 3)


def test_adapter_import_loads_no_model_stack() -> None:
    src = _REPO_ROOT / "services" / "src"
    code = (
        "import sys; "
        f"sys.path.insert(0, r'{src}'); "
        "import airunner_services.content_safety.qwen_guard as m; "
        "assert 'torch' not in sys.modules; "
        "assert 'transformers' not in sys.modules; "
        "assert m.MODEL_ID.startswith('Qwen/')"
    )
    subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )


@pytest.mark.integration
def test_real_guard_evaluates_neutral_request() -> None:
    """Real-model smoke: structured verdict only, no efficacy claim."""
    pytest.importorskip("transformers")
    try:
        evaluator = qwen_guard.load_qwen_guard_evaluator()
    except qwen_guard.QwenGuardUnavailableError:
        pytest.skip("Qwen3Guard weights are not cached locally")
    verdict = evaluator({"prompt": _NEUTRAL_TEXT})
    assert isinstance(verdict, SemanticVerdict)
    assert verdict.evaluated is True
    assert verdict.reason in (
        REASON_ALLOWED,
        REASON_BLOCKED,
        REASON_AMBIGUOUS,
    )
