from dataclasses import dataclass


@dataclass
class ScannedModel:
    """Represents a model found during scanning."""

    name: str
    path: str
    version: str
    category: str
    pipeline_action: str