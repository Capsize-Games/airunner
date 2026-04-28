"""Tests for the shared local-runtime boundary helpers."""

from __future__ import annotations

from pathlib import Path

from airunner.runtime_layout import (
    DEFAULT_RUNTIME_HOST,
    build_runtime_directory_layout,
    resolve_runtime_bind_host,
)
from airunner.services.daemon_config import DaemonConfig
from airunner.services.service_manager import LinuxSystemdHandler


def test_build_runtime_directory_layout_uses_standard_subdirectories(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("AIRUNNER_BASE_PATH", str(tmp_path))

    layout = build_runtime_directory_layout()

    assert layout.runtime_root == tmp_path / "runtime"
    assert layout.config_dir == tmp_path / "runtime" / "configs"
    assert layout.log_dir == tmp_path / "runtime" / "logs"
    assert layout.socket_dir == tmp_path / "runtime" / "sockets"
    assert layout.cache_dir == tmp_path / "cache"
    assert layout.model_dir == tmp_path / "models"


def test_resolve_runtime_bind_host_stays_loopback_by_default(monkeypatch):
    monkeypatch.setenv("AIRUNNER_RUNTIME_BIND_HOST", "0.0.0.0")
    monkeypatch.delenv("AIRUNNER_ALLOW_REMOTE_RUNTIME_BIND", raising=False)

    resolved = resolve_runtime_bind_host("AIRUNNER_RUNTIME_BIND_HOST")

    assert resolved == DEFAULT_RUNTIME_HOST


def test_resolve_runtime_bind_host_allows_explicit_remote_override(
    monkeypatch,
):
    monkeypatch.setenv("AIRUNNER_RUNTIME_BIND_HOST", "0.0.0.0")
    monkeypatch.setenv("AIRUNNER_ALLOW_REMOTE_RUNTIME_BIND", "1")

    resolved = resolve_runtime_bind_host("AIRUNNER_RUNTIME_BIND_HOST")

    assert resolved == "0.0.0.0"


def test_daemon_config_defaults_to_runtime_layout(monkeypatch, tmp_path):
    monkeypatch.setenv("AIRUNNER_BASE_PATH", str(tmp_path))

    config = DaemonConfig()

    assert config.config_path == tmp_path / "runtime" / "configs" / "daemon.yaml"
    assert config.config["logging"]["file"] == str(
        tmp_path / "runtime" / "logs" / "daemon.log"
    )
    assert config.config["runtime"]["socket_dir"] == str(
        tmp_path / "runtime" / "sockets"
    )


def test_linux_systemd_service_content_includes_runtime_boundary(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("AIRUNNER_BASE_PATH", str(tmp_path))
    handler = LinuxSystemdHandler()
    config_path = tmp_path / "runtime" / "configs" / "daemon.yaml"

    content = handler._generate_service_content("python -m airunner.services.daemon", config_path)

    assert "AIRUNNER_RUNTIME_ROOT" in content
    assert "AIRUNNER_RUNTIME_BIND_HOST=127.0.0.1" in content
    assert f"ExecStart=python -m airunner.services.daemon --config {config_path}" in content
    assert "NoNewPrivileges=yes" in content
    assert f"ReadWritePaths={tmp_path}" in content