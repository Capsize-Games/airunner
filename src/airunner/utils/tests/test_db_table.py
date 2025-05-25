"""
Tests for airunner.utils.db.table
Covers all public functions, error handling, and edge cases.
All DB/model/engine dependencies are mocked. No real DB is touched.
"""

import pytest
from unittest.mock import MagicMock, patch, call
import airunner.utils.db.table as dbtable


class DummyModel:
    __tablename__ = "dummy"
    __table__ = MagicMock()
    __table__.columns = [MagicMock(name="col1"), MagicMock(name="col2")]
    __table_args__ = ()


def test_get_tables():
    conn = MagicMock()
    inspector = MagicMock()
    inspector.get_table_names.return_value = ["foo", "bar"]
    with patch(
        "airunner.utils.db.table.op.get_bind", return_value=conn
    ), patch("airunner.utils.db.table.sa.inspect", return_value=inspector):
        tables = dbtable.get_tables()
        assert tables == ["foo", "bar"]


def test_table_exists_true_false():
    conn = MagicMock()
    inspector = MagicMock()
    inspector.get_table_names.return_value = ["foo", "bar"]
    with patch(
        "airunner.utils.db.table.op.get_bind", return_value=conn
    ), patch("airunner.utils.db.table.sa.inspect", return_value=inspector):
        assert dbtable.table_exists("foo")
        assert not dbtable.table_exists("baz")


def test_add_table_adds_and_skips(capfd):
    DummyModel.__table__.columns = [
        MagicMock(copy=MagicMock(return_value=MagicMock()))
    ]
    DummyModel.__table_args__ = ()
    # Table does not exist: should create
    with patch(
        "airunner.utils.db.table.table_exists", return_value=False
    ), patch("airunner.utils.db.table.op.create_table") as create_table:
        dbtable.add_table(DummyModel)
        create_table.assert_called_once()
    # Table exists: should print and skip
    with patch(
        "airunner.utils.db.table.table_exists", return_value=True
    ), patch("airunner.utils.db.table.op.create_table") as create_table:
        dbtable.add_table(DummyModel)
        out, _ = capfd.readouterr()
        assert "already exists" in out


def test_add_tables_calls_create_table_with_defaults():
    with patch("airunner.utils.db.table.create_table_with_defaults") as create:
        dbtable.add_tables([DummyModel, DummyModel])
        assert create.call_count == 2


def test_drop_table_drops_and_skips(capfd):
    # Table exists: should drop
    with patch(
        "airunner.utils.db.table.table_exists", return_value=True
    ), patch("airunner.utils.db.table.op.drop_table") as drop_table:
        dbtable.drop_table(DummyModel)
        drop_table.assert_called_once_with(DummyModel.__tablename__)
    # Table does not exist: should print and skip
    with patch(
        "airunner.utils.db.table.table_exists", return_value=False
    ), patch("airunner.utils.db.table.op.drop_table") as drop_table:
        dbtable.drop_table(DummyModel)
        out, _ = capfd.readouterr()
        assert "does not exist" in out


def test_drop_tables_calls_drop_table():
    with patch("airunner.utils.db.table.drop_table") as drop:
        dbtable.drop_tables([DummyModel, DummyModel])
        assert drop.call_count == 2


def test_create_table_with_defaults_success_and_exists(capfd):
    DummyModel.__table__.columns = [
        MagicMock(
            copy=MagicMock(return_value=MagicMock(default=None, name="col1"))
        )
    ]
    DummyModel.__table_args__ = ()
    # Table does not exist: should create and set defaults
    with patch(
        "airunner.utils.db.table.table_exists", return_value=False
    ), patch("airunner.utils.db.table.op.create_table") as create_table, patch(
        "airunner.utils.db.table.set_default_values"
    ) as set_defaults:
        dbtable.create_table_with_defaults(DummyModel)
        create_table.assert_called_once()
        set_defaults.assert_called_once_with(DummyModel)
    # Table exists: should print and skip
    with patch(
        "airunner.utils.db.table.table_exists", return_value=True
    ), patch("airunner.utils.db.table.op.create_table") as create_table, patch(
        "airunner.utils.db.table.set_default_values"
    ) as set_defaults:
        dbtable.create_table_with_defaults(DummyModel)
        out, _ = capfd.readouterr()
        assert "already exists" in out


def test_create_table_with_defaults_exception(capfd):
    DummyModel.__table__.columns = [
        MagicMock(
            copy=MagicMock(return_value=MagicMock(default=None, name="col1"))
        )
    ]
    DummyModel.__table_args__ = ()
    with patch(
        "airunner.utils.db.table.table_exists", return_value=False
    ), patch(
        "airunner.utils.db.table.op.create_table",
        side_effect=Exception("fail"),
    ):
        dbtable.create_table_with_defaults(DummyModel)
        out, _ = capfd.readouterr()
        assert "Failed to create table" in out


def test_set_default_values():
    col1 = MagicMock()
    col1.name = "foo"
    col1.default = MagicMock(arg=42)
    col2 = MagicMock()
    col2.name = "bar"
    col2.default = None
    DummyModel.__table__.columns = [col1, col2]
    with patch("airunner.utils.db.table.op.bulk_insert") as bulk:
        dbtable.set_default_values(DummyModel)
        bulk.assert_called_once_with(DummyModel.__table__, [{"foo": 42}])
