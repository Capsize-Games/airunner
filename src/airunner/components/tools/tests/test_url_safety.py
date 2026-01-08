from __future__ import annotations

import pytest

from airunner.components.tools.url_safety import SSRFBlocked, validate_url_for_fetch


def test_rejects_non_http_scheme() -> None:
    with pytest.raises(SSRFBlocked):
        validate_url_for_fetch("file:///etc/passwd")


def test_rejects_loopback_ipv4() -> None:
    with pytest.raises(SSRFBlocked):
        validate_url_for_fetch("http://127.0.0.1/")


def test_rejects_link_local_metadata_ipv4() -> None:
    with pytest.raises(SSRFBlocked):
        validate_url_for_fetch("http://169.254.169.254/latest/meta-data/")


def test_allows_public_ipv4_literal() -> None:
    # example.com (public, globally routable). Using an IP literal avoids DNS reliance.
    validate_url_for_fetch("http://93.184.216.34/")
