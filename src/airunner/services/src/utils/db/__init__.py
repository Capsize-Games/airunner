"""Service-owned database migration helpers."""

from airunner_services.utils.db.column import add_column
from airunner_services.utils.db.column import add_column_with_fk
from airunner_services.utils.db.column import add_columns
from airunner_services.utils.db.column import alter_column
from airunner_services.utils.db.column import column_exists
from airunner_services.utils.db.column import create_unique_constraint
from airunner_services.utils.db.column import drop_column
from airunner_services.utils.db.column import drop_column_with_fk
from airunner_services.utils.db.column import drop_columns
from airunner_services.utils.db.column import drop_constraint
from airunner_services.utils.db.column import get_columns
from airunner_services.utils.db.column import safe_alter_column
from airunner_services.utils.db.column import safe_alter_columns
from airunner_services.utils.db.column import set_default
from airunner_services.utils.db.column import set_default_and_create_fk
from airunner_services.utils.db.foreign_key import create_foreign_key
from airunner_services.utils.db.table import add_table
from airunner_services.utils.db.table import add_tables
from airunner_services.utils.db.table import drop_table
from airunner_services.utils.db.table import drop_tables
from airunner_services.utils.db.table import get_tables
from airunner_services.utils.db.table import table_exists


__all__ = [
    "add_column",
    "add_column_with_fk",
    "add_columns",
    "add_table",
    "add_tables",
    "alter_column",
    "column_exists",
    "create_foreign_key",
    "create_unique_constraint",
    "drop_column",
    "drop_column_with_fk",
    "drop_columns",
    "drop_constraint",
    "drop_table",
    "drop_tables",
    "get_columns",
    "get_tables",
    "safe_alter_column",
    "safe_alter_columns",
    "set_default",
    "set_default_and_create_fk",
    "table_exists",
]
