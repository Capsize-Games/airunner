"""Shared fixtures for the P07 upgrade regression suites."""

from __future__ import annotations

import sqlite3
from pathlib import Path

_HEAD_A = "p07fakehead0001"
_HEAD_B = "p07fakehead0002"


def _data_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    script = (
        "CREATE TABLE app_settings (k TEXT, v TEXT);"
        "CREATE TABLE conversations (id INTEGER, t TEXT);"
        "CREATE TABLE media_paths (id INTEGER, p TEXT);"
        "CREATE TABLE policy_prefs (k TEXT, v TEXT);"
        "CREATE TABLE alembic_version (version_num TEXT);"
        "INSERT INTO app_settings VALUES ('theme', 'dark');"
        "INSERT INTO conversations VALUES (1, 'hello');"
        "INSERT INTO media_paths VALUES (1, '/models/x');"
        "INSERT INTO policy_prefs VALUES ('mode', 'strict');"
        f"INSERT INTO alembic_version VALUES ('{_HEAD_A}');"
    )
    with sqlite3.connect(str(path)) as db:
        db.executescript(script)


def _rows(path: Path, table: str) -> int:
    with sqlite3.connect(str(path)) as db:
        return int(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
