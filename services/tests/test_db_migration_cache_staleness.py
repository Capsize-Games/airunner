"""Regression tests: the migration-heads cache must track script changes.

A rewritten/new migration script must invalidate the cached heads, a stale
cache entry must never be reused, and a database behind the scripts must
not be reported as up to date.
"""

from __future__ import annotations

import json
import os
import time

import pytest

import importlib as _importlib

setup_db_mod = _importlib.import_module(
    "airunner_services.database.setup_database"
)


@pytest.fixture()
def isolated_cache(tmp_path, monkeypatch):
    """Point the heads cache at a temp ``AIRUNNER_BASE_PATH``."""
    monkeypatch.setattr(setup_db_mod, "AIRUNNER_BASE_PATH", str(tmp_path))
    return tmp_path


def _layout(tmp_path, contents: dict[str, str]):
    base = tmp_path / "migrations"
    versions = base / "versions"
    versions.mkdir(parents=True)
    for name, body in contents.items():
        (versions / name).write_text(body, encoding="utf-8")
    return base, [versions]


def test_signature_changes_when_script_content_changes(tmp_path) -> None:
    """Editing a migration file invalidates the cached signature."""
    base, locations = _layout(tmp_path, {"a1.py": "x = 1\n"})
    before = setup_db_mod._migration_signature(locations, base)
    time.sleep(0.01)
    (locations[0] / "a1.py").write_text("x = 2\n", encoding="utf-8")
    after = setup_db_mod._migration_signature(locations, base)
    assert before != after


def test_signature_changes_when_script_added(tmp_path) -> None:
    """A new migration file invalidates the cached signature."""
    base, locations = _layout(tmp_path, {"a1.py": "x = 1\n"})
    before = setup_db_mod._migration_signature(locations, base)
    (locations[0] / "a2.py").write_text("y = 2\n", encoding="utf-8")
    after = setup_db_mod._migration_signature(locations, base)
    assert before != after


def test_content_only_change_same_size_same_mtime_detected(tmp_path) -> None:
    """A same-size rewrite with a frozen mtime must still invalidate.

    mtime+size alone cannot prove content is unchanged; a content-aware
    signature (hash) must catch this.
    """
    base, locations = _layout(tmp_path, {"a1.py": "aaa\n"})
    before = setup_db_mod._migration_signature(locations, base)
    target = locations[0] / "a1.py"
    frozen = os.stat(target)
    target.write_text("bbb\n", encoding="utf-8")
    os.utime(
        target, ns=(frozen.st_atime_ns, frozen.st_mtime_ns)
    )
    after = setup_db_mod._migration_signature(locations, base)
    assert before != after


def test_stale_signature_cache_entry_is_ignored(
    isolated_cache, tmp_path
) -> None:
    """A cache entry stored under an old signature must not be reused."""
    base, locations = _layout(tmp_path, {"a1.py": "x = 1\n"})
    current = setup_db_mod._migration_signature(locations, base)
    setup_db_mod._write_cached_migration_heads("stale-signature", ("head-a",))
    assert setup_db_mod._read_cached_migration_heads(current) == ()


def test_corrupt_cache_payload_is_ignored(isolated_cache) -> None:
    """An unreadable cache file must behave as a cache miss, not a crash."""
    cache_path = setup_db_mod._migration_heads_cache_path()
    cache_path.write_text("{not-json", encoding="utf-8")
    assert setup_db_mod._read_cached_migration_heads("anything") == ()


def test_db_behind_scripts_is_not_at_head(monkeypatch) -> None:
    """A database whose heads differ from the scripts is not current."""
    monkeypatch.setattr(
        setup_db_mod,
        "_cached_expected_migration_heads",
        lambda *a, **k: ("new-head",),
    )
    monkeypatch.setattr(
        setup_db_mod,
        "_current_database_heads",
        lambda *a, **k: ("old-head",),
    )
    assert (
        setup_db_mod._database_is_at_head(object(), "db-url", [], None)
        is False
    )


def test_db_matching_scripts_is_at_head(monkeypatch) -> None:
    """Equal heads mean the database is current — no upgrade needed."""
    monkeypatch.setattr(
        setup_db_mod,
        "_cached_expected_migration_heads",
        lambda *a, **k: ("head-a",),
    )
    monkeypatch.setattr(
        setup_db_mod,
        "_current_database_heads",
        lambda *a, **k: ("head-a",),
    )
    assert (
        setup_db_mod._database_is_at_head(object(), "db-url", [], None)
        is True
    )


def test_round_trip_cache_hit(isolated_cache, tmp_path) -> None:
    """A write under the current signature must be readable back."""
    base, locations = _layout(tmp_path, {"a1.py": "x = 1\n"})
    signature = setup_db_mod._migration_signature(locations, base)
    setup_db_mod._write_cached_migration_heads(signature, ("head-a",))
    assert setup_db_mod._read_cached_migration_heads(signature) == ("head-a",)
