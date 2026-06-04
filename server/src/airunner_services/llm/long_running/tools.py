"""Thin export surface for long-running management tools."""

from airunner_services.llm.long_running.tools_creation import (
    create_long_running_project,
    initialize_project_features,
)
from airunner_services.llm.long_running.tools_status import (
    get_next_feature_to_work_on,
    get_project_progress_log,
    get_project_status,
    list_long_running_projects,
    list_project_features,
)
from airunner_services.llm.long_running.tools_update import (
    add_project_feature,
    log_project_progress,
    update_feature_status,
)


# Export list of tools
LONG_RUNNING_TOOLS = [
    create_long_running_project,
    initialize_project_features,
    get_project_status,
    list_project_features,
    get_project_progress_log,
    list_long_running_projects,
    add_project_feature,
    update_feature_status,
    log_project_progress,
    get_next_feature_to_work_on,
]
