"""Thin facade for automatic harness wrapping."""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from airunner_services.llm.long_running.auto_wrapper_execution import (
    wrap_and_execute,
)
from airunner_services.llm.long_running.auto_wrapper_project import (
    create_features_from_analysis,
    create_project_for_task,
    generate_project_name,
    mark_project_complete,
    sanitize_feature_name,
)
from airunner_services.llm.long_running.auto_wrapper_prompting import (
    create_sub_prompt,
)
from airunner_services.llm.long_running.auto_wrapper_results import (
    aggregate_results,
)
from airunner_services.llm.long_running.auto_wrapper_progress import emit_progress
from airunner_services.llm.long_running.task_detector import analyze_task
from airunner_services.llm.long_running.project_manager import ProjectManager
from airunner_services.llm.long_running.runtime_components import (
    resolve_project_manager,
)

logger = logging.getLogger(__name__)


class AutoHarnessWrapper:
    """Automatically wraps complex tasks with the Long-Running Harness.

    This wrapper provides:
    - Automatic task complexity detection
    - Project creation for multi-step tasks
    - Feature decomposition based on detected items
    - Progress tracking and state management
    - Coherent execution across multiple sub-tasks
    """

    def __init__(
        self,
        chat_model: Any,
        on_progress: Optional[Callable[[str, str, float], None]] = None,
        project_manager: Optional[ProjectManager] = None,
    ) -> None:
        """Initialize the auto-wrapper."""
        self._chat_model = chat_model
        self._on_progress = on_progress
        self._project_manager = resolve_project_manager(project_manager)
        self._current_project_id: Optional[int] = None

    def should_wrap(self, prompt: str) -> bool:
        """Check if a prompt should be wrapped with the harness.

        Args:
            prompt: User's input text

        Returns:
            True if the task is complex enough to benefit from wrapping
        """
        analysis = analyze_task(prompt)
        return analysis.should_use_harness

    wrap_and_execute = wrap_and_execute
    _create_project_for_task = create_project_for_task
    _create_features_from_analysis = create_features_from_analysis
    _create_sub_prompt = create_sub_prompt
    _aggregate_results = aggregate_results
    _mark_project_complete = mark_project_complete
    _generate_project_name = generate_project_name
    _sanitize_feature_name = sanitize_feature_name
    _emit_progress = emit_progress

    def get_current_project_id(self) -> Optional[int]:
        """Get the ID of the currently active project.

        Returns:
            Project ID or None if no project is active
        """
        return self._current_project_id


def create_auto_wrapper(
    chat_model: Any,
    on_progress: Optional[Callable[[str, str, float], None]] = None,
    project_manager: Optional[ProjectManager] = None,
) -> AutoHarnessWrapper:
    """Return a configured automatic harness wrapper."""
    return AutoHarnessWrapper(
        chat_model,
        on_progress,
        project_manager=project_manager,
    )
