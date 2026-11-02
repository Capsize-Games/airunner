"""Operator-only Triton toolchain installation dispatch tests."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_daemon_install_option_exits_before_daemon_startup(monkeypatch, capsys):
    from airunner_services import daemon
    from airunner_services.art import triton_toolchain_installer

    calls = []
    destination = Path.home() / ".cache" / "airunner" / "chosen"
    monkeypatch.setattr(
        triton_toolchain_installer,
        "install_private_toolchain",
        lambda requested=None: calls.append(requested) or {
            "environment": {"TRITON_PTXAS_PATH": str(destination / "bin/ptxas")}
        },
    )
    monkeypatch.setattr(
        daemon,
        "AIRunnerDaemon",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("daemon startup must not run for installer command")
        ),
    )

    daemon.main(["--install-triton-toolchain", "--triton-toolchain-dir", str(destination)])

    assert calls == [destination]
    assert "Private Triton toolchain staged" in capsys.readouterr().out


def test_destination_flag_requires_explicit_installer_command(monkeypatch):
    from airunner_services import daemon

    try:
        daemon.main(["--triton-toolchain-dir", "/tmp/toolchain"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("destination-only invocation must be rejected")


def test_installed_package_resources_match_pinned_manifest():
    from airunner_services.art import triton_toolchain_installer as installer

    manifest = installer._source_manifest()
    assert len(manifest["archives"]) == 6
    assert all(item["url"].startswith("https://developer.download.nvidia.com/") for item in manifest["redistributions"].values())
    for notice in manifest["notices"]:
        resource = installer.resources.files("airunner_services.art").joinpath(
            "data/triton_external_toolchain_notices", notice["filename"]
        )
        assert installer.hashlib.sha256(resource.read_bytes()).hexdigest() == notice["sha256"]


def test_daemon_reports_operator_install_failure_without_starting(monkeypatch, capsys):
    from airunner_services import daemon
    from airunner_services.art import triton_toolchain_installer as installer

    def fail(_destination):
        raise installer.StageError("reviewed input hash mismatch")

    monkeypatch.setattr(installer, "install_private_toolchain", fail)
    with pytest.raises(SystemExit) as exc:
        daemon.main(["--install-triton-toolchain"])
    assert exc.value.code == 1
    assert "reviewed input hash mismatch" in capsys.readouterr().err
