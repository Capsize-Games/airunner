"""Resumable background runner for persisted coding-agent work."""

import time
from threading import RLock
from typing import Any

from PySide6.QtCore import QObject, Signal

from airunner.components.agents.runtime.agent_message_channel import (
    AgentMessageChannel,
)
from airunner.components.agents.runtime.agent_message_record import (
    AgentMessageRecord,
)
from airunner.components.agents.runtime.agent_role import AgentRole
from airunner.components.agents.runtime.agent_run_record import (
    AgentRunRecord,
)
from airunner.components.agents.runtime.agent_run_status import (
    AgentRunStatus,
)
from airunner.components.agents.runtime.agent_session_record import (
    AgentSessionRecord,
)
from airunner.components.agents.runtime.agent_task_record import (
    AgentTaskRecord,
)
from airunner.components.agents.runtime.agent_task_status import (
    AgentTaskStatus,
)
from airunner.components.document_editor.project.airunner_project_state_service import (
    AirunnerProjectStateService,
)
from airunner.utils.application.background_worker import BackgroundWorker


class AgentBackgroundRunManager(QObject):
    """Run persisted coding-agent work in background threads."""

    runProgressUpdated = Signal(str, object)
    runStatusUpdated = Signal(str, str)
    runMessageLogged = Signal(str, str, str)
    runFinished = Signal(str, dict)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._lock = RLock()
        self._workers: dict[str, BackgroundWorker] = {}
        self._state_services: dict[str, AirunnerProjectStateService] = {}
        self._pause_requests: set[str] = set()
        self._cancel_requests: set[str] = set()

    def start_scripted_run(
        self,
        state_service: AirunnerProjectStateService,
        session: AgentSessionRecord,
        task: AgentTaskRecord,
        role: AgentRole,
        steps: list[dict[str, Any]],
        *,
        summary: str = "",
    ) -> str:
        """Start a persisted background run using serialized step data."""
        run = AgentRunRecord(
            session_id=session.record_id,
            task_id=task.record_id,
            role=role,
            status=AgentRunStatus.RUNNING,
            summary=summary,
            metadata={
                "steps": list(steps),
                "current_step_index": 0,
            },
        )
        session.active_run_id = run.record_id
        session.status = AgentRunStatus.RUNNING
        if task.record_id not in session.task_ids:
            session.task_ids.append(task.record_id)
        task.status = AgentTaskStatus.IN_PROGRESS
        state_service.save_session(session)
        state_service.save_task(task)
        state_service.save_run(run)
        self._launch_worker(run.record_id, state_service)
        self.runStatusUpdated.emit(run.record_id, AgentRunStatus.RUNNING.value)
        return run.record_id

    def pause_run(self, run_id: str) -> bool:
        """Pause a running background agent run."""
        state_service = self._state_services.get(run_id)
        if state_service is None:
            return False
        with self._lock:
            self._pause_requests.add(run_id)
        self._update_run_state(
            run_id,
            state_service,
            run_status=AgentRunStatus.PAUSED,
            task_status=AgentTaskStatus.BLOCKED,
        )
        self.runStatusUpdated.emit(run_id, AgentRunStatus.PAUSED.value)
        return True

    def resume_run(self, run_id: str) -> bool:
        """Resume a paused background agent run."""
        state_service = self._state_services.get(run_id)
        if state_service is None:
            return False
        with self._lock:
            self._pause_requests.discard(run_id)
        self._update_run_state(
            run_id,
            state_service,
            run_status=AgentRunStatus.RUNNING,
            task_status=AgentTaskStatus.IN_PROGRESS,
        )
        self.runStatusUpdated.emit(run_id, AgentRunStatus.RUNNING.value)
        return True

    def cancel_run(self, run_id: str) -> bool:
        """Cancel an active background agent run."""
        state_service = self._state_services.get(run_id)
        worker = self._workers.get(run_id)
        if state_service is None or worker is None:
            return False
        with self._lock:
            self._cancel_requests.add(run_id)
        worker.cancel()
        self.runStatusUpdated.emit(run_id, AgentRunStatus.CANCELLED.value)
        return True

    def restore_unfinished_runs(
        self,
        state_service: AirunnerProjectStateService,
    ) -> list[str]:
        """Restore unfinished runs from persisted .airunner state."""
        restored: list[str] = []
        for session in state_service.list_resumable_sessions():
            if not session.active_run_id:
                continue
            run = state_service.load_run(session.active_run_id)
            if run.status not in self._restorable_run_statuses():
                continue
            if run.status == AgentRunStatus.PAUSED:
                with self._lock:
                    self._pause_requests.add(run.record_id)
            self._launch_worker(run.record_id, state_service)
            restored.append(run.record_id)
        return restored

    def _launch_worker(
        self,
        run_id: str,
        state_service: AirunnerProjectStateService,
    ) -> None:
        """Create, track, and start one background worker."""
        with self._lock:
            if run_id in self._workers:
                return
            self._state_services[run_id] = state_service
        worker = BackgroundWorker(
            task_function=lambda worker, active_run_id=run_id: (
                self._execute_scripted_run(active_run_id, worker)
            ),
            callback_data={"run_id": run_id},
        )
        worker.progressUpdate.connect(
            lambda value, active_run_id=run_id: self._on_progress(
                active_run_id,
                value,
            )
        )
        worker.statusUpdate.connect(
            lambda message, active_run_id=run_id: self._on_status(
                active_run_id,
                message,
            )
        )
        worker.taskFinished.connect(
            lambda payload, active_run_id=run_id: self._on_finished(
                active_run_id,
                payload,
            )
        )
        with self._lock:
            self._workers[run_id] = worker
        worker.start()

    def _execute_scripted_run(
        self,
        run_id: str,
        worker: BackgroundWorker,
    ) -> dict[str, Any]:
        """Execute serialized step data for one persisted run."""
        state_service = self._state_services[run_id]
        run = state_service.load_run(run_id)
        steps = list(run.metadata.get("steps", []))
        start_index = int(run.metadata.get("current_step_index", 0))
        if start_index >= len(steps):
            self._mark_completed(run_id, state_service)
            return {"status": AgentRunStatus.COMPLETED.value}
        for index in range(start_index, len(steps)):
            self._wait_if_paused(run_id, worker)
            if self._should_cancel(run_id, worker):
                self._mark_cancelled(run_id, state_service)
                return {"status": AgentRunStatus.CANCELLED.value}
            step = dict(steps[index])
            status_message = step.get("status") or self._default_status(
                index,
                len(steps),
            )
            worker.update_status(str(status_message))
            progress = step.get("progress")
            if progress is not None:
                worker.update_progress(progress)
            commentary = step.get("commentary")
            if commentary:
                state_service.append_message(
                    run_id,
                    AgentMessageRecord(
                        content=str(commentary),
                        channel=AgentMessageChannel.COMMENTARY,
                        role=run.role,
                    ),
                )
                self.runMessageLogged.emit(
                    run_id,
                    AgentMessageChannel.COMMENTARY.value,
                    str(commentary),
                )
            self._sleep_with_controls(
                float(step.get("delay_seconds", 0.0) or 0.0),
                run_id,
                worker,
            )
            if self._should_cancel(run_id, worker):
                self._mark_cancelled(run_id, state_service)
                return {"status": AgentRunStatus.CANCELLED.value}
            run = state_service.load_run(run_id)
            run.status = AgentRunStatus.RUNNING
            run.metadata["current_step_index"] = index + 1
            state_service.save_run(run)
        self._mark_completed(run_id, state_service)
        return {"status": AgentRunStatus.COMPLETED.value}

    def _wait_if_paused(
        self,
        run_id: str,
        worker: BackgroundWorker,
    ) -> None:
        """Block while a run is paused, keeping cancellation responsive."""
        while self._is_paused(run_id) and not self._should_cancel(run_id, worker):
            worker.update_status(AgentRunStatus.PAUSED.value)
            time.sleep(0.05)

    def _sleep_with_controls(
        self,
        delay_seconds: float,
        run_id: str,
        worker: BackgroundWorker,
    ) -> None:
        """Sleep in short intervals so pause and cancel stay responsive."""
        deadline = time.monotonic() + max(delay_seconds, 0.0)
        while time.monotonic() < deadline:
            self._wait_if_paused(run_id, worker)
            if self._should_cancel(run_id, worker):
                return
            time.sleep(0.05)

    def _mark_completed(
        self,
        run_id: str,
        state_service: AirunnerProjectStateService,
    ) -> None:
        """Persist completed state for one run and its owning records."""
        run = state_service.load_run(run_id)
        run.status = AgentRunStatus.COMPLETED
        state_service.save_run(run)
        self._update_session_and_task(
            run,
            state_service,
            AgentRunStatus.COMPLETED,
            AgentTaskStatus.COMPLETED,
        )
        self.runStatusUpdated.emit(run_id, AgentRunStatus.COMPLETED.value)

    def _mark_cancelled(
        self,
        run_id: str,
        state_service: AirunnerProjectStateService,
    ) -> None:
        """Persist cancelled state for one run and its owning records."""
        run = state_service.load_run(run_id)
        run.status = AgentRunStatus.CANCELLED
        state_service.save_run(run)
        self._update_session_and_task(
            run,
            state_service,
            AgentRunStatus.CANCELLED,
            AgentTaskStatus.CANCELLED,
        )
        self.runStatusUpdated.emit(run_id, AgentRunStatus.CANCELLED.value)

    def _update_run_state(
        self,
        run_id: str,
        state_service: AirunnerProjectStateService,
        *,
        run_status: AgentRunStatus,
        task_status: AgentTaskStatus,
    ) -> None:
        """Persist a state transition for one run and its owning records."""
        run = state_service.load_run(run_id)
        run.status = run_status
        state_service.save_run(run)
        self._update_session_and_task(
            run,
            state_service,
            run_status,
            task_status,
        )

    def _update_session_and_task(
        self,
        run: AgentRunRecord,
        state_service: AirunnerProjectStateService,
        session_status: AgentRunStatus,
        task_status: AgentTaskStatus,
    ) -> None:
        """Persist session and task state for one run."""
        session = state_service.load_session(run.session_id)
        task = state_service.load_task(run.task_id)
        session.status = session_status
        session.active_run_id = (
            None if self._is_terminal_status(session_status)
            else run.record_id
        )
        task.status = task_status
        state_service.save_session(session)
        state_service.save_task(task)

    def _on_progress(self, run_id: str, value: object) -> None:
        """Forward progress updates to the UI layer."""
        self.runProgressUpdated.emit(run_id, value)

    def _on_status(self, run_id: str, message: str) -> None:
        """Forward status updates to the UI layer."""
        self.runStatusUpdated.emit(run_id, message)

    def _on_finished(self, run_id: str, payload: dict[str, Any]) -> None:
        """Finalize bookkeeping after one background worker exits."""
        state_service = self._state_services.get(run_id)
        if state_service is not None and payload.get("error"):
            self._update_run_state(
                run_id,
                state_service,
                run_status=AgentRunStatus.FAILED,
                task_status=AgentTaskStatus.FAILED,
            )
            self.runStatusUpdated.emit(run_id, AgentRunStatus.FAILED.value)
        with self._lock:
            self._workers.pop(run_id, None)
            self._pause_requests.discard(run_id)
            self._cancel_requests.discard(run_id)
        self.runFinished.emit(run_id, payload)

    def _restorable_run_statuses(self) -> set[AgentRunStatus]:
        """Return run states that should be restored on startup."""
        return {
            AgentRunStatus.PENDING,
            AgentRunStatus.RUNNING,
            AgentRunStatus.PAUSED,
        }

    def _default_status(self, index: int, total_steps: int) -> str:
        """Return a default status string for a scripted step."""
        return f"step {index + 1} of {total_steps}"

    def _is_terminal_status(self, status: AgentRunStatus) -> bool:
        """Return whether a run status is terminal."""
        return status in {
            AgentRunStatus.COMPLETED,
            AgentRunStatus.FAILED,
            AgentRunStatus.CANCELLED,
        }

    def _is_paused(self, run_id: str) -> bool:
        """Return whether one run is currently paused."""
        with self._lock:
            return run_id in self._pause_requests

    def _should_cancel(
        self,
        run_id: str,
        worker: BackgroundWorker,
    ) -> bool:
        """Return whether one run should exit early."""
        with self._lock:
            return worker.is_cancelled or run_id in self._cancel_requests