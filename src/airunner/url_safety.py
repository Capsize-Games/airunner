"""Compatibility re-export shim for URL safety helpers (issue #2048).

The canonical implementation lives in ``airunner_services.url_safety``,
which carries the complete SSRF blocklist (private/link-local IPs, NAT64
embedded-IPv4 prefixes, 6to4 relay anycast and the operator-configurable
``AIRUNNER_SSRF_ALLOWED_HOSTS`` allow-list). This module is a thin re-export
so older ``airunner.url_safety`` imports keep working without a drifting
second copy.
"""

from __future__ import annotations

from airunner_services.url_safety import (
    SSRFBlocked,
    safe_fetch_bytes,
    safe_fetch_url,
    validate_url_for_fetch,
)

__all__ = [
    "SSRFBlocked",
    "safe_fetch_bytes",
    "safe_fetch_url",
    "validate_url_for_fetch",
]
