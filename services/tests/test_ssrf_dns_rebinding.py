"""Regression tests: SSRF DNS-rebinding protection (issue #2490).

Validation resolves a hostname, but a plain ``requests`` call resolves it
again at connect time. An attacker hostname that answers with a public IP
during validation and a private IP a moment later (DNS rebinding) would
steer the connection onto an unvalidated address. These tests prove the
resolve-once + validated-IP connect behavior:

- ``resolve_url_for_fetch`` resolves exactly once per hop and pins one
  validated IP.
- ``pinned_dns`` keeps the socket layer on the validated IP even after
  the hostname's DNS record rebounds, without affecting other hostnames,
  and restores the resolver afterwards.
- every downloader path (generic safe-fetch, CivitAI streaming + metadata,
  HuggingFace worker response) re-validates each redirect hop and keeps
  the connection pinned while the transport runs.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import pytest
import requests

from airunner_common import settings as airunner_common_settings
from airunner_services import url_safety
from airunner_services.url_safety import (
    SSRFBlocked,
    pinned_dns,
    resolve_url_for_fetch,
    safe_fetch_bytes,
)


@pytest.fixture(autouse=True)
def _online_mode_for_rebinding_tests(monkeypatch):
    """Exercise DNS/SSRF validation itself, not the offline short-circuit."""
    monkeypatch.setattr(airunner_common_settings, "AIRUNNER_OFFLINE_MODE", False)


def _public_resolve(monkeypatch, mapping: dict) -> list:
    """Stub validation-time DNS to fixed public IPs; record calls."""
    calls: list = []

    def _fake_resolve(hostname: str, port: int):
        calls.append((hostname, port))
        return {ipaddress.ip_address(mapping[hostname])}

    monkeypatch.setattr(url_safety, "_resolve_host_ips", _fake_resolve)
    return calls


# ---------------------------------------------------------------------------
# resolve-once primitive
# ---------------------------------------------------------------------------


def test_resolve_returns_single_validated_ip_and_resolves_once(monkeypatch) -> None:
    """One validation performs one resolution and pins one public IP."""
    calls = _public_resolve(monkeypatch, {"cdn.example": "93.184.216.34"})

    target = resolve_url_for_fetch("https://cdn.example/file.bin")

    assert target.ip == "93.184.216.34"
    assert target.hostname == "cdn.example"
    assert target.port == 443
    assert calls == [("cdn.example", 443)]


def test_resolve_rejects_rebound_private_answer(monkeypatch) -> None:
    """A hostname rebound to private space fails closed at validation."""
    _public_resolve(monkeypatch, {"cdn.example": "10.9.9.9"})

    with pytest.raises(SSRFBlocked):
        resolve_url_for_fetch("https://cdn.example/file.bin")


def test_pinned_dns_survives_rebinding_and_restores(monkeypatch) -> None:
    """The socket layer keeps the validated IP after DNS rebounds."""
    real_getaddrinfo = socket.getaddrinfo

    def _attacker_dns(host, port, *args, **kwargs):
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            return real_getaddrinfo(host, port, *args, **kwargs)
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.9.9.9", port))
        ]

    monkeypatch.setattr(socket, "getaddrinfo", _attacker_dns)
    _public_resolve(monkeypatch, {"rebind.example": "93.184.216.34"})

    target = resolve_url_for_fetch("https://rebind.example/file.bin")
    assert target.ip == "93.184.216.34"

    with pinned_dns(target):
        pinned = {info[4][0] for info in socket.getaddrinfo("rebind.example", 443)}
        assert pinned == {"93.184.216.34"}
        # Other hostnames still see the (attacker-controlled) resolver.
        other = socket.getaddrinfo("other.example", 80)
        assert other[0][4][0] == "10.9.9.9"

    # After the pin is released the rebound record is visible again.
    assert socket.getaddrinfo("rebind.example", 443)[0][4][0] == "10.9.9.9"


def test_pinned_dns_none_target_is_passthrough() -> None:
    """Doubles that stub validation (returning None) skip pinning safely."""
    with pinned_dns(None) as yielded:
        assert yielded is None
    assert socket.getaddrinfo is not url_safety._pinned_getaddrinfo


# ---------------------------------------------------------------------------
# Generic safe-fetch path: pinned connect + redirect re-validation
# ---------------------------------------------------------------------------


class _FakeFetchResponse:
    def __init__(self, body: bytes = b"", *, status_code: int = 200, headers=None):
        self.status_code = status_code
        self.headers = headers or {}
        self.encoding = "utf-8"
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def iter_content(self, chunk_size: int):
        del chunk_size
        yield self._body


def test_safe_fetch_connects_to_validated_ip_despite_rebinding(monkeypatch) -> None:
    """Same-hop rebinding cannot move the connection off the validated IP."""
    resolutions = {"cdn.example": "93.184.216.34"}
    seen_inside_transport: dict = {}

    def _fake_resolve(hostname: str, port: int):
        return {ipaddress.ip_address(resolutions[hostname])}

    monkeypatch.setattr(url_safety, "_resolve_host_ips", _fake_resolve)

    def _fake_get(self, url, **kwargs):
        host = urlparse(url).hostname or ""
        # DNS rebounds after validation, before the stack would connect.
        resolutions[host] = "10.9.9.9"
        seen_inside_transport[host] = {
            info[4][0] for info in socket.getaddrinfo(host, 443)
        }
        return _FakeFetchResponse(body=b"weights")

    monkeypatch.setattr(requests.Session, "get", _fake_get)

    assert safe_fetch_bytes("https://cdn.example/file.bin") == b"weights"
    assert seen_inside_transport == {"cdn.example": {"93.184.216.34"}}


def test_safe_fetch_revalidates_redirect_after_rebinding(monkeypatch) -> None:
    """A redirect target that rebounds to private space is never fetched."""
    resolutions = {
        "attacker.example": "93.184.216.34",
        "cdn.evil.example": "93.184.216.35",
    }
    calls: list = []

    def _fake_resolve(hostname: str, port: int):
        return {ipaddress.ip_address(resolutions[hostname])}

    monkeypatch.setattr(url_safety, "_resolve_host_ips", _fake_resolve)

    def _fake_get(self, url, **kwargs):
        calls.append(url)
        if urlparse(url).hostname == "attacker.example":
            # The redirect target rebounds to private space after hop one.
            resolutions["cdn.evil.example"] = "10.1.2.3"
            return _FakeFetchResponse(
                status_code=302,
                headers={"location": "https://cdn.evil.example/payload"},
            )
        raise AssertionError("rebound redirect target must not be fetched")

    monkeypatch.setattr(requests.Session, "get", _fake_get)

    with pytest.raises(SSRFBlocked):
        safe_fetch_bytes("https://attacker.example/start.bin")
    assert calls == ["https://attacker.example/start.bin"]


# ---------------------------------------------------------------------------
# CivitAI paths: streaming download + metadata JSON
# ---------------------------------------------------------------------------


def test_civitai_stream_revalidates_rebound_redirect(monkeypatch) -> None:
    """A CivitAI redirect hop that rebounds private is blocked pre-request."""
    from airunner_services.downloads import civitai as civitai_module

    resolutions = {
        "attacker.example": "93.184.216.34",
        "cdn.evil.example": "93.184.216.35",
    }

    def _fake_resolve(hostname: str, port: int):
        return {ipaddress.ip_address(resolutions[hostname])}

    monkeypatch.setattr(url_safety, "_resolve_host_ips", _fake_resolve)

    calls: list = []

    class _Redirect:
        status_code = 302
        headers = {"location": "https://cdn.evil.example/payload"}

        def close(self) -> None:
            return None

    def _fake_get(url, **kwargs):
        calls.append(url)
        assert kwargs.get("allow_redirects") is False
        if urlparse(url).hostname == "attacker.example":
            resolutions["cdn.evil.example"] = "10.1.2.3"
        return _Redirect()

    monkeypatch.setattr(civitai_module.requests, "get", _fake_get)

    with pytest.raises(SSRFBlocked):
        civitai_module._get_streaming_response(
            "https://attacker.example/model.bin", api_key=""
        )
    assert calls == ["https://attacker.example/model.bin"]


def test_civitai_stream_pins_connection_despite_rebinding(monkeypatch) -> None:
    """The CivitAI transport still dials the validated IP after rebinding."""
    from airunner_services.downloads import civitai as civitai_module

    resolutions = {"civitai.example": "93.184.216.34"}
    seen_inside_transport: dict = {}

    def _fake_resolve(hostname: str, port: int):
        return {ipaddress.ip_address(resolutions[hostname])}

    monkeypatch.setattr(url_safety, "_resolve_host_ips", _fake_resolve)

    class _Final:
        status_code = 200

        def close(self) -> None:
            return None

    def _fake_get(url, **kwargs):
        host = urlparse(url).hostname or ""
        resolutions[host] = "10.9.9.9"
        seen_inside_transport[host] = {
            info[4][0] for info in socket.getaddrinfo(host, 443)
        }
        return _Final()

    monkeypatch.setattr(civitai_module.requests, "get", _fake_get)

    response = civitai_module._get_streaming_response(
        "https://civitai.example/model.bin", api_key=""
    )
    assert response.status_code == 200
    assert seen_inside_transport == {"civitai.example": {"93.184.216.34"}}


def test_civitai_metadata_redirect_to_private_is_blocked(monkeypatch) -> None:
    """CivitAI metadata follows redirects manually; private hops fail."""
    from airunner_services.downloads import civitai as civitai_module

    _public_resolve(monkeypatch, {"civitai.com": "93.184.216.34"})
    calls: list = []

    class _Redirect:
        status_code = 302
        headers = {"location": "http://169.254.169.254/latest/meta-data/"}

        def close(self) -> None:
            return None

        def raise_for_status(self) -> None:
            return None

    def _fake_get(url, **kwargs):
        calls.append(url)
        assert kwargs.get("allow_redirects") is False
        return _Redirect()

    monkeypatch.setattr(civitai_module.requests, "get", _fake_get)

    with pytest.raises(SSRFBlocked):
        civitai_module.fetch_model_info("1234")
    assert len(calls) == 1


def test_civitai_metadata_success_still_returns_json(monkeypatch) -> None:
    """The guarded metadata path returns JSON when every hop validates."""
    from airunner_services.downloads import civitai as civitai_module

    _public_resolve(monkeypatch, {"civitai.com": "93.184.216.34"})

    class _Ok:
        status_code = 200
        headers = {}

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {"id": 1234}

    monkeypatch.setattr(
        civitai_module.requests, "get", lambda url, **kwargs: _Ok()
    )

    assert civitai_module.fetch_model_info("1234") == {"id": 1234}


# ---------------------------------------------------------------------------
# HuggingFace worker path: validated response keeps the pin per hop
# ---------------------------------------------------------------------------


def test_hf_response_pins_connection_despite_rebinding(monkeypatch) -> None:
    """The HF worker dials the validated IP even after DNS rebounds."""
    from airunner_services.downloads import (
        huggingface_download_worker as hf_worker_module,
    )

    resolutions = {"huggingface.co": "93.184.216.34"}
    seen_inside_transport: dict = {}

    def _fake_resolve(hostname: str, port: int):
        return {ipaddress.ip_address(resolutions[hostname])}

    monkeypatch.setattr(url_safety, "_resolve_host_ips", _fake_resolve)

    class _Final:
        status_code = 200
        headers = {}
        url = ""

    def _fake_get(url, **kwargs):
        host = urlparse(url).hostname or ""
        resolutions[host] = "10.9.9.9"
        seen_inside_transport[host] = {
            info[4][0] for info in socket.getaddrinfo(host, 443)
        }
        assert kwargs.get("allow_redirects") is False
        return _Final()

    monkeypatch.setattr(hf_worker_module.requests, "get", _fake_get)

    response = hf_worker_module._open_validated_hf_response(
        "get",
        "https://huggingface.co/org/model/resolve/main/weights.bin",
        {},
        30,
    )
    assert response.status_code == 200
    assert seen_inside_transport == {"huggingface.co": {"93.184.216.34"}}


def test_hf_response_redirect_revalidated_after_rebinding(monkeypatch) -> None:
    """An HF redirect hop that rebounds private is blocked pre-request."""
    from airunner_services.downloads import (
        huggingface_download_worker as hf_worker_module,
    )

    resolutions = {
        "huggingface.co": "93.184.216.34",
        "cdn.evil.example": "93.184.216.35",
    }

    def _fake_resolve(hostname: str, port: int):
        return {ipaddress.ip_address(resolutions[hostname])}

    monkeypatch.setattr(url_safety, "_resolve_host_ips", _fake_resolve)

    calls: list = []

    class _Redirect:
        status_code = 302
        headers = {"location": "https://cdn.evil.example/payload"}

        def close(self) -> None:
            return None

    def _fake_get(url, **kwargs):
        calls.append(url)
        resolutions["cdn.evil.example"] = "10.1.2.3"
        return _Redirect()

    monkeypatch.setattr(hf_worker_module.requests, "get", _fake_get)

    with pytest.raises(SSRFBlocked):
        hf_worker_module._open_validated_hf_response(
            "get",
            "https://huggingface.co/org/model/resolve/main/weights.bin",
            {},
            30,
        )
    assert calls == [
        "https://huggingface.co/org/model/resolve/main/weights.bin"
    ]
