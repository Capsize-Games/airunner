from dataclasses import make_dataclass, field
from sqlalchemy.inspection import inspect


def model_to_dataclass(model_cls):
    """Dynamically generate a dataclass for a SQLAlchemy model."""
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
