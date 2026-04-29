"""Tests for repeated database setup caching."""

from __future__ import annotations

from pathlib import Path

import airunner.setup_database as setup_database_module


def _reset_setup_cache() -> None:
    """Clear cached setup state between tests."""
    setup_database_module._COMPLETED_SETUP_URLS.clear()


def test_setup_database_skips_repeated_upgrade(
    monkeypatch,
    tmp_path,
) -> None:
    """Repeated setup calls for the same URL should only migrate once."""
    calls: list[tuple[str, str]] = []
    db_url = f"sqlite:///{tmp_path / 'cache-test.sqlite'}"

    _reset_setup_cache()
    monkeypatch.delenv("AIRUNNER_DISABLE_DB_SETUP_CACHE", raising=False)
    monkeypatch.setattr(
        setup_database_module.command,
        "upgrade",
        lambda cfg, rev: calls.append(
            (cfg.get_main_option("sqlalchemy.url"), rev)
        ),
    )

    setup_database_module.setup_database(db_url)
    setup_database_module.setup_database(db_url)

    assert calls == [(db_url, "head")]


def test_setup_database_migrates_new_urls(
    monkeypatch,
    tmp_path,
) -> None:
    """Different database URLs should still run separate migrations."""
    calls: list[tuple[str, str]] = []
    first_url = f"sqlite:///{tmp_path / 'first.sqlite'}"
    second_url = f"sqlite:///{tmp_path / 'second.sqlite'}"

    _reset_setup_cache()
    monkeypatch.delenv("AIRUNNER_DISABLE_DB_SETUP_CACHE", raising=False)
    monkeypatch.setattr(
        setup_database_module.command,
        "upgrade",
        lambda cfg, rev: calls.append(
            (cfg.get_main_option("sqlalchemy.url"), rev)
        ),
    )

    setup_database_module.setup_database(first_url)
    setup_database_module.setup_database(second_url)

    assert calls == [(first_url, "head"), (second_url, "head")]


def test_setup_database_skips_upgrade_when_db_is_current(
    monkeypatch,
    tmp_path,
) -> None:
    """Persisted current-head databases should skip Alembic upgrade."""
    calls: list[tuple[str, str]] = []
    db_url = f"sqlite:///{tmp_path / 'current.sqlite'}"

    _reset_setup_cache()
    monkeypatch.delenv("AIRUNNER_DISABLE_DB_SETUP_CACHE", raising=False)
    monkeypatch.setattr(
        setup_database_module,
        "_database_is_at_head",
        lambda cfg, url, version_locations, base: True,
    )
    monkeypatch.setattr(
        setup_database_module.command,
        "upgrade",
        lambda cfg, rev: calls.append(
            (cfg.get_main_option("sqlalchemy.url"), rev)
        ),
    )

    setup_database_module.setup_database(db_url)

    assert calls == []
    assert db_url in setup_database_module._COMPLETED_SETUP_URLS


def test_database_is_at_head_compares_sorted_heads(monkeypatch) -> None:
    """Head comparison should ignore ordering differences."""
    monkeypatch.setattr(
        setup_database_module,
        "_cached_expected_migration_heads",
        lambda cfg, version_locations, base: ("a", "b"),
    )
    monkeypatch.setattr(
        setup_database_module,
        "_current_database_heads",
        lambda url: ("a", "b"),
    )

    assert setup_database_module._database_is_at_head(
        object(),
        "sqlite:///unused.sqlite",
        [],
        Path("."),
    )