"""Transitional API exports for the service-owned DB helper package."""

from importlib import import_module as _import_module

_db_module = _import_module("airunner_services.utils.db")
_bootstrap_module = _import_module("airunner_services.utils.db.bootstrap")
_engine_module = _import_module("airunner_services.utils.db.engine")

add_column = _db_module.add_column
add_column_with_fk = _db_module.add_column_with_fk
add_columns = _db_module.add_columns
add_table = _db_module.add_table
add_tables = _db_module.add_tables
alter_column = _db_module.alter_column
column_exists = _db_module.column_exists
create_foreign_key = _db_module.create_foreign_key
create_unique_constraint = _db_module.create_unique_constraint
drop_column = _db_module.drop_column
drop_column_with_fk = _db_module.drop_column_with_fk
drop_columns = _db_module.drop_columns
drop_constraint = _db_module.drop_constraint
drop_table = _db_module.drop_table
drop_tables = _db_module.drop_tables
get_columns = _db_module.get_columns
get_tables = _db_module.get_tables
safe_alter_column = _db_module.safe_alter_column
safe_alter_columns = _db_module.safe_alter_columns
set_default = _db_module.set_default
set_default_ai_models = _bootstrap_module.set_default_ai_models
set_default_and_create_fk = _db_module.set_default_and_create_fk
set_default_controlnet_models = _bootstrap_module.set_default_controlnet_models
set_default_font_settings = _bootstrap_module.set_default_font_settings
set_default_pipeline_values = _bootstrap_module.set_default_pipeline_values
set_default_prompt_templates = _bootstrap_module.set_default_prompt_templates
set_default_schedulers = _bootstrap_module.set_default_schedulers
set_default_shortcut_keys = _bootstrap_module.set_default_shortcut_keys
set_image_filter_settings = _bootstrap_module.set_image_filter_settings
table_exists = _db_module.table_exists
SQLITE_BUSY_TIMEOUT_MS = _engine_module.SQLITE_BUSY_TIMEOUT_MS
create_configured_engine = _engine_module.create_configured_engine
get_connection = _engine_module.get_connection
get_inspector = _engine_module.get_inspector

__all__ = [
	"SQLITE_BUSY_TIMEOUT_MS",
	"add_column",
	"add_column_with_fk",
	"add_columns",
	"add_table",
	"add_tables",
	"alter_column",
	"column_exists",
	"create_configured_engine",
	"create_foreign_key",
	"create_unique_constraint",
	"drop_column",
	"drop_column_with_fk",
	"drop_columns",
	"drop_constraint",
	"drop_table",
	"drop_tables",
	"get_columns",
	"get_connection",
	"get_inspector",
	"get_tables",
	"safe_alter_column",
	"safe_alter_columns",
	"set_default",
	"set_default_ai_models",
	"set_default_and_create_fk",
	"set_default_controlnet_models",
	"set_default_font_settings",
	"set_default_pipeline_values",
	"set_default_prompt_templates",
	"set_default_schedulers",
	"set_default_shortcut_keys",
	"set_image_filter_settings",
	"table_exists",
]