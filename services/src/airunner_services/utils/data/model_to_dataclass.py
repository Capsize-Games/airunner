"""Dataclass conversion helpers for service-owned ORM models."""

from dataclasses import field, make_dataclass

from sqlalchemy.inspection import inspect


def model_to_dataclass(model_cls):
    """Dynamically generate one dataclass for one SQLAlchemy model."""
    mapper = inspect(model_cls)
    dataclass_fields = [
        (column.key, column.type.python_type, None)
        for column in mapper.columns
    ]
    if model_cls.__name__ == "Chatbot":
        dataclass_fields.append(
            ("target_files", list, field(default_factory=list))
        )
        dataclass_fields.append(
            ("target_directories", list, field(default_factory=list))
        )
    return make_dataclass(model_cls.__name__ + "Data", dataclass_fields)


__all__ = ["model_to_dataclass"]
