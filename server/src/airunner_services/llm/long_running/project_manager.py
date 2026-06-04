"""Project manager facade for long-running agent projects."""

from __future__ import annotations

from airunner_services.llm.long_running.project_manager_decision_ops import (
    get_relevant_decisions,
    record_decision,
    update_decision_outcome,
)
from airunner_services.llm.long_running.project_manager_detach import (
    detach,
    detach_all,
)
from airunner_services.llm.long_running.project_manager_feature_ops import (
    add_feature,
    add_features_bulk,
    get_feature,
    get_next_feature_to_work_on,
    get_project_features,
    update_feature_status,
)
from airunner_services.llm.long_running.project_manager_git_ops import (
    _git_commit,
    _init_git_repo,
    get_git_log,
    git_revert_to_commit,
)
from airunner_services.llm.long_running.project_manager_progress_ops import (
    get_progress_as_text,
    get_progress_log,
    log_progress,
)
from airunner_services.llm.long_running.project_manager_project_ops import (
    create_project,
    delete_project,
    get_project,
    get_project_by_name,
    list_projects,
    update_project_status,
)
from airunner_services.llm.long_running.project_manager_session_ops import (
    end_session,
    get_last_session,
    start_session,
)
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class ProjectManager:
    """Persistence facade for long-running agent projects."""

    def __init__(self) -> None:
        """Initialize the manager logger."""
        self._logger = logger

    _detach = staticmethod(detach)
    _detach_all = staticmethod(detach_all)

    create_project = create_project
    get_project = get_project
    get_project_by_name = get_project_by_name
    list_projects = list_projects
    update_project_status = update_project_status
    delete_project = delete_project

    add_feature = add_feature
    add_features_bulk = add_features_bulk
    get_feature = get_feature
    get_project_features = get_project_features
    get_next_feature_to_work_on = get_next_feature_to_work_on
    update_feature_status = update_feature_status

    start_session = start_session
    end_session = end_session
    get_last_session = get_last_session

    log_progress = log_progress
    get_progress_log = get_progress_log
    get_progress_as_text = get_progress_as_text

    record_decision = record_decision
    update_decision_outcome = update_decision_outcome
    get_relevant_decisions = get_relevant_decisions

    _init_git_repo = _init_git_repo
    _git_commit = _git_commit
    git_revert_to_commit = git_revert_to_commit
    get_git_log = get_git_log
