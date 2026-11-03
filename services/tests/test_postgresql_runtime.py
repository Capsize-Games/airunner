"""PostgreSQL native runtime configuration without loading a DBAPI."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

from airunner_services.database.db import engine as engine_module
from airunner_services.runtimes.postgresql_runtime import (
    PostgreSQLRuntimeError,
    configure_postgresql_runtime,
    normalize_postgresql_url,
)


def test_sqlite_does_not_change_postgresql_runtime_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("SASL_PATH", "/host/plugins")
    monkeypatch.setenv("PSYCOPG_IMPL", "binary")

    assert (
        configure_postgresql_runtime(
            f"sqlite:///{tmp_path / 'service.db'}",
            runtime_root=tmp_path / "runtime",
        )
        is None
    )
    assert os.environ["SASL_PATH"] == "/host/plugins"
    assert os.environ["PSYCOPG_IMPL"] == "binary"
    assert not (tmp_path / "runtime").exists()


def test_postgresql_uses_private_empty_plugin_path_and_pure_driver(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("SASL_PATH", "/usr/lib/x86_64-linux-gnu/sasl2")
    monkeypatch.setenv("PSYCOPG_IMPL", "binary")
    runtime_root = tmp_path / "private-runtime"

    plugin_path = configure_postgresql_runtime(
        "postgresql://db.example/service", runtime_root=runtime_root
    )

    assert plugin_path == runtime_root / "postgresql-runtime" / "sasl-empty"
    assert plugin_path.is_dir()
    assert not plugin_path.is_symlink()
    assert list(plugin_path.iterdir()) == []
    assert stat.S_IMODE(plugin_path.stat().st_mode) == 0o700
    assert os.environ["SASL_PATH"] == str(plugin_path)
    assert os.pathsep not in os.environ["SASL_PATH"]
    assert "=" not in os.environ["SASL_PATH"]
    assert os.environ["PSYCOPG_IMPL"] == "python"


def test_existing_plugin_symlink_is_rejected_without_replacing_inherited_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir(mode=0o700)
    host_plugins = tmp_path / "host-plugins"
    host_plugins.mkdir(mode=0o700)
    private_root = runtime_root / "postgresql-runtime"
    private_root.mkdir(mode=0o700)
    (private_root / "sasl-empty").symlink_to(
        host_plugins, target_is_directory=True
    )
    monkeypatch.setenv("SASL_PATH", str(host_plugins))

    with pytest.raises(PostgreSQLRuntimeError, match="symlink"):
        configure_postgresql_runtime(
            "postgresql+psycopg://db.example/service",
            runtime_root=runtime_root,
        )

    assert os.environ["SASL_PATH"] == str(host_plugins)


def test_shared_runtime_root_permissions_and_contents_are_unchanged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runtime_root = tmp_path / "shared-runtime"
    runtime_root.mkdir(mode=0o700)
    runtime_root.chmod(0o755)
    sibling = runtime_root / "daemon.heartbeat"
    sibling.write_text("owned by the existing runtime", encoding="utf-8")

    plugin_path = configure_postgresql_runtime(
        "postgresql://db.example/service", runtime_root=runtime_root
    )

    assert plugin_path == runtime_root / "postgresql-runtime" / "sasl-empty"
    assert stat.S_IMODE(runtime_root.stat().st_mode) == 0o755
    assert (
        sibling.read_text(encoding="utf-8") == "owned by the existing runtime"
    )
    assert stat.S_IMODE(plugin_path.parent.stat().st_mode) == 0o700


def test_symlink_runtime_ancestor_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    real_root = tmp_path / "real-runtime"
    real_root.mkdir(mode=0o700)
    alias = tmp_path / "runtime-alias"
    alias.symlink_to(real_root, target_is_directory=True)
    monkeypatch.setenv("SASL_PATH", "/host/plugins")

    with pytest.raises(PostgreSQLRuntimeError, match="contains a symlink"):
        configure_postgresql_runtime(
            "postgresql://db.example/service", runtime_root=alias
        )

    assert os.environ["SASL_PATH"] == "/host/plugins"
    assert not (real_root / "postgresql-runtime").exists()


def test_parent_traversal_runtime_root_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(PostgreSQLRuntimeError, match="parent traversal"):
        configure_postgresql_runtime(
            "postgresql://db.example/service",
            runtime_root=tmp_path / ".." / "outside",
        )


def test_nonempty_plugin_directory_is_rejected(
    tmp_path: Path,
) -> None:
    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir(mode=0o700)
    plugin_path = runtime_root / "postgresql-runtime" / "sasl-empty"
    plugin_path.parent.mkdir(mode=0o700)
    plugin_path.mkdir(mode=0o700)
    (plugin_path / "libsasl-digestmd5.so").write_bytes(b"fixture")

    with pytest.raises(PostgreSQLRuntimeError, match="must be empty"):
        configure_postgresql_runtime(
            "postgresql+psycopg://db.example/service",
            runtime_root=runtime_root,
        )


@pytest.mark.parametrize(
    ("real_id", "effective_id", "getter"),
    [
        (1000, 2000, "uid"),
        (1000, 2000, "gid"),
    ],
)
def test_setuid_or_setgid_execution_fails_before_environment_change(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    real_id: int,
    effective_id: int,
    getter: str,
) -> None:
    monkeypatch.setattr(os, f"get{getter}", lambda: real_id)
    monkeypatch.setattr(os, f"gete{getter}", lambda: effective_id)
    monkeypatch.setenv("SASL_PATH", "/host/plugins")
    monkeypatch.setenv("PSYCOPG_IMPL", "binary")

    with pytest.raises(PostgreSQLRuntimeError, match="equal real/effective"):
        configure_postgresql_runtime(
            "postgresql://db.example/service",
            runtime_root=tmp_path / "runtime",
        )

    assert os.environ["SASL_PATH"] == "/host/plugins"
    assert os.environ["PSYCOPG_IMPL"] == "binary"
    assert not (tmp_path / "runtime").exists()


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("postgresql://db.example/service", "postgresql+psycopg"),
        ("postgres://db.example/service", "postgresql+psycopg"),
        ("postgresql+psycopg2://db.example/service", "postgresql+psycopg2"),
        ("postgresql+psycopg://db.example/service", "postgresql+psycopg"),
        ("sqlite:///service.db", "sqlite"),
    ],
)
def test_postgresql_url_normalization_preserves_explicit_drivers(
    source: str, expected: str
) -> None:
    assert make_url(normalize_postgresql_url(source)).drivername == expected


def test_engine_factory_sets_runtime_before_sqlalchemy_can_load_a_driver(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runtime_root = tmp_path / "runtime"
    monkeypatch.setenv("AIRUNNER_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.setenv("SASL_PATH", "/host/plugins")
    monkeypatch.setenv("PSYCOPG_IMPL", "binary")
    calls: list[object] = []

    def create_engine_probe(url: object, **kwargs: object) -> object:
        calls.append(url)
        assert os.environ["SASL_PATH"] == str(
            runtime_root / "postgresql-runtime" / "sasl-empty"
        )
        assert os.environ["PSYCOPG_IMPL"] == "python"
        return object()

    monkeypatch.setattr(engine_module, "create_engine", create_engine_probe)

    engine = engine_module.create_configured_engine(
        "postgresql://db.example/service"
    )

    assert engine is not None
    assert len(calls) == 1
    assert make_url(calls[0]).drivername == "postgresql+psycopg"


def test_configured_engine_preserves_alembic_options_and_coercion():
    config = {
        "sqlalchemy.url": "sqlite://",
        "sqlalchemy.echo": "true",
        "sqlalchemy.pool_recycle": "12",
        "unrelated": "ignored",
    }
    original = dict(config)
    engine = engine_module.create_configured_engine_from_config(
        config, pool_recycle=23
    )
    try:
        assert engine.echo is True
        assert engine.pool._recycle == 23
        assert config == original
        with engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA busy_timeout").scalar() == 5000
    finally:
        engine.dispose()


def test_configured_engine_supports_custom_prefix(monkeypatch):
    observed = {}

    def factory(url, **kwargs):
        observed.update(url=url, **kwargs)
        return "configured"

    monkeypatch.setattr(engine_module, "create_configured_engine", factory)
    assert engine_module.create_configured_engine_from_config(
        {"db.url": "sqlite://", "db.echo": "false", "sqlalchemy.echo": "true"},
        prefix="db.",
    ) == "configured"
    assert observed == {"url": "sqlite://", "echo": "false", "_coerce_config": True}
