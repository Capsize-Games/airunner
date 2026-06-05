"""Feature-record helpers for initializer-agent project creation."""

from __future__ import annotations

from typing import Any

from airunner_services.database.models.project_state import FeatureCategory


def create_feature_records(
    agent: Any,
    project_id: int,
    features_data: list[dict[str, Any]],
) -> dict[str, int]:
    """Create features without dependencies and return their IDs."""
    feature_ids: dict[str, int] = {}
    for feature_data in features_data:
        feature = agent._project_manager.add_feature(
            project_id=project_id,
            name=feature_data["name"],
            description=feature_data.get("description", ""),
            category=FeatureCategory(
                feature_data.get("category", "functional")
            ),
            verification_steps=feature_data.get("verification_steps", []),
            priority=feature_data.get("priority", 5),
            depends_on=[],
        )
        feature_ids[feature_data["name"]] = feature.id
    return feature_ids


def dependency_ids(
    depends_on_names: list[str],
    feature_ids: dict[str, int],
) -> list[int]:
    """Return known dependency IDs for one feature."""
    return [
        feature_ids[name] for name in depends_on_names if name in feature_ids
    ]


def update_feature_dependencies(
    agent: Any,
    features_data: list[dict[str, Any]],
    feature_ids: dict[str, int],
) -> None:
    """Update dependencies for all created features."""
    for feature_data in features_data:
        feature_id = feature_ids.get(feature_data["name"])
        if feature_id is None:
            continue
        depends_on = dependency_ids(
            feature_data.get("depends_on_names", []),
            feature_ids,
        )
        if depends_on:
            set_feature_dependencies(agent, feature_id, depends_on)


def set_feature_dependencies(
    agent: Any,
    feature_id: int,
    depends_on: list[int],
) -> None:
    """Persist dependency IDs for one feature."""
    feature = agent._project_manager.get_feature(feature_id)
    if feature is not None:
        feature.depends_on = depends_on


# Feature creation and dependency wiring are split here so initializer runs can
# reuse the same record-building steps.
# The project-level transaction logic remains in the neighboring module.
