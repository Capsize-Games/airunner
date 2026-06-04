"""Next-feature selection for the long-running project manager."""

from __future__ import annotations

from typing import Any, Optional

from airunner_services.database.models.project_state import ProjectFeature
from airunner_services.database.session import session_scope
from airunner_services.llm.long_running.project_manager_feature_dependency import (
    _next_not_started_feature,
    _retry_feature,
)
from airunner_services.llm.long_running.project_manager_feature_query import (
    _in_progress_feature,
    _project_features,
)


def get_next_feature_to_work_on(
    manager: Any,
    project_id: int,
) -> Optional[ProjectFeature]:
    """Return the next feature that should be worked on."""
    with session_scope() as db:
        feature = _in_progress_feature(db, project_id)
        if feature is None:
            features = _project_features(db, project_id)
            feature = _next_not_started_feature(features) or _retry_feature(features)
        return manager._detach(db, feature)