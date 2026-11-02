"""Security boundaries for the operator-only Triton input stager."""

from __future__ import annotations

import os
import stat
import urllib.request
from pathlib import Path

import pytest

from airunner_services.art import triton_toolchain_installer as installer


def test_installer_cli_requires_an_explicit_network_action(monkeypatch):
    calls = []
    monkeypatch.setattr(
        installer,
        "install_private_toolchain",
        lambda *_args, **_kwargs: calls.append("install"),
    )
    monkeypatch.setattr(
        installer,
        "stage_external_toolchain",
        lambda *_args, **_kwargs: calls.append("stage"),
    )

    with pytest.raises(SystemExit) as exc:
        installer.main([])

    assert exc.value.code == 2
    assert calls == []


def test_cli_install_and_staging_modes_print_their_returned_receipt(monkeypatch, capsys, tmp_path):
    expected = tmp_path / "receipt.json"
    receipt = {
        "environment": {"TRITON_PTXAS_PATH": str(tmp_path / "bin/ptxas")},
        "receipt_path": str(expected),
    }
    calls = []
    monkeypatch.setattr(
        installer,
        "install_private_toolchain",
        lambda: calls.append(("install",)) or receipt,
    )
    monkeypatch.setattr(
        installer,
        "stage_external_toolchain",
        lambda output, archive_cache=None: calls.append(("stage", output, archive_cache)) or receipt,
    )

    assert installer.main(["--install"]) == 0
    assert f"Receipt: {expected}" in capsys.readouterr().out
    assert installer.main(["--output-dir", str(tmp_path / "output")]) == 0
    assert calls == [
        ("install",),
        ("stage", tmp_path / "output", None),
    ]


def test_archive_cache_cannot_be_shared_tmp_root():
    with pytest.raises(installer.StageError, match="private AIRunner cache or /tmp"):
        installer._allowed_private_path(Path("/tmp"))


def test_missing_compile_cache_does_not_create_or_download(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: home))
    monkeypatch.setattr(
        installer, "_fetch",
        lambda *_args, **_kwargs: pytest.fail("cache discovery must not download"),
    )
    with pytest.raises(installer.StageError, match="does not exist"):
        installer.cached_toolchain_environment()
    assert list(home.iterdir()) == []


def test_private_directory_rejects_insecure_existing_cache_without_chmod(monkeypatch, tmp_path):
    home = tmp_path / "home"
    (home / ".cache" / "airunner").mkdir(parents=True)
    os.chmod(home / ".cache", 0o755)
    os.chmod(home / ".cache" / "airunner", 0o755)
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: home))

    with pytest.raises(installer.StageError, match="owner-only"):
        installer._ensure_private_directory(home / ".cache" / "airunner" / "triton")

    assert stat.S_IMODE((home / ".cache" / "airunner").stat().st_mode) == 0o755


def test_private_path_rejects_symlinked_cache_component(tmp_path):
    real = tmp_path / "real-cache"
    real.mkdir(mode=0o700)
    link = tmp_path / "linked-cache"
    link.symlink_to(real, target_is_directory=True)

    with pytest.raises(installer.StageError, match="symbolic links"):
        installer._allowed_private_path(link / "toolchain")


def test_redirect_target_is_rejected_before_urllib_follows_it():
    handler = installer._PinnedNvidiaRedirectHandler()
    request = urllib.request.Request(
        "https://developer.download.nvidia.com/compute/cuda/redist/input.tar.xz"
    )

    with pytest.raises(installer.StageError, match="outside the pinned NVIDIA"):
        handler.redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "https://attacker.example/collect",
        )


@pytest.mark.parametrize(
    "url",
    [
        "http://developer.download.nvidia.com/compute/cuda/redist/file",
        "https://developer.download.nvidia.com.evil/compute/cuda/redist/file",
        "https://user@developer.download.nvidia.com/compute/cuda/redist/file",
        "https://developer.download.nvidia.com/compute/cuda/redist/file?token=x",
        "https://developer.download.nvidia.com/elsewhere/file",
    ],
)
def test_download_url_requires_exact_https_nvidia_redist_endpoint(url):
    with pytest.raises(installer.StageError):
        installer._validate_download_url(url)
