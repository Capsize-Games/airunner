"""Automatic harness wrapper for complex tasks.

This module provides automatic wrapping of complex tasks with the
Long-Running Harness. It integrates with the LLM generation flow
to detect and wrap multi-step tasks transparently.

Usage:
    The wrapper is called from the generation mixin when Auto mode
    detects a complex task. It:
    
    1. Creates a project for the task
    2. Decomposes the task into features (if multi-item)
    3. Wraps execution with progress tracking
    4. Returns results with coherent state management
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from airunner.components.llm.long_running.task_detector import (
    TaskAnalysis,
    TaskType,
    analyze_task,
)
from airunner.components.llm.long_running.project_manager import ProjectManager
from airunner.components.llm.long_running.data.project_state import (
    ProjectState,
    FeatureStatus,
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
    ):
        """Initialize the auto-wrapper.

        Args:
            chat_model: LangChain chat model instance
            on_progress: Optional callback for progress updates
                        Signature: (task_name, status, progress_pct)
        """
        self._chat_model = chat_model
        self._on_progress = on_progress
        self._project_manager = ProjectManager()
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

    def wrap_and_execute(
        self,
        prompt: str,
        execute_fn: Callable[[str], Dict[str, Any]],
        working_directory: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Wrap a task with the harness and execute it.

        This is the main entry point for automatic harness wrapping.
        It:
        1. Analyzes the task complexity
        2. Creates a project if needed
        3. Decomposes into features
        4. Executes each feature with progress tracking
        5. Returns aggregated results

        Args:
            prompt: User's input text (the task description)
            execute_fn: Function to execute each sub-task
                       Signature: (sub_prompt) -> Dict[str, Any]
            working_directory: Optional working directory for the project

        Returns:
            Dictionary with 'response' key and optional metadata
        """
        analysis = analyze_task(prompt)

        if not analysis.should_use_harness:
            # Simple task - execute directly without wrapping
            logger.debug(f"Simple task, executing directly: {prompt[:50]}...")
            return execute_fn(prompt)

        logger.info(
            f"Complex task detected ({analysis.task_type.value}): "
            f"{analysis.reason}"
        )

        # Create a project for this task
        project = self._create_project_for_task(
            prompt, analysis, working_directory
        )
        self._current_project_id = project.id

        self._emit_progress(
            f"Project '{project.name}'",
            "created",
            0.0,
        )

        # Add features based on detected items
        features = self._create_features_from_analysis(project.id, analysis, prompt)

        if not features:
            # No specific features detected - treat as single complex task
            logger.info("No specific features detected, executing as single task")
            result = execute_fn(prompt)
            self._mark_project_complete(project.id)
            return result

        # Execute each feature
        results = []
        total_features = len(features)

        for i, feature in enumerate(features):
            progress = i / total_features
            self._emit_progress(
                feature.name,
                "in_progress",
                progress,
            )

            # Update feature status
            self._project_manager.update_feature_status(
                feature.id, FeatureStatus.IN_PROGRESS.value
            )

            # Create sub-prompt for this feature
            sub_prompt = self._create_sub_prompt(prompt, feature, analysis)

            try:
                # Execute the sub-task
                result = execute_fn(sub_prompt)
                results.append(result)

                # Log progress
                self._project_manager.log_progress(
                    project_id=project.id,
                    feature_name=feature.name,
                    message=f"Completed: {feature.description[:100]}",
                    work_type="execution",
                )

                # Mark feature complete
                self._project_manager.update_feature_status(
                    feature.id, FeatureStatus.COMPLETED.value
                )

                self._emit_progress(
                    feature.name,
                    "completed",
                    (i + 1) / total_features,
                )

            except Exception as e:
                logger.error(f"Feature {feature.name} failed: {e}")
                self._project_manager.update_feature_status(
                    feature.id, FeatureStatus.BLOCKED.value
                )
                self._project_manager.log_progress(
                    project_id=project.id,
                    feature_name=feature.name,
                    message=f"Failed: {str(e)}",
                    work_type="error",
                )

        # Mark project complete
        self._mark_project_complete(project.id)

        # Aggregate results
        return self._aggregate_results(results, analysis, project)

    def _create_project_for_task(
        self,
        prompt: str,
        analysis: TaskAnalysis,
        working_directory: Optional[str],
    ) -> ProjectState:
        """Create a project for the detected task.

        Args:
            prompt: Original user prompt
            analysis: Task analysis result
            working_directory: Optional working directory

        Returns:
            Created ProjectState
        """
        # Generate a concise name from the prompt
        name = self._generate_project_name(prompt, analysis)

        project = self._project_manager.create_project(
            name=name,
            description=prompt,
            working_directory=working_directory,
            metadata={
                "task_type": analysis.task_type.value,
                "confidence": analysis.confidence,
                "auto_wrapped": True,
            },
        )

        logger.info(f"Created project '{name}' (ID: {project.id}) for task")
        return project

    def _create_features_from_analysis(
        self,
        project_id: int,
        analysis: TaskAnalysis,
        original_prompt: str,
    ) -> List[Any]:
        """Create features based on the task analysis.

        Args:
            project_id: Project ID to add features to
            analysis: Task analysis with detected items
            original_prompt: Original user prompt

        Returns:
            List of created ProjectFeature objects
        """
        features = []

        if analysis.detected_items:
            # Create a feature for each detected item
            for i, item in enumerate(analysis.detected_items):
                feature = self._project_manager.add_feature(
                    project_id=project_id,
                    name=self._sanitize_feature_name(item),
                    description=f"Process: {item}",
                    priority=i + 1,
                    dependencies=[],
                )
                features.append(feature)
                logger.debug(f"Created feature: {feature.name}")
        else:
            # Single complex task - create one feature
            feature = self._project_manager.add_feature(
                project_id=project_id,
                name="main_task",
                description=original_prompt[:200],
                priority=1,
                dependencies=[],
            )
            features.append(feature)

        return features

    def _create_sub_prompt(
        self,
        original_prompt: str,
        feature: Any,
        analysis: TaskAnalysis,
    ) -> str:
        """Create a focused sub-prompt for a specific feature.

        Args:
            original_prompt: Original user prompt
            feature: The feature to create a prompt for
            analysis: Task analysis

        Returns:
            Focused sub-prompt for this feature
        """
        if analysis.task_type == TaskType.MULTI_RESEARCH:
            # For research tasks, focus on the specific topic
            return f"Research and provide information about: {feature.name}"

        elif analysis.task_type == TaskType.CODING_PROJECT:
            # For coding tasks, include context
            return (
                f"Context: {original_prompt}\n\n"
                f"Focus on this specific task: {feature.description}"
            )

        else:
            # Generic multi-step
            return f"As part of '{original_prompt}', complete this step: {feature.description}"

    def _aggregate_results(
        self,
        results: List[Dict[str, Any]],
        analysis: TaskAnalysis,
        project: ProjectState,
    ) -> Dict[str, Any]:
        """Aggregate results from multiple feature executions.

        Args:
            results: List of results from each feature
            analysis: Task analysis
            project: The project

        Returns:
            Aggregated result dictionary
        """
        if not results:
            return {
                "response": "No results generated.",
                "project_id": project.id,
            }

        # Combine responses
        responses = []
        for i, result in enumerate(results):
            response = result.get("response", "")
            if response:
                responses.append(f"## Part {i + 1}\n\n{response}")

        combined = "\n\n---\n\n".join(responses)

        # Add summary header
        summary = (
            f"**Completed {len(results)} tasks** "
            f"(Project: {project.name}, ID: {project.id})\n\n"
        )

        return {
            "response": summary + combined,
            "project_id": project.id,
            "task_count": len(results),
            "task_type": analysis.task_type.value,
        }

    def _mark_project_complete(self, project_id: int) -> None:
        """Mark a project as complete.

        Args:
            project_id: Project ID to mark complete
        """
        project = self._project_manager.get_project(project_id)
        if project:
            self._project_manager.update_project_status(
                project_id, "completed"
            )
            logger.info(f"Project {project_id} marked complete")

    def _generate_project_name(
        self, prompt: str, analysis: TaskAnalysis
    ) -> str:
        """Generate a concise project name from the prompt.

        Args:
            prompt: User prompt
            analysis: Task analysis

        Returns:
            Generated project name
        """
        # Extract key words from prompt
        words = prompt.split()[:5]
        base_name = "_".join(w.lower() for w in words if len(w) > 2)

        # Add task type prefix
        prefix_map = {
            TaskType.MULTI_RESEARCH: "research",
            TaskType.CODING_PROJECT: "code",
            TaskType.MULTI_STEP: "task",
            TaskType.COMPLEX_ANALYSIS: "analysis",
        }
        prefix = prefix_map.get(analysis.task_type, "project")

        name = f"{prefix}_{base_name}"

        # Sanitize and truncate
        name = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
        return name[:50]

    def _sanitize_feature_name(self, name: str) -> str:
        """Sanitize a feature name.

        Args:
            name: Raw feature name

        Returns:
            Sanitized name
        """
        # Remove special characters, keep alphanumeric and underscores
        sanitized = "".join(
            c if c.isalnum() or c in "_- " else "_" for c in name
        )
        # Replace spaces with underscores
        sanitized = sanitized.replace(" ", "_")
        # Remove multiple underscores
        while "__" in sanitized:
            sanitized = sanitized.replace("__", "_")
        return sanitized[:50].strip("_")

    def _emit_progress(
        self, task_name: str, status: str, progress: float
    ) -> None:
        """Emit a progress update.

        Args:
            task_name: Name of current task/feature
            status: Status string
            progress: Progress percentage (0.0 to 1.0)
        """
        if self._on_progress:
            try:
                self._on_progress(task_name, status, progress)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")

    def get_current_project_id(self) -> Optional[int]:
        """Get the ID of the currently active project.

        Returns:
            Project ID or None if no project is active
        """
        return self._current_project_id


def create_auto_wrapper(
    chat_model: Any,
    on_progress: Optional[Callable[[str, str, float], None]] = None,
) -> AutoHarnessWrapper:
    """Factory function to create an AutoHarnessWrapper.

    Args:
        chat_model: LangChain chat model
        on_progress: Optional progress callback

    Returns:
        Configured AutoHarnessWrapper instance
    """
    return AutoHarnessWrapper(chat_model, on_progress)
