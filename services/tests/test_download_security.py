"""Unit tests for security fixes on the generic URL download path.

Covers GitHub issue #2029:
- SSRF validation for outbound download URLs (loopback / private / link-local).
- Filename sanitization (``../``, absolute paths, embedded separators).
- Output directory constrained to the configured download root.
- ``_open_download`` validates URLs before issuing requests.
"""

from __future__ import annotations

import os
from unittest import mock

import pytest

from airunner_services.downloads.job_service import (
    _assert_output_path_contained,
    _resolve_safe_file_path,
    _resolve_safe_output_dir,
    _safe_filename,
)
from airunner_services.downloads.civitai import (
    _MAX_DOWNLOAD_REDIRECTS,
    _open_download,
)
from airunner_services.runtimes.file_policy import PathPolicyError
from airunner_services.url_safety import (
    SSRFBlocked,
    validate_url_for_fetch,
)


# ---------------------------------------------------------------------------
# Filename sanitization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_filename",
    [
        "../evil.sh",
        "../../etc/passwd",
        "sub/../escape.txt",
        "/etc/passwd",
        "/tmp/absolute.bin",
        "a/b",
        "..",
        ".",
        "",
        "name\x00evil",
    ],
)
def test_safe_filename_rejects_traversal_and_absolute(bad_filename: str) -> None:
    with pytest.raises(PathPolicyError):
        _safe_filename(bad_filename)


def test_safe_filename_accepts_plain_basename() -> None:
    assert _safe_filename("model.zip") == "model.zip"
    assert _safe_filename("weights.safetensors") == "weights.safetensors"
    assert _safe_filename("download.bin") == "download.bin"


# ---------------------------------------------------------------------------
# Output directory constraints
# ---------------------------------------------------------------------------


def test_output_dir_must_stay_inside_download_root(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AIRUNNER_DOWNLOAD_ROOT", str(tmp_path / "models"))
    root = tmp_path / "models"
    root.mkdir(parents=True)

    inside = _resolve_safe_output_dir(str(root / "downloads" / "sub"))
    assert inside == (root / "downloads" / "sub").resolve()

    with pytest.raises(PathPolicyError):
        _resolve_safe_output_dir(str(tmp_path / "outside"))


def test_output_dir_rejects_relative_escape(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AIRUNNER_DOWNLOAD_ROOT", str(tmp_path / "models"))
    root = tmp_path / "models"
    root.mkdir(parents=True)
    with pytest.raises(PathPolicyError):
        _resolve_safe_output_dir("../outside")


# ---------------------------------------------------------------------------
# SSRF validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_url",
    [
        "http://127.0.0.1/anything",
        "http://127.0.0.2:8080/x",
        "http://localhost:8080/x",
        "http://[::1]/x",
        "http://10.0.0.1/x",
        "http://172.16.0.1/x",
        "http://192.168.1.1/x",
        "http://169.254.169.254/latest/meta-data/",
        "http://0.0.0.0/x",
        "http://[fe80::1]/x",
        "http://[::ffff:127.0.0.1]/x",
    ],
)
def test_validate_url_for_fetch_rejects_loopback_and_private(bad_url: str) -> None:
    with pytest.raises(SSRFBlocked):
        validate_url_for_fetch(bad_url)


def test_validate_url_for_fetch_rejects_bad_scheme_and_userinfo() -> None:
    with pytest.raises(SSRFBlocked):
        validate_url_for_fetch("file:///etc/passwd")
    with pytest.raises(SSRFBlocked):
        validate_url_for_fetch("ftp://example.com/x")
    with pytest.raises(SSRFBlocked):
        validate_url_for_fetch("http://user:pass@example.com/x")


def test_validate_url_for_fetch_allowlist_for_intranet_mirrors(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "AIRUNNER_SSRF_ALLOWED_HOSTS",
        "10.0.0.1, 10.0.0.2, mirror.internal",
    )
    # Allowlisted IP literal passes even though it is private.
    validate_url_for_fetch("http://10.0.0.1/models/weights.safetensors")
    validate_url_for_fetch("http://10.0.0.2/file.zip")
    # Non-allowlisted private IP is still rejected.
    with pytest.raises(SSRFBlocked):
        validate_url_for_fetch("http://10.0.0.3/file.zip")
    # Loopback stays rejected even when allowlisted via a hostname entry.
    with pytest.raises(SSRFBlocked):
        validate_url_for_fetch("http://localhost/x")


def test_validate_url_for_fetch_hostname_resolution(
    monkeypatch,
) -> None:
    import ipaddress

    from airunner_services import url_safety

    def _fake_resolve(hostname: str, port: int):
        del hostname, port
        return {ipaddress.ip_address("93.184.216.34")}

    monkeypatch.setattr(url_safety, "_resolve_host_ips", _fake_resolve)
    validate_url_for_fetch("https://example.com/path")

    def _fake_private_resolve(hostname: str, port: int):
        del hostname, port
        return {ipaddress.ip_address("10.1.2.3")}

    monkeypatch.setattr(url_safety, "_resolve_host_ips", _fake_private_resolve)
    with pytest.raises(SSRFBlocked):
        validate_url_for_fetch("https://example.com/path")


def test_validate_url_for_fetch_rejects_obfuscated_loopback(
    monkeypatch,
) -> None:
    """Decimal/octal hostnames that resolve to loopback are still blocked."""
    import ipaddress

    from airunner_services import url_safety

    def _fake_resolve(hostname: str, port: int):
        del hostname, port
        return {ipaddress.ip_address("127.0.0.1")}

    monkeypatch.setattr(url_safety, "_resolve_host_ips", _fake_resolve)
    with pytest.raises(SSRFBlocked):
        validate_url_for_fetch("http://2130706433/anything")


# ---------------------------------------------------------------------------
# civitai._open_download validates before fetching
# ---------------------------------------------------------------------------


def test_open_download_blocks_ssrf_url_before_request() -> None:
    with mock.patch("airunner_services.downloads.civitai.requests.get") as get:
        with pytest.raises(SSRFBlocked):
            _open_download("http://127.0.0.1/private", api_key="")
        get.assert_not_called()


def test_open_download_accepts_public_url() -> None:
    response = mock.MagicMock()
    response.status_code = 200
    with mock.patch(
        "airunner_services.downloads.civitai.requests.get",
        return_value=response,
    ) as get:
        result = _open_download("https://example.com/model.safetensors", api_key="")
        assert result is response
        get.assert_called_once()


def test_open_download_rejects_redirect_to_private_target(monkeypatch) -> None:
    """A public URL that redirects onto the metadata IP must be blocked."""
    import ipaddress

    from airunner_services import url_safety

    def _fake_public_resolve(hostname: str, port: int):
        del hostname, port
        return {ipaddress.ip_address("93.184.216.34")}

    monkeypatch.setattr(url_safety, "_resolve_host_ips", _fake_public_resolve)

    redirect_response = mock.MagicMock()
    redirect_response.status_code = 302
    redirect_response.headers = {
        "location": "http://169.254.169.254/latest/meta-data/",
    }
    final_response = mock.MagicMock()
    final_response.status_code = 200

    with mock.patch(
        "airunner_services.downloads.civitai.requests.get",
        side_effect=[redirect_response, final_response],
    ) as get:
        with pytest.raises(SSRFBlocked):
            _open_download("https://attacker.example/model.bin", api_key="")
    # The redirect target must never be requested.
    assert get.call_count == 1


def test_open_download_follows_redirect_when_target_is_public(monkeypatch) -> None:
    """A public URL that redirects to another public URL still succeeds."""
    import ipaddress

    from airunner_services import url_safety

    def _fake_public_resolve(hostname: str, port: int):
        del hostname, port
        return {ipaddress.ip_address("93.184.216.34")}

    monkeypatch.setattr(url_safety, "_resolve_host_ips", _fake_public_resolve)

    redirect_response = mock.MagicMock()
    redirect_response.status_code = 302
    redirect_response.headers = {"location": "https://cdn.example/model.bin"}
    final_response = mock.MagicMock()
    final_response.status_code = 200

    with mock.patch(
        "airunner_services.downloads.civitai.requests.get",
        side_effect=[redirect_response, final_response],
    ) as get:
        result = _open_download("https://attacker.example/model.bin", api_key="")
    assert result is final_response
    assert get.call_count == 2


def test_open_download_limits_redirects(monkeypatch) -> None:
    """Redirect chains are capped to avoid open-redirect loops."""
    import ipaddress

    from airunner_services import url_safety

    def _fake_public_resolve(hostname: str, port: int):
        del hostname, port
        return {ipaddress.ip_address("93.184.216.34")}

    monkeypatch.setattr(url_safety, "_resolve_host_ips", _fake_public_resolve)

    redirects = [
        mock.MagicMock(
            status_code=302,
            headers={"location": f"https://cdn.example/hop-{index}.bin"},
        )
        for index in range(_MAX_DOWNLOAD_REDIRECTS + 1)
    ]
    final_response = mock.MagicMock()
    final_response.status_code = 200

    with mock.patch(
        "airunner_services.downloads.civitai.requests.get",
        side_effect=[*redirects, final_response],
    ) as get:
        with pytest.raises(SSRFBlocked):
            _open_download("https://attacker.example/model.bin", api_key="")
    assert get.call_count == _MAX_DOWNLOAD_REDIRECTS + 1


# ---------------------------------------------------------------------------
# Destination file path containment (arbitrary file write protection)
# ---------------------------------------------------------------------------


def test_resolve_safe_file_path_rejects_escape(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AIRUNNER_DOWNLOAD_ROOT", str(tmp_path / "models"))
    root = tmp_path / "models"
    root.mkdir(parents=True)

    for bad_path in (
        str(tmp_path / "outside" / "evil.sh"),
        str(tmp_path / "etc" / "passwd"),
        "/etc/passwd",
        "/tmp/absolute.bin",
    ):
        with pytest.raises(PathPolicyError):
            _resolve_safe_file_path(bad_path)


def test_resolve_safe_file_path_rejects_traversal_and_empty() -> None:
    for bad_path in ("", "..", ".", "../evil.sh", "sub/../escape.txt"):
        with pytest.raises(PathPolicyError):
            _resolve_safe_file_path(bad_path)


def test_resolve_safe_file_path_accepts_inside_root(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AIRUNNER_DOWNLOAD_ROOT", str(tmp_path / "models"))
    root = tmp_path / "models"
    root.mkdir(parents=True)

    inside = root / "art" / "models" / "civitai" / "weights.safetensors"
    resolved = _resolve_safe_file_path(str(inside))
    assert resolved == inside.resolve().as_posix()


def test_resolve_safe_file_path_rejects_symlink_escape(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AIRUNNER_DOWNLOAD_ROOT", str(tmp_path / "models"))
    root = tmp_path / "models"
    outside = tmp_path / "outside"
    root.mkdir(parents=True)
    outside.mkdir(parents=True)
    (root / "link").symlink_to(outside, target_is_directory=True)

    with pytest.raises(PathPolicyError):
        _resolve_safe_file_path(str(root / "link" / "evil.sh"))


def test_assert_output_path_contained_rejects_symlink_escape(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AIRUNNER_DOWNLOAD_ROOT", str(tmp_path / "models"))
    root = tmp_path / "models"
    outside = tmp_path / "outside"
    root.mkdir(parents=True)
    outside.mkdir(parents=True)
    (root / "link").symlink_to(outside, target_is_directory=True)

    with pytest.raises(PathPolicyError):
        _assert_output_path_contained(root / "link" / "evil.sh")


def test_resolve_safe_output_dir_rejects_empty(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AIRUNNER_DOWNLOAD_ROOT", str(tmp_path / "models"))
    root = tmp_path / "models"
    root.mkdir(parents=True)
    with pytest.raises(PathPolicyError):
        _resolve_safe_output_dir("")
    with pytest.raises(PathPolicyError):
        _resolve_safe_output_dir("   ")
