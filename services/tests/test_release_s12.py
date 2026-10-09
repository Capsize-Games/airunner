"""Release regression tests for issue #2110 (S12).

Publication gate for chatbot text and derived speech: visible output is
buffered whole, reviewed locally, and published only when allowed.
Denials fail closed (matcher block, missing policy data, unavailable /
timed-out / erroring contextual evaluator) without raising into the UI.
A denied final response carries a generic message that is distinct from
model-failure text. Cancellation drops buffered text.

Every token used here is synthetic and neutral. No model is loaded and
no network is used; the evaluator is injected through ``set_evaluator``
and every test resets shared safety state.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from airunner_common.contract_enums import ModelStatus
from airunner_services import content_safety_gate as gate
from airunner_services.content_safety import candidate_hashes, policy_data
from airunner_services.content_safety import semantic
from airunner_services.content_safety.matcher import (
    REASON_POLICY_UNAVAILABLE,
    REASON_PROHIBITED,
)
from airunner_services.content_safety.semantic import (
    REASON_ALLOWED,
    REASON_TIMEOUT,
    REASON_UNAVAILABLE,
    SemanticVerdict,
    set_evaluator,
    set_judge,
)
from airunner_services.llm.managers.mixins.generation_stream_support import (
    create_streaming_callback,
    create_thinking_callback,
    emit_visible_response,
    send_end_of_message,
)
from airunner_services.workers.tts_generator_worker import TTSGeneratorWorker

_REPO_ROOT = Path(__file__).resolve().parents[2]

_SYNTHETIC = "wobblequixotic"
_NEUTRAL_TEXT = "a calm neutral landscape painting"


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
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


@pytest.fixture
def policy_dir() -> Iterator[Path]:
    base = _REPO_ROOT / "tmp" / "content_safety_tests"
    base.mkdir(parents=True, exist_ok=True)
    created = Path(tempfile.mkdtemp(prefix="s12_", dir=base))
    yield created
    shutil.rmtree(created, ignore_errors=True)


def _load_synthetic_policy(
    policy_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    token: str = _SYNTHETIC,
) -> None:
    path = policy_dir / "policy_terms.dat"
    hashes = sorted(candidate_hashes(token))
    path.write_text(
        "".join(f"{digest}\n" for digest in hashes),
        encoding="utf-8",
    )
    monkeypatch.setenv(policy_data.POLICY_DATA_ENV_VAR, str(path))
    policy_data.reset_cache()


def _enable_contextual(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(semantic.CONTEXTUAL_ENV_VAR, "1")


def _make_owner(signals: list) -> SimpleNamespace:
    llm = SimpleNamespace(
        send_llm_text_streamed_signal=signals.append,
    )
    return SimpleNamespace(
        api=SimpleNamespace(llm=llm),
        logger=logging.getLogger("test_release_s12"),
        _current_request_id="req-s12",
        _workflow_manager=None,
        _interrupted=False,
    )


def _signal_texts(signals: list) -> list[str]:
    texts = []
    for signal in signals:
        texts.append(str(getattr(signal, "message", "") or ""))
        final = getattr(signal, "final_visible_message", None)
        if final:
            texts.append(str(final))
    return texts


def _make_tts_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Any, list, list]:
    monkeypatch.setattr(
        TTSGeneratorWorker,
        "chatbot",
        property(lambda self: SimpleNamespace(gender="Male", id=None)),
    )
    monkeypatch.setattr(
        TTSGeneratorWorker,
        "chatbot_voice_settings",
        property(lambda self: SimpleNamespace(model_type="Espeak")),
    )
    monkeypatch.setattr(
        TTSGeneratorWorker,
        "espeak_settings",
        property(
            lambda self: SimpleNamespace(
                rate=100,
                pitch=100,
                volume=100,
                voice="male1",
                language="en-US",
            )
        ),
    )
    worker = TTSGeneratorWorker.__new__(TTSGeneratorWorker)
    worker.do_interrupt = False
    worker.logger = logging.getLogger("test_release_s12")
    worker._failed_model = None
    synth_calls: list = []
    emitted: list = []
    worker.tts = SimpleNamespace(
        status=ModelStatus.LOADED,
        generate=lambda request: synth_calls.append(request) or b"audio",
    )
    worker.emit_signal = lambda code, data=None: emitted.append((code, data))
    return worker, synth_calls, emitted


def test_publication_gate_blocks_matched_output(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    result = gate.evaluate_publication_fields(
        {"message": f"neutral words {_SYNTHETIC} neutral words"}
    )
    assert result.allowed is False
    assert result.reason == REASON_PROHIBITED


def test_publication_gate_fails_closed_without_policy() -> None:
    result = gate.evaluate_publication_fields({"message": _NEUTRAL_TEXT})
    assert result.allowed is False
    assert result.reason == REASON_POLICY_UNAVAILABLE


def test_publication_gate_allows_neutral_output(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    result = gate.evaluate_publication_fields({"message": _NEUTRAL_TEXT})
    assert result.allowed is True


def test_streamed_text_buffered_then_published_in_order(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    signals: list = []
    owner = _make_owner(signals)
    request = SimpleNamespace(node_id="node-s12")
    complete = [""]
    sequence = [0]
    on_token = create_streaming_callback(owner, request, complete, sequence)
    on_thinking = create_thinking_callback(owner, request, sequence)
    for token in ["a calm ", "neutral ", "reply"]:
        on_token(token)
    assert signals == []
    on_thinking("streaming", "status update")
    assert len(signals) == 1
    assert signals[0].message_type == "thinking"
    send_end_of_message(
        owner, request, sequence, [], 1, 2, 3, complete[0], None
    )
    assert [s.message_type for s in signals[1:]] == ["assistant"] * 2
    assert signals[1].message == "a calm neutral reply"
    assert signals[1].is_end_of_message is False
    assert signals[2].is_end_of_message is True
    assert signals[2].final_visible_message == "a calm neutral reply"
    numbers = [s.sequence_number for s in signals]
    assert numbers == sorted(numbers) and len(set(numbers)) == len(numbers)


def test_denied_stream_publishes_denial_not_raw_text(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    raw = f"words {_SYNTHETIC} words"
    signals: list = []
    owner = _make_owner(signals)
    request = SimpleNamespace(node_id="node-s12")
    complete = [""]
    sequence = [0]
    on_token = create_streaming_callback(owner, request, complete, sequence)
    for token in ["words ", f"{_SYNTHETIC} ", "words"]:
        on_token(token)
    assert signals == []
    send_end_of_message(owner, request, sequence, [], 1, 2, 3, raw, None)
    assert len(signals) == 1
    assert signals[0].is_end_of_message is True
    assert (
        signals[0].final_visible_message
        == gate.GENERIC_PUBLICATION_DENIAL_MESSAGE
    )
    assert all(_SYNTHETIC not in text for text in _signal_texts(signals))
    denial = gate.GENERIC_PUBLICATION_DENIAL_MESSAGE
    assert denial and not denial.startswith("Error")
    assert _SYNTHETIC not in denial


def test_tool_originated_denied_text_withheld(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    raw = f"tool words {_SYNTHETIC} tool words"
    signals: list = []
    owner = _make_owner(signals)
    request = SimpleNamespace(node_id="node-s12")
    complete = [""]
    sequence = [0]
    create_streaming_callback(owner, request, complete, sequence)
    emit_visible_response(owner, request, raw, complete, sequence)
    assert signals == []
    assert complete[0] == gate.GENERIC_PUBLICATION_DENIAL_MESSAGE
    complete[0] = raw
    send_end_of_message(owner, request, sequence, [], 1, 2, 3, raw, None)
    assert len(signals) == 1
    assert (
        signals[0].final_visible_message
        == gate.GENERIC_PUBLICATION_DENIAL_MESSAGE
    )
    assert all(_SYNTHETIC not in text for text in _signal_texts(signals))


def test_tool_originated_allowed_text_published_once(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    signals: list = []
    owner = _make_owner(signals)
    request = SimpleNamespace(node_id="node-s12")
    complete = [""]
    sequence = [0]
    create_streaming_callback(owner, request, complete, sequence)
    emit_visible_response(owner, request, _NEUTRAL_TEXT, complete, sequence)
    assert len(signals) == 1
    send_end_of_message(
        owner, request, sequence, [], 1, 2, 3, _NEUTRAL_TEXT, None
    )
    assert len(signals) == 2
    assert "".join(_signal_texts(signals[:1])) == _NEUTRAL_TEXT
    assert signals[1].final_visible_message == _NEUTRAL_TEXT


def test_contextual_timeout_denies_but_stream_survives(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    _enable_contextual(monkeypatch)
    monkeypatch.setattr(semantic, "CONTEXTUAL_TIMEOUT_SECONDS", 0.05)

    def _slow(fields: dict[str, str]) -> SemanticVerdict:
        time.sleep(0.5)
        return SemanticVerdict.allow(REASON_ALLOWED)

    set_evaluator(_slow)
    direct = gate.evaluate_publication_fields({"message": _NEUTRAL_TEXT})
    assert direct.allowed is False
    assert direct.reason == REASON_TIMEOUT
    signals: list = []
    owner = _make_owner(signals)
    request = SimpleNamespace(node_id="node-s12")
    send_end_of_message(owner, request, [0], [], 1, 2, 3, _NEUTRAL_TEXT, None)
    assert len(signals) == 1
    assert signals[0].is_end_of_message is True
    assert (
        signals[0].final_visible_message
        == gate.GENERIC_PUBLICATION_DENIAL_MESSAGE
    )


def test_contextual_unavailable_denies(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    _enable_contextual(monkeypatch)
    set_evaluator(None)
    set_judge(None)
    direct = gate.evaluate_publication_fields({"message": _NEUTRAL_TEXT})
    assert direct.allowed is False
    assert direct.reason == REASON_UNAVAILABLE
    signals: list = []
    owner = _make_owner(signals)
    request = SimpleNamespace(node_id="node-s12")
    send_end_of_message(owner, request, [0], [], 1, 2, 3, _NEUTRAL_TEXT, None)
    assert len(signals) == 1
    assert (
        signals[0].final_visible_message
        == gate.GENERIC_PUBLICATION_DENIAL_MESSAGE
    )


def test_contextual_allowing_evaluator_publishes_neutral_text(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    _enable_contextual(monkeypatch)
    set_evaluator(
        lambda fields: SemanticVerdict.allow(REASON_ALLOWED),
    )
    signals: list = []
    owner = _make_owner(signals)
    request = SimpleNamespace(node_id="node-s12")
    complete = [""]
    sequence = [0]
    on_token = create_streaming_callback(owner, request, complete, sequence)
    on_token(_NEUTRAL_TEXT)
    send_end_of_message(
        owner, request, sequence, [], 1, 2, 3, complete[0], None
    )
    assert len(signals) == 2
    assert signals[0].message == _NEUTRAL_TEXT
    assert signals[1].final_visible_message == _NEUTRAL_TEXT


def test_interrupted_publish_drops_buffered_text(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    signals: list = []
    owner = _make_owner(signals)
    request = SimpleNamespace(node_id="node-s12")
    complete = [""]
    sequence = [0]
    on_token = create_streaming_callback(owner, request, complete, sequence)
    on_token("partial buffered reply")
    owner._interrupted = True
    send_end_of_message(
        owner, request, sequence, [], 1, 2, 3, complete[0], None
    )
    assert len(signals) == 1
    assert signals[0].is_end_of_message is True
    assert not signals[0].message
    assert not signals[0].final_visible_message
    assert all("partial" not in text for text in _signal_texts(signals))


def test_tts_denied_text_never_synthesized(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    worker, synth_calls, emitted = _make_tts_worker(monkeypatch)
    worker._generate(f"say {_SYNTHETIC} aloud")
    assert synth_calls == []
    assert emitted == []


def test_tts_allowed_text_synthesized(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_synthetic_policy(policy_dir, monkeypatch)
    worker, synth_calls, emitted = _make_tts_worker(monkeypatch)
    worker._generate(_NEUTRAL_TEXT)
    assert len(synth_calls) == 1
    assert _NEUTRAL_TEXT in synth_calls[0].message
    assert len(emitted) == 1
    assert emitted[0][1] == {"message": b"audio"}
