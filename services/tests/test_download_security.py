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

from airunner_common import settings as airunner_common_settings
from airunner_services.downloads.civitai import (
    _MAX_DOWNLOAD_REDIRECTS,
    _open_download,
    _planned_download_file,
    _safe_server_filename,
    get_files_to_download,
)
from airunner_services.downloads.huggingface import (
    prepare_huggingface_download_request,
    safe_hf_filename,
)
from airunner_services.downloads.huggingface_download_worker import (
    _HF_MAX_REDIRECTS,
    _contained_hf_path,
    _open_validated_hf_response,
)
from airunner_services.downloads.job_service import (
    DownloadJobService,
    _assert_output_path_contained,
    _resolve_safe_file_path,
    _resolve_safe_output_dir,
    _safe_filename,
)
from airunner_services.runtimes.file_policy import PathPolicyError
from airunner_services.url_safety import (
    SSRFBlocked,
    validate_url_for_fetch,
)


@pytest.fixture(autouse=True)
def _online_mode_for_ssrf_tests(monkeypatch):
    """This file exercises SSRF/path-safety validation specifically.

    Force online mode so validate_url_for_fetch reaches those checks
    instead of short-circuiting on the offline-by-default policy
    (release issue O01); that policy has its own dedicated tests.
    """
    monkeypatch.setattr(airunner_common_settings, "AIRUNNER_OFFLINE_MODE", False)


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
        # NAT64-embedded loopback/private IPv4 (RFC 6052 / RFC 8215). These
        # prefixes report is_global=True, so they need an explicit check.
        "http://[64:ff9b::7f00:1]/x",
        "http://[64:ff9b::a00:1]/x",
        "http://[64:ff9b::ac10:1]/x",
        "http://[64:ff9b::c0a8:101]/x",
        "http://[64:ff9b:1::7f00:1]/x",
        # 6to4 relay anycast (deprecated, RFC 7526).
        "http://192.88.99.1/x",
        # Multicast is not a valid fetch target.
        "http://224.0.0.1/x",
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


def test_validate_url_for_fetch_nat64_embedded_public_ip_allowed() -> None:
    """A NAT64 prefix embedding a public IPv4 stays fetchable (no overblock)."""
    # 64:ff9b::808:808 embeds 8.8.8.8, which is a global address.
    validate_url_for_fetch("http://[64:ff9b::808:808]/x")


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


# ---------------------------------------------------------------------------
# CivitAI server-supplied filenames (fail closed, never rewritten)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_filename",
    [
        "../evil.sh",
        "../../etc/passwd",
        "sub/escape.bin",
        "sub\\escape.bin",
        "/etc/passwd",
        "/tmp/absolute.bin",
        "..",
        ".",
        "",
        "   ",
        "name\x00evil",
    ],
)
def test_safe_server_filename_rejects_escapes(bad_filename: str) -> None:
    with pytest.raises(PathPolicyError):
        _safe_server_filename(bad_filename)


def test_safe_server_filename_accepts_plain_basename() -> None:
    assert _safe_server_filename("model.safetensors") == "model.safetensors"


def test_planned_download_file_rejects_malicious_server_name(tmp_path) -> None:
    file_info = {
        "name": "../evil.sh",
        "downloadUrl": "https://civitai.com/api/download/models/1",
        "sizeKB": 1,
    }
    with pytest.raises(PathPolicyError):
        _planned_download_file(file_info, tmp_path / "model")


def test_get_files_to_download_rejects_malicious_server_name(tmp_path) -> None:
    version = {
        "files": [
            {
                "name": "good.safetensors",
                "downloadUrl": "https://civitai.com/api/download/models/1",
                "sizeKB": 1,
            },
            {
                "name": "../../evil.sh",
                "downloadUrl": "https://civitai.com/api/download/models/2",
                "sizeKB": 1,
            },
        ]
    }
    with pytest.raises(PathPolicyError):
        get_files_to_download(version, tmp_path / "model")


def test_planned_download_file_confines_writes_to_model_dir(tmp_path) -> None:
    file_info = {
        "name": "weights.safetensors",
        "downloadUrl": "https://civitai.com/api/download/models/1",
        "sizeKB": 1,
    }
    planned = _planned_download_file(file_info, tmp_path / "model")
    assert planned is not None
    assert planned["filename"] == "weights.safetensors"


def test_civitai_model_job_fails_closed_on_malicious_filename(tmp_path) -> None:
    """A malicious server filename fails the job instead of writing."""
    import threading

    tracker = mock.AsyncMock()
    service = DownloadJobService(
        tracker=tracker,
        huggingface_downloader=mock.MagicMock(),
    )
    malicious_version = {
        "files": [
            {
                "name": "../evil.sh",
                "downloadUrl": "https://civitai.com/api/download/models/1",
                "sizeKB": 1,
            }
        ]
    }
    with (
        mock.patch(
            "airunner_services.downloads.job_service.fetch_model_info_for_url",
            return_value={
                "name": "model",
                "selectedVersion": malicious_version,
            },
        ),
        mock.patch(
            "airunner_services.downloads.job_service.download_civitai_file"
        ) as download,
    ):
        service._run_civitai_model_job(
            "job-1",
            threading.Event(),
            "https://civitai.com/models/1",
            str(tmp_path),
            "",
        )
    download.assert_not_called()
    tracker.fail_job.assert_called()


# ---------------------------------------------------------------------------
# HuggingFace filename gate (relative subpaths allowed, escapes rejected)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_filename",
    [
        "../evil.bin",
        "sub/../../evil.bin",
        "/etc/passwd",
        "/tmp/absolute.bin",
        "..\\evil.bin",
        "sub\\escape.bin",
        "..",
        ".",
        "",
        "   ",
        "name\x00evil",
    ],
)
def test_safe_hf_filename_rejects_escapes(bad_filename: str) -> None:
    with pytest.raises(PathPolicyError):
        safe_hf_filename(bad_filename)


def test_safe_hf_filename_accepts_relative_subpaths() -> None:
    assert safe_hf_filename("model.safetensors") == "model.safetensors"
    assert (
        safe_hf_filename("tokenizer/merges.txt") == "tokenizer/merges.txt"
    )


def test_prepare_hf_request_rejects_malicious_filenames() -> None:
    with pytest.raises(PathPolicyError):
        prepare_huggingface_download_request(
            repo_id="org/repo",
            model_type="art",
            output_dir="/tmp/models",
            gguf_filename="../evil.gguf",
        )
    with pytest.raises(PathPolicyError):
        prepare_huggingface_download_request(
            repo_id="org/repo",
            model_type="art",
            output_dir="/tmp/models",
            missing_files=["good.bin", "../../evil.bin"],
        )


def test_contained_hf_path_rejects_symlink_escape(tmp_path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    base = tmp_path / "model"
    base.mkdir()
    (base / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(PathPolicyError):
        _contained_hf_path(base, "link/evil.bin")


def test_contained_hf_path_accepts_inside_path(tmp_path) -> None:
    base = tmp_path / "model"
    (base / "sub").mkdir(parents=True)
    resolved = _contained_hf_path(base, "sub/weights.safetensors")
    assert resolved == (base / "sub" / "weights.safetensors").resolve()


def test_hf_file_job_rejects_traversal_filename(tmp_path) -> None:
    """A traversal filename fails the HF single-file job without writing."""
    import threading

    tracker = mock.AsyncMock()
    downloader = mock.MagicMock()
    service = DownloadJobService(
        tracker=tracker,
        huggingface_downloader=downloader,
    )
    service._run_huggingface_file_job(
        "job-1",
        threading.Event(),
        "org/repo",
        "../evil.bin",
        str(tmp_path),
    )
    downloader.download_file.assert_not_called()
    tracker.fail_job.assert_called()


# ---------------------------------------------------------------------------
# HuggingFace redirect validation (every hop, like civitai)
# ---------------------------------------------------------------------------


def test_validated_hf_response_blocks_ssrf_url_before_request() -> None:
    with mock.patch(
        "airunner_services.downloads.huggingface_download_worker.requests.get"
    ) as get, mock.patch(
        "airunner_services.downloads.huggingface_download_worker.requests.head"
    ) as head:
        with pytest.raises(SSRFBlocked):
            _open_validated_hf_response(
                "get", "http://127.0.0.1/private", {}, 30
            )
        with pytest.raises(SSRFBlocked):
            _open_validated_hf_response(
                "head", "http://127.0.0.1/private", {}, 30
            )
        get.assert_not_called()
        head.assert_not_called()


def test_validated_hf_response_rejects_redirect_to_private_target(
    monkeypatch,
) -> None:
    """A public HF URL that redirects onto the metadata IP is blocked."""
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
        "airunner_services.downloads.huggingface_download_worker.requests.get",
        side_effect=[redirect_response, final_response],
    ) as get:
        with pytest.raises(SSRFBlocked):
            _open_validated_hf_response(
                "get", "https://huggingface.co/org/repo", {}, 30
            )
    assert get.call_count == 1


def test_validated_hf_response_follows_public_redirect(monkeypatch) -> None:
    """A public redirect target is still followed."""
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
        "airunner_services.downloads.huggingface_download_worker.requests.get",
        side_effect=[redirect_response, final_response],
    ) as get:
        result = _open_validated_hf_response(
            "get", "https://huggingface.co/org/repo", {}, 30
        )
    assert result is final_response
    assert get.call_count == 2


def test_validated_hf_response_limits_redirects(monkeypatch) -> None:
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
        for index in range(_HF_MAX_REDIRECTS + 1)
    ]
    final_response = mock.MagicMock()
    final_response.status_code = 200

    with mock.patch(
        "airunner_services.downloads.huggingface_download_worker.requests.get",
        side_effect=[*redirects, final_response],
    ) as get:
        with pytest.raises(SSRFBlocked):
            _open_validated_hf_response(
                "get", "https://huggingface.co/org/repo", {}, 30
            )
    assert get.call_count == _HF_MAX_REDIRECTS + 1
