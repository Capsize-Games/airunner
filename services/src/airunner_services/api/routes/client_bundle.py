"""Serve the built desktop chat client over the daemon's loopback origin.

The desktop chat surface is the cloud-excluded React build produced by the
web repo's ``airunner-desktop`` target (#2230). The daemon serves it so the
page shares its origin with ``/api/v1/*``: ``wsHost()`` keeps resolving to
the daemon without a build-time host override, and the existing
loopback-token policy that guards the API guards the bundle too.

The bundle is optional. When ``AIRUNNER_CLIENT_BUNDLE`` does not point at a
directory containing ``index.html`` nothing is mounted and the daemon's
routing is byte-for-byte what it was before.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

BUNDLE_ENV = "AIRUNNER_CLIENT_BUNDLE"
INDEX_FILE = "index.html"


def bundle_directory() -> Optional[Path]:
    """Return the configured bundle directory when it holds an index file."""
    raw = (os.environ.get(BUNDLE_ENV) or "").strip()
    if not raw:
        return None
    directory = Path(raw).expanduser()
    if not (directory / INDEX_FILE).is_file():
        return None
    return directory


def mount_client_bundle(app: FastAPI) -> bool:
    """Mount the built bundle at the site root; report whether it was mounted.

    Registered after every API router, so API paths keep precedence and only
    unmatched paths (``/index.html``, ``/assets/*``) reach the bundle.
    """
    directory: Union[None, Path] = bundle_directory()
    if directory is None:
        return False
    app.mount(
        "/",
        StaticFiles(directory=str(directory), html=True),
        name="client-bundle",
    )
    return True


__all__ = [
    "BUNDLE_ENV",
    "INDEX_FILE",
    "bundle_directory",
    "mount_client_bundle",
]
