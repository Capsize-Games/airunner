"""SSRF guard for Muse-returned image URLs."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


def guard_image_url(url: str) -> None:
    """Reject a non-https, private, or unresolvable image URL.

    Raises:
        ValueError: with a stable ``muse_*`` code as its message.
    """
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("muse_invalid_image_url")
    host = (parsed.hostname or "").strip().lower().rstrip(".")
    if not host or host == "localhost" or host.endswith(".localhost"):
        raise ValueError("muse_invalid_image_url")
    _reject_non_global(_resolve(host))


def _resolve(host: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        return [literal]
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except OSError as exc:
        raise ValueError("muse_invalid_image_url") from exc
    addresses = []
    for info in infos:
        sockaddr = info[4]
        try:
            addresses.append(ipaddress.ip_address(str(sockaddr[0])))
        except ValueError as exc:
            raise ValueError("muse_invalid_image_url") from exc
    if not addresses:
        raise ValueError("muse_invalid_image_url")
    return addresses


def _reject_non_global(
    addresses: list[ipaddress.IPv4Address | ipaddress.IPv6Address],
) -> None:
    for address in addresses:
        mapped = getattr(address, "ipv4_mapped", None)
        if mapped is not None:
            address = mapped
        if not address.is_global:
            raise ValueError("muse_invalid_image_url")


__all__ = ["guard_image_url"]
