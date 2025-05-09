import os

from pathlib import Path

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from airunner.settings import AIRUNNER_DB_URL

config = context.config
config.set_main_option("sqlalchemy.url", AIRUNNER_DB_URL)

# Check if DB file exists
if AIRUNNER_DB_URL.__contains__("sqlite"):
    db_path = AIRUNNER_DB_URL.replace("sqlite:///", "")
    try:
        if not os.path.exists(db_path):
            print(f"Database file not found at {db_path}")
            # create the file
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            with open(db_path, "w") as f:
                pass
            print(f"Database file created at {db_path}")
    except Exception as e:
        print(f"Error checking DB path: {e}")

# Import your models here
from airunner.data.models.base import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Get the path to the alembic.ini file
config_file_path = Path(__file__).parent / "../alembic.ini"

# Set the config file name explicitly
config.config_file_name = str(config_file_path)

# Interpret the config file for Python logging
fileConfig(config.config_file_name)

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline():
    """Run migrations in 'offline' mode.
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.
    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=False,
        compare_server_default=False,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=False,
            compare_server_default=False,
        )

        with context.begin_transaction():
            context.run_migrations()
            connection.commit()
    print("Migrations completed successfully.")


if context.is_offline_mode():
    print("Running migrations offline...")
    run_migrations_offline()
else:
    print("Running migrations online...")
    run_migrations_online()
