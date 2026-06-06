"""Feature-selection facade for the long-running project manager."""

from airunner_services.llm.long_running.project_manager_feature_next import (
    get_next_feature_to_work_on,
)

__all__ = ["get_next_feature_to_work_on"]
