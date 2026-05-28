"""Feature-dependency helpers for the long-running project manager."""

from __future__ import annotations

from airunner_services.database.models.project_state import (
    FeatureStatus,
    ProjectFeature,
)


def _passing_feature_ids(features: list[ProjectFeature]) -> set[int]:
    """Return the ids of passing features."""
    return {
        feature.id
        for feature in features
        if feature.status == FeatureStatus.PASSING
    }


def _next_not_started_feature(
    features: list[ProjectFeature],
) -> ProjectFeature | None:
    """Return the highest-priority unblocked not-started feature."""
    passing_ids = _passing_feature_ids(features)
    for feature in sorted(features, key=lambda item: item.priority, reverse=True):
        dependencies = feature.depends_on or []
        is_ready = feature.status == FeatureStatus.NOT_STARTED
        if is_ready and all(dep_id in passing_ids for dep_id in dependencies):
            return feature
    return None


def _retry_feature(features: list[ProjectFeature]) -> ProjectFeature | None:
    """Return the failing feature with the fewest attempts."""
    failing = [
        feature
        for feature in features
        if feature.status == FeatureStatus.FAILING
    ]
    return min(failing, key=lambda item: item.attempts or 0) if failing else None


# Dependency checks stay separate from feature lookup so scheduling code can
# choose the next candidate without re-encoding status rules.
# Retry selection stays intentionally conservative by preferring fewer attempts.