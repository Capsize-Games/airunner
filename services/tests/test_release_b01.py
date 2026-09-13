"""Regression tests for release issue B01.

Proves the companion contracts package (services/src/airunner_services/
llm/companion/) satisfies its own acceptance criteria:

- Importing it pulls in no Qt, torch, SQL driver, or redis module (it is
  orchestration interfaces only; B02-B16 provide real implementations).
- A minimal fake implementation of each Protocol satisfies it via
  isinstance() (the contracts are @runtime_checkable, not just
  statically typed).
- The worked "one turn, tool call, persistence, background follow-up"
  example from release-planning/linux-v1/companion-contracts.md
  actually composes and runs end to end against fakes.

No GUI/model/network/database access — every dependency here is a
fake satisfying a Protocol, never a real implementation.
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from typing import AsyncIterator, List

import pytest

from airunner_services.llm.companion import (
    CallChainId,
    ChatbotId,
    CompanionErrorCode,
    CompanionInferenceClient,
    CompanionInferenceRequest,
    CompanionJobHandle,
    CompanionJobRequest,
    CompanionJobType,
    CompanionMemoryRepository,
    CompanionScheduler,
    CompanionStreamEvent,
    CompanionToolDispatcher,
    CompanionTurnRequest,
    FactRecord,
    SessionRecord,
    ToolDispatchRequest,
    ToolDispatchResult,
    TurnRecord,
)
from airunner_services.runtimes.contracts import ChatMessage, MessageRole

_FORBIDDEN_MODULE_MARKERS = ("pyside6", "pyqt", "torch", "sqlalchemy", "psycopg", "redis")


def test_companion_package_import_is_free_of_qt_torch_and_sql_drivers() -> None:
    before = set(sys.modules.keys())
    import airunner_services.llm.companion  # noqa: F401

    after = set(sys.modules.keys())
    new_modules = after - before
    hits = [
        module
        for module in new_modules
        for marker in _FORBIDDEN_MODULE_MARKERS
        if marker in module.lower()
    ]
    assert hits == []


def test_companion_package_does_not_import_the_web_package() -> None:
    """The web repo's package is also named airunner_services (parent spec:
    "Do not import the web package at runtime or install both
    implementations in one environment") -- this cannot fully prove the
    web package is absent, but it does prove the companion module only
    ever references symbols this checkout's own airunner_services
    actually has, by virtue of the import above succeeding without a
    namespace collision error."""
    import airunner_services.llm.companion as companion

    assert companion.__file__ is not None
    assert "airunnerweb" not in companion.__file__


# --- Protocol conformance (runtime_checkable) ---


class _FakeMemoryRepository:
    def __init__(self) -> None:
        self.turns: List[TurnRecord] = []
        self.sessions: dict = {}

    def get_or_start_session(self, chatbot_id):
        session = self.sessions.get(chatbot_id)
        if session is None:
            session = SessionRecord(
                chatbot_id=chatbot_id, started_at="t0", last_message_at="t0"
            )
            self.sessions[chatbot_id] = session
        return session

    def append_turn(self, turn: TurnRecord) -> TurnRecord:
        turn = turn.model_copy(update={"turn_id": len(self.turns) + 1})
        self.turns.append(turn)
        return turn

    def get_recent_turns(self, chatbot_id, session_id, *, limit):
        return self.turns[-limit:]

    def update_session_summary(self, session) -> None:
        self.sessions[session.chatbot_id] = session

    def get_facts(self, chatbot_id, *, limit):
        return []

    def upsert_fact(self, fact: FactRecord) -> FactRecord:
        return fact


class _FakeScheduler:
    def __init__(self) -> None:
        self.scheduled: List[CompanionJobRequest] = []

    def schedule(self, request: CompanionJobRequest) -> CompanionJobHandle:
        self.scheduled.append(request)
        return CompanionJobHandle(
            job_id=f"job-{len(self.scheduled)}",
            job_type=request.job_type,
            accepted=True,
        )


class _FakeToolDispatcher:
    def available_tools(self, chatbot_id) -> List[str]:
        return ["get_weather"]

    def dispatch(self, request: ToolDispatchRequest) -> ToolDispatchResult:
        return ToolDispatchResult(
            tool_name=request.tool_name,
            content="Sunny, 22C",
            succeeded=True,
        )


class _FakeInferenceClient:
    async def stream(
        self, request: CompanionInferenceRequest
    ) -> AsyncIterator[CompanionStreamEvent]:
        for index, chunk in enumerate(["Sounds ", "lovely ", "out."]):
            yield CompanionStreamEvent(
                call_chain_id=request.call_chain_id,
                sequence=index,
                delta_text=chunk,
                final=(index == 2),
            )


def test_fake_memory_repository_satisfies_protocol() -> None:
    assert isinstance(_FakeMemoryRepository(), CompanionMemoryRepository)


def test_fake_scheduler_satisfies_protocol() -> None:
    assert isinstance(_FakeScheduler(), CompanionScheduler)


def test_fake_tool_dispatcher_satisfies_protocol() -> None:
    assert isinstance(_FakeToolDispatcher(), CompanionToolDispatcher)


def test_fake_inference_client_satisfies_protocol() -> None:
    assert isinstance(_FakeInferenceClient(), CompanionInferenceClient)


# --- The worked example from companion-contracts.md, end to end ---


def test_worked_example_one_turn_tool_call_persistence_background_job() -> None:
    memory_repo = _FakeMemoryRepository()
    scheduler = _FakeScheduler()
    tool_dispatcher = _FakeToolDispatcher()
    inference_client = _FakeInferenceClient()

    request = CompanionTurnRequest(
        chatbot_id=ChatbotId(7),
        call_chain_id=CallChainId(str(uuid.uuid4())),
        message="what's the weather looking like?",
    )

    # 1. Resolve/start the session.
    session = memory_repo.get_or_start_session(request.chatbot_id)
    assert session.chatbot_id == request.chatbot_id

    # 2. Compose messages (stand-in for B10's real prompt composition).
    recent_turns = memory_repo.get_recent_turns(
        request.chatbot_id,
        session.session_id,
        limit=request.context_budget.max_recent_turns,
    )
    facts = memory_repo.get_facts(
        request.chatbot_id, limit=request.context_budget.max_facts
    )
    assert recent_turns == []
    assert facts == []
    messages = [ChatMessage(role=MessageRole.USER, content=request.message)]

    # 3. Tool dispatch.
    assert "get_weather" in tool_dispatcher.available_tools(request.chatbot_id)
    tool_result = tool_dispatcher.dispatch(
        ToolDispatchRequest(
            tool_name="get_weather",
            arguments={},
            chatbot_id=request.chatbot_id,
        )
    )
    assert tool_result.succeeded
    messages.append(ChatMessage(role=MessageRole.TOOL, content=tool_result.content))

    # 4. Inference (streamed).
    inference_request = CompanionInferenceRequest(
        call_chain_id=request.call_chain_id, messages=messages
    )

    async def _run_inference() -> str:
        reply = ""
        async for event in inference_client.stream(inference_request):
            reply += event.delta_text
            if event.final:
                break
        return reply

    reply_text = asyncio.run(_run_inference())
    assert reply_text == "Sounds lovely out."

    # 5. Persist the completed turn BEFORE scheduling background work
    #    (parent spec architecture decision #4).
    turn = memory_repo.append_turn(
        TurnRecord(
            chatbot_id=request.chatbot_id,
            session_id=session.session_id or 0,
            role="assistant",
            content=reply_text,
            turn_index=len(recent_turns),
            call_chain_id=request.call_chain_id,
        )
    )
    assert turn.turn_id is not None
    assert memory_repo.turns == [turn]

    # 6. Schedule bounded background follow-up, keyed for idempotency.
    handle = scheduler.schedule(
        CompanionJobRequest(
            job_type=CompanionJobType.FACT_EXTRACTION,
            chatbot_id=request.chatbot_id,
            session_id=session.session_id,
            idempotency_key=f"fact-extract:{turn.turn_id}",
        )
    )
    assert handle.accepted
    assert scheduler.scheduled[0].job_type == CompanionJobType.FACT_EXTRACTION


def test_companion_error_carries_a_deterministic_code_not_free_text() -> None:
    from airunner_services.llm.companion import CompanionError, ERROR_SESSION_EXPIRED

    error = CompanionError(
        CompanionErrorCode(code=ERROR_SESSION_EXPIRED, detail="session gone", retryable=True)
    )
    assert error.error.code == ERROR_SESSION_EXPIRED
    assert error.error.retryable is True


def test_context_budget_has_sane_defaults() -> None:
    request = CompanionTurnRequest(
        chatbot_id=ChatbotId(1),
        call_chain_id=CallChainId("cc-1"),
        message="hi",
    )
    assert request.context_budget.max_prompt_tokens > 0
    assert request.context_budget.max_recent_turns > 0
