from dataclasses import make_dataclass
from sqlalchemy.inspection import inspect


def model_to_dataclass(model_cls):
    """Dynamically generate a dataclass for a SQLAlchemy model."""
    mapper = inspect(model_cls)
    dataclass_fields = [
        (column.key, column.type.python_type, None)
        for column in mapper.columns
    ]
    return make_dataclass(model_cls.__name__ + "Data", dataclass_fields)
