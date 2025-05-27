"""
Tests for airunner.utils.db.column
Covers all public functions, error handling, and edge cases.
All DB/model/engine dependencies are mocked. No real DB is touched.
"""

import pytest
from unittest.mock import MagicMock, patch, call
import sqlalchemy as sa

import airunner.utils.db.column as dbcol


class DummyModel:
    __tablename__ = "dummy"
    __table__ = MagicMock()
    col1 = sa.Column("col1", sa.Integer)
    col2 = sa.Column("col2", sa.String)
    col3 = sa.Column("col3", sa.Integer)
    __table__.columns.keys.return_value = ["col1", "col2", "col3"]


def test_get_columns():
    inspector = MagicMock()
    inspector.get_columns.return_value = [
        {"name": "col1"},
        {"name": "col2"},
        {"name": "col3"},
    ]
    with patch("airunner.utils.db.column.get_inspector", return_value=inspector):
        cols = dbcol.get_columns(DummyModel)
        assert cols == ["col1", "col2", "col3"]


def test_column_exists_true_false():
    with patch("airunner.utils.db.column.get_columns", return_value=["col1", "col2"]):
        assert dbcol.column_exists(DummyModel, "col1")
        assert not dbcol.column_exists(DummyModel, "col3")


def test_add_column_adds_and_skips(capfd):
    with patch(
        "airunner.utils.db.column.column_exists", return_value=False
    ), patch.object(DummyModel, "__table__") as table_mock, patch(
        "airunner.utils.db.column.op"
    ) as op_mock:
        table_mock.columns.keys.return_value = ["col1", "col2"]
        setattr(DummyModel, "col1", sa.Column("col1", sa.Integer))
        dbcol.add_column(DummyModel, "col1")
        op_mock.add_column.assert_called_once()
    # Already exists
    with patch(
        "airunner.utils.db.column.column_exists", return_value=True
    ), patch.object(DummyModel, "__table__") as table_mock, patch(
        "airunner.utils.db.column.op"
    ) as op_mock:
        table_mock.columns.keys.return_value = ["col1", "col2"]
        dbcol.add_column(DummyModel, "col1")
        out, _ = capfd.readouterr()
        assert "already exists" in out


def test_add_columns_calls_add_column():
    with patch("airunner.utils.db.column.add_column") as add_col:
        dbcol.add_columns(DummyModel, ["col1", "col2"])
        add_col.assert_has_calls([call(DummyModel, "col1"), call(DummyModel, "col2")])


def test_drop_column_drops_and_skips(capfd):
    inspector = MagicMock()
    inspector.get_foreign_keys.return_value = [
        {"constrained_columns": ["col1"], "name": "fk1"},
        {"constrained_columns": ["col2"]},
    ]
    with patch("airunner.utils.db.column.column_exists", return_value=True), patch(
        "airunner.utils.db.column.get_inspector", return_value=inspector
    ), patch("airunner.utils.db.column.op.batch_alter_table") as batch_alter:
        batch_op = MagicMock()
        batch_alter.return_value.__enter__.return_value = batch_op
        dbcol.drop_column(DummyModel, "col1")
        batch_op.drop_constraint.assert_called_with("fk1", type_="foreignkey")
        batch_op.drop_column.assert_called_with("col1")
    # Not exists
    with patch("airunner.utils.db.column.column_exists", return_value=False), patch(
        "airunner.utils.db.column.get_inspector", return_value=inspector
    ), patch("airunner.utils.db.column.op.batch_alter_table") as batch_alter:
        dbcol.drop_column(DummyModel, "colX")
        out, _ = capfd.readouterr()
        assert "does not exist" in out


def test_drop_column_prints_for_unnamed_fk(capfd):
    inspector = MagicMock()
    inspector.get_foreign_keys.return_value = [
        {"constrained_columns": ["col1"], "name": None}
    ]
    with patch("airunner.utils.db.column.column_exists", return_value=True), patch(
        "airunner.utils.db.column.get_inspector", return_value=inspector
    ), patch("airunner.utils.db.column.op.batch_alter_table") as batch_alter:
        batch_op = MagicMock()
        batch_alter.return_value.__enter__.return_value = batch_op
        dbcol.drop_column(DummyModel, "col1")
        out, _ = capfd.readouterr()
        assert "Skipping unnamed foreign key constraint" in out


def test_drop_columns_calls_drop_column():
    with patch("airunner.utils.db.column.drop_column") as drop_col:
        dbcol.drop_columns(DummyModel, ["col1", "col2"])
        drop_col.assert_has_calls([call(DummyModel, "col1"), call(DummyModel, "col2")])


def test_alter_column_type_change_and_skip(capfd):
    col_a = sa.Column("col1", sa.Integer)
    col_b = sa.Column("col1", sa.String)
    # Type is different: should alter
    with patch.object(DummyModel, "col1", col_a), patch(
        "airunner.utils.db.column.op.batch_alter_table"
    ) as batch_alter:
        batch_op = MagicMock()
        batch_alter.return_value.__enter__.return_value = batch_op
        dbcol.alter_column(DummyModel, col_a, col_b)
        batch_op.alter_column.assert_called_once()
    # Type is same: should skip
    col_b2 = sa.Column("col1", sa.Integer)
    # Patch the type attribute to ensure the equality branch is hit
    with patch.object(DummyModel, "col1", col_a), patch.object(
        col_b2, "type", col_a.type
    ), patch("airunner.utils.db.column.op.batch_alter_table") as batch_alter, patch(
        "builtins.print"
    ) as print_mock:
        dbcol.alter_column(DummyModel, col_a, col_b2)
        print_mock.assert_called()


def test_add_column_with_fk():
    with patch("airunner.utils.db.column.column_exists", return_value=False), patch(
        "airunner.utils.db.column.op.batch_alter_table"
    ) as batch_alter:
        batch_op = MagicMock()
        batch_alter.return_value.__enter__.return_value = batch_op
        dbcol.add_column_with_fk(
            DummyModel, "col4", sa.Integer, "other", "id", "fk_col4"
        )
        batch_op.add_column.assert_called_once()
        batch_op.create_foreign_key.assert_called_once_with(
            "fk_col4", "other", ["col4"], ["id"]
        )


def test_drop_column_with_fk():
    inspector = MagicMock()
    inspector.get_foreign_keys.return_value = [{"name": "fk_col4"}]
    with patch("airunner.utils.db.column.column_exists", return_value=True), patch(
        "airunner.utils.db.column.get_inspector", return_value=inspector
    ), patch("airunner.utils.db.column.op.batch_alter_table") as batch_alter:
        batch_op = MagicMock()
        batch_alter.return_value.__enter__.return_value = batch_op
        dbcol.drop_column_with_fk(DummyModel, "col4", "fk_col4")
        batch_op.drop_constraint.assert_called_once_with("fk_col4", type_="foreignkey")
        batch_op.drop_column.assert_called_once_with("col4")
    # Not exists
    with patch("airunner.utils.db.column.column_exists", return_value=False), patch(
        "airunner.utils.db.column.get_inspector", return_value=inspector
    ), patch("airunner.utils.db.column.op.batch_alter_table") as batch_alter, patch(
        "builtins.print"
    ) as print_mock:
        dbcol.drop_column_with_fk(DummyModel, "colX", "fk_colX")
        print_mock.assert_called()


def test_safe_alter_column_and_error(capfd):
    with patch("airunner.utils.db.column.column_exists", return_value=True), patch(
        "airunner.utils.db.column.op.batch_alter_table"
    ) as batch_alter:
        batch_op = MagicMock()
        batch_alter.return_value.__enter__.return_value = batch_op
        dbcol.safe_alter_column(
            DummyModel,
            "col1",
            new_type=sa.String(),
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.alter_column.assert_called_once()
    # Not exists
    with patch("airunner.utils.db.column.column_exists", return_value=False):
        dbcol.safe_alter_column(DummyModel, "colX")
        out, _ = capfd.readouterr()
        assert "does not exist" in out
    # Simulate OperationalError
    with patch("airunner.utils.db.column.column_exists", return_value=True), patch(
        "airunner.utils.db.column.op.batch_alter_table",
        side_effect=sa.exc.OperationalError("stmt", {}, Exception()),
    ), patch("builtins.print") as print_mock:
        dbcol.safe_alter_column(DummyModel, "col1")
        print_mock.assert_called()


def test_safe_alter_column_server_default():
    with patch("airunner.utils.db.column.column_exists", return_value=True), patch(
        "airunner.utils.db.column.op.batch_alter_table"
    ) as batch_alter:
        batch_op = MagicMock()
        batch_alter.return_value.__enter__.return_value = batch_op
        dbcol.safe_alter_column(
            DummyModel,
            "col1",
            new_type=sa.String(),
            existing_type=sa.Integer(),
            nullable=True,
            existing_server_default="foo",
        )
        batch_op.alter_column.assert_called_once()
        # Should include server_default in options
        args, kwargs = batch_op.alter_column.call_args
        assert "server_default" in kwargs


def test_safe_alter_columns():
    with patch("airunner.utils.db.column.safe_alter_column") as safe_alter:
        col = sa.Column("col1", sa.Integer)
        dbcol.safe_alter_columns(DummyModel, [col])
        safe_alter.assert_called_once_with(
            DummyModel, "col1", col.type, col.type, col.nullable
        )


def test_set_default_and_create_fk():
    with patch("airunner.utils.db.column.op.execute") as op_exec, patch(
        "airunner.utils.db.column.safe_alter_column"
    ) as safe_alter:
        dbcol.set_default_and_create_fk("table", "col", "ref_table", "ref_col", 42)
        op_exec.assert_called()
        safe_alter.assert_called()


def test_set_default():
    with patch("airunner.utils.db.column.safe_alter_column") as safe_alter:
        dbcol.set_default(DummyModel, "col1", 7)
        safe_alter.assert_called_once()


def test_create_unique_constraint_and_error():
    with patch("airunner.utils.db.column.op.batch_alter_table") as batch_alter:
        batch_op = MagicMock()
        batch_alter.return_value.__enter__.return_value = batch_op
        dbcol.create_unique_constraint(DummyModel, ["col1"], "uq_col1")
        batch_op.create_unique_constraint.assert_called_once_with("uq_col1", ["col1"])
    # OperationalError
    with patch(
        "airunner.utils.db.column.op.batch_alter_table",
        side_effect=sa.exc.OperationalError("stmt", {}, Exception()),
    ), patch("builtins.print") as print_mock:
        dbcol.create_unique_constraint(DummyModel, ["col1"], "uq_col1")
        print_mock.assert_called()
    # NotImplementedError
    with patch(
        "airunner.utils.db.column.op.batch_alter_table",
        side_effect=NotImplementedError("sqlite"),
    ), patch("builtins.print") as print_mock:
        dbcol.create_unique_constraint(DummyModel, ["col1"], "uq_col1")
        print_mock.assert_called()


def test_drop_constraint_and_error():
    with patch("airunner.utils.db.column.op.batch_alter_table") as batch_alter:
        batch_op = MagicMock()
        batch_alter.return_value.__enter__.return_value = batch_op
        dbcol.drop_constraint(DummyModel, "uq_col1")
        batch_op.drop_constraint.assert_called_once_with("uq_col1", type_="unique")
    # OperationalError
    with patch(
        "airunner.utils.db.column.op.batch_alter_table",
        side_effect=sa.exc.OperationalError("stmt", {}, Exception()),
    ), patch("builtins.print") as print_mock:
        dbcol.drop_constraint(DummyModel, "uq_col1")
        print_mock.assert_called()
    # NotImplementedError
    with patch(
        "airunner.utils.db.column.op.batch_alter_table",
        side_effect=NotImplementedError("sqlite"),
    ), patch("builtins.print") as print_mock:
        dbcol.drop_constraint(DummyModel, "uq_col1")
        print_mock.assert_called()
