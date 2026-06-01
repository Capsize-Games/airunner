"""Execution helpers for the automatic harness wrapper."""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from airunner_services.llm.long_running.auto_wrapper_feature_updates import (
    mark_feature_failure,
    mark_feature_in_progress,
    mark_feature_success,
)
from airunner_services.llm.long_running.task_detector import (
    TaskAnalysis,
    analyze_task,
)
from airunner_services.utils.application.log_hygiene import summarize_text


logger = logging.getLogger(__name__)


def wrap_and_execute(
    agent: Any,
    prompt: str,
    execute_fn: Callable[[str], dict[str, Any]],
    working_directory: Optional[str] = None,
) -> dict[str, Any]:
    """Wrap one prompt with harness behavior when warranted."""
    analysis = analyze_task(prompt)
    if not analysis.should_use_harness:
        return _execute_direct(prompt, execute_fn)
    project, features = _initialize_execution(
        agent, prompt, analysis, working_directory,
    )
    if not features:
        return _execute_single_complex_task(agent, prompt, execute_fn, project.id)
    results = _execute_features(agent, features, prompt, analysis, execute_fn, project)
    agent._mark_project_complete(project.id)
    return agent._aggregate_results(results, analysis, project)


def _execute_direct(
    prompt: str,
    execute_fn: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    """Execute one simple task without harness wrapping."""
    logger.debug(
        "Simple task, executing directly (%s)",
        summarize_text(prompt, label="prompt"),
    )
    return execute_fn(prompt)


def _initialize_execution(
    agent: Any,
    prompt: str,
    analysis: TaskAnalysis,
    working_directory: Optional[str],
) -> tuple[Any, list[Any]]:
    """Create the project and initial features for one wrapped task."""
    logger.info(
        "Complex task detected (%s): %s",
        analysis.task_type.value,
        analysis.reason,
    )
    project = agent._create_project_for_task(prompt, analysis, working_directory)
    agent._current_project_id = project.id
    agent._emit_progress(f"Project '{project.name}'", "created", 0.0)
    features = agent._create_features_from_analysis(project.id, analysis, prompt)
    return project, features


def _execute_single_complex_task(
    agent: Any,
    prompt: str,
    execute_fn: Callable[[str], dict[str, Any]],
    project_id: int,
) -> dict[str, Any]:
    """Execute one wrapped task without decomposed features."""
    logger.info("No specific features detected, executing as single task")
    result = execute_fn(prompt)
    agent._mark_project_complete(project_id)
    return result


def _execute_features(
    agent: Any, features: list[Any], prompt: str,
    analysis: TaskAnalysis,
    execute_fn: Callable[[str], dict[str, Any]],
    project: Any,
) -> list[dict[str, Any]]:
    """Execute all decomposed features for one wrapped task."""
    results: list[dict[str, Any]] = []
    total_features = len(features)
    for index, feature in enumerate(features):
        result = _run_feature(agent, feature, index, total_features, prompt,
                              analysis, execute_fn, project.id)
        if result is not None:
            results.append(result)
    return results


def _run_feature(
    agent: Any,
    feature: Any,
    index: int,
    total_features: int,
    prompt: str,
    analysis: TaskAnalysis,
    execute_fn: Callable[[str], dict[str, Any]],
    project_id: int,
) -> Optional[dict[str, Any]]:
    """Execute one decomposed feature with progress tracking."""
    mark_feature_in_progress(agent, feature, index, total_features)
    sub_prompt = agent._create_sub_prompt(prompt, feature, analysis)
    try:
        result = execute_fn(sub_prompt)
    except Exception as error:
        mark_feature_failure(agent, feature, error, project_id)
        return None
    mark_feature_success(agent, feature, index, total_features, project_id)
    return result


# Execution orchestration lives here, while naming, prompting, and persistence
# helpers stay in adjacent modules.
# That split keeps the wrapper entrypoint focused on task flow.
# The result aggregation boundary also stays outside this module on purpose.
# Keeping that separation makes failure handling easier to reason about.
# MI note: this helper stays intentionally narrow and delegated.
# MI note: related orchestration lives in neighboring long_running modules.
