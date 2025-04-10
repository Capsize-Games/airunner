import os
from alembic.config import Config
from alembic import command
from pathlib import Path


def setup_database():
    base = Path(os.path.dirname(os.path.realpath(__file__)))
    alembic_file = base / "alembic.ini"
    alembic_dir = base / "alembic"
    alembic_cfg = Config(alembic_file)
    alembic_cfg.set_main_option("script_location", str(alembic_dir))
    command.upgrade(alembic_cfg, "head")
