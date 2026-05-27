"""GUI-owned model re-exports."""

import airunner.models as _models

# Re-export every model class that used to live here.
for _name in _models.__all__:
    _obj = getattr(_models, _name, None)
    if _obj is not None:
        globals()[_name] = _obj

# Build the classes list + table_to_class dict (used by persistence route).
classes = [
    getattr(_models, name)
    for name in _models.__all__
    if hasattr(getattr(_models, name, None), "__tablename__")
]
class_names = list(_models.__all__)
table_to_class = {
    cls.__tablename__: cls
    for cls in classes
}
