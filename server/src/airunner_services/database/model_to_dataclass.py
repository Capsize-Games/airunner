"""Generate dataclasses from SQLAlchemy model classes.

Used by ``BaseModel.to_dataclass()`` to produce a plain-data
representation of an ORM instance that can safely cross process
boundaries (e.g. returned by the HTTP bridge).
"""

from __future__ import annotations

from dataclasses import make_dataclass, field
from sqlalchemy.inspection import inspect


def model_to_dataclass(model_cls):
    """Dynamically generate a dataclass for one SQLAlchemy model."""
    mapper = inspect(model_cls)
    dataclass_fields = [
        (column.key, column.type.python_type, None)
        for column in mapper.columns
    ]
    # Special-case for Chatbot: add relationship fields as optional
    if model_cls.__name__ == "Chatbot":
        dataclass_fields.append(
            ("target_files", list, field(default_factory=list))
        )
        dataclass_fields.append(
            ("target_directories", list, field(default_factory=list))
        )
    return make_dataclass(model_cls.__name__ + "Data", dataclass_fields)


__all__ = ["model_to_dataclass"]
