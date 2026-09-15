"""Reporting helpers for the long-running harness."""

from __future__ import annotations

from typing import Any

from airunner_services.llm.long_running.harness_reporting_sections import (
    decision_section,
    feature_section,
    git_section,
    progress_section,
    report_header,
)


def export_project_report(agent: Any, project_id: int) -> str:
    """Export a comprehensive project report."""
    project = agent._project_manager.get_project(project_id)
    if project is None:
        return "# Error: Project not found"
    features = agent._project_manager.get_project_features(project_id)
    progress_log = agent._project_manager.get_progress_log(project_id, 50)
    git_log = agent._project_manager.get_git_log(project_id, 20)
    decisions = agent._project_manager.get_relevant_decisions(project_id, limit=20)
    lines = report_header(project)
    lines.extend(feature_section(features))
    lines.extend(progress_section(progress_log))
    lines.extend(git_section(git_log))
    lines.extend(decision_section(decisions))
    return "\n".join(lines)