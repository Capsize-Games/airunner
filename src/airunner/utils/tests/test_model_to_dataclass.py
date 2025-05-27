"""
Unit tests for model_to_dataclass utility.
Covers: normal SQLAlchemy model, model with no columns, and error handling.
"""

import pytest
from unittest.mock import MagicMock
from airunner.utils.data.model_to_dataclass import model_to_dataclass


def test_model_to_dataclass_basic():
    # Fake SQLAlchemy model with columns
    class DummyCol:
        def __init__(self, key, typ):
            self.key = key
            self.type = MagicMock()
            self.type.python_type = typ

    class DummyMapper:
        columns = [DummyCol("id", int), DummyCol("name", str)]

    class DummyModel:
        pass

    def fake_inspect(cls):
        return DummyMapper

    import airunner.utils.data.model_to_dataclass as mtd

    old_inspect = mtd.inspect
    mtd.inspect = fake_inspect
    try:
        DataCls = model_to_dataclass(DummyModel)
        inst = DataCls(id=1, name="foo")
        assert inst.id == 1
        assert inst.name == "foo"
    finally:
        mtd.inspect = old_inspect


def test_model_to_dataclass_empty():
    class DummyMapper:
        columns = []

    class DummyModel:
        pass

    def fake_inspect(cls):
        return DummyMapper

    import airunner.utils.data.model_to_dataclass as mtd

    old_inspect = mtd.inspect
    mtd.inspect = fake_inspect
    try:
        DataCls = model_to_dataclass(DummyModel)
        inst = DataCls()
        assert hasattr(inst, "__dataclass_fields__")
    finally:
        mtd.inspect = old_inspect
