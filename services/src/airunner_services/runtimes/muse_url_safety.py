"""SSRF guard for Muse-returned image URLs."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from airunner_services.url_safety import _is_ip_disallowed


def guard_image_url(url: str) -> None:
    """Reject a non-https, private, or unresolvable image URL.

    Address checks reuse the canonical outbound-fetch guard
    (:func:`airunner_services.url_safety._is_ip_disallowed`), which
    covers NAT64-embedded, 6to4-relay, multicast, and non-global
    addresses in addition to plain private/loopback ranges.

    Raises:
        ValueError: with a stable ``muse_*`` code as its message.
    """
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("muse_invalid_image_url")
    host = (parsed.hostname or "").strip().lower().rstrip(".")
    if not host or host == "localhost" or host.endswith(".localhost"):
        raise ValueError("muse_invalid_image_url")
    _reject_disallowed(_resolve(host))


def _resolve(host: str) -> list[ipaddress._BaseAddress]:
    try:
        return [ipaddress.ip_address(host)]
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except OSError as exc:
        raise ValueError("muse_invalid_image_url") from exc
    addresses = []
    for info in infos:
        try:
            addresses.append(ipaddress.ip_address(str(info[4][0])))
        except ValueError as exc:
            raise ValueError("muse_invalid_image_url") from exc
    if not addresses:
        raise ValueError("muse_invalid_image_url")
    return addresses


def _reject_disallowed(
    addresses: list[ipaddress._BaseAddress],
) -> None:
    for address in addresses:
        mapped = getattr(address, "ipv4_mapped", None)
        if mapped is not None:
            address = mapped
        if _is_ip_disallowed(address):
            raise ValueError("muse_invalid_image_url")


__all__ = ["guard_image_url"]
