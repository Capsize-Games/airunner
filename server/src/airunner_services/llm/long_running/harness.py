"""Thin facade for the long-running harness."""

from __future__ import annotations

from typing import Any, Callable, Optional

from airunner_services.llm.long_running.harness_autonomous import (
    run_until_complete,
)
from airunner_services.llm.long_running.harness_decisions import (
    add_decision_feedback,
    get_decision_history,
)
from airunner_services.llm.long_running.harness_project import (
    abandon_project,
    create_project,
    pause_project,
    resume_project,
    revert_to_checkpoint,
)
from airunner_services.llm.long_running.harness_reporting import (
    export_project_report,
)
from airunner_services.llm.long_running.harness_runtime import (
    initialize_runtime,
    register_sub_agent,
)
from airunner_services.llm.long_running.harness_session import run_session
from airunner_services.llm.long_running.harness_status import get_project_status
from airunner_services.llm.long_running.project_manager import ProjectManager
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class LongRunningHarness:
    """Main orchestrator for long-running agent projects."""

    def __init__(
        self, chat_model: Any, tools: Optional[list[Any]] = None,
        project_manager: Optional[ProjectManager] = None,
        sub_agents: Optional[dict[str, Any]] = None,
        on_progress: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> None:
        """Initialize the harness."""
        self._chat_model = chat_model
        self._tools = tools or []
        self._on_progress = on_progress
        initialize_runtime(self, project_manager, sub_agents)
        logger.info("LongRunningHarness initialized")

    register_sub_agent = register_sub_agent
    create_project = create_project
    run_session = run_session
    run_until_complete = run_until_complete
    resume_project = resume_project
    get_project_status = get_project_status
    pause_project = pause_project
    abandon_project = abandon_project
    revert_to_checkpoint = revert_to_checkpoint
    get_decision_history = get_decision_history
    add_decision_feedback = add_decision_feedback
    export_project_report = export_project_report


# The facade intentionally preserves the public API while delegating behavior
# into neighboring helper modules.
# Keeping this file thin makes orchestration entrypoints easier to scan.
