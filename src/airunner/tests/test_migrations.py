import os
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Define a temporary in-memory SQLite database URL
TEST_AIRUNNER_DB_URL = "sqlite:///:memory:"


@pytest.fixture(scope="module")
def alembic_config():
    # Create a temporary Alembic configuration for testing
    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), '../alembic.ini'))
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_AIRUNNER_DB_URL)
    # Set the script location explicitly
    alembic_cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), '../alembic'))
    return alembic_cfg


@pytest.fixture(scope="module")
def connection(alembic_config):
    # Create an engine and connection to the temporary database
    engine = create_engine(TEST_AIRUNNER_DB_URL)
    connection = engine.connect()
    yield connection
    connection.close()


@pytest.fixture(scope="module")
def setup_database(connection, alembic_config):
    # Bind the connection to the Alembic configuration
    alembic_config.attributes['connection'] = connection
    command.upgrade(alembic_config, 'head')
    yield
    command.downgrade(alembic_config, '181e31f78151')


def test_migrations_up_down(setup_database, alembic_config):
    # Run migrations up to the latest version
    command.upgrade(alembic_config, 'head')
    # Run migrations down to the specific version
    command.downgrade(alembic_config, '181e31f78151')
    # Run migrations up to the latest version again
    command.upgrade(alembic_config, 'head')
