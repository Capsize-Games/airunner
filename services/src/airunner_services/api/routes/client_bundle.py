"""Serve the built desktop chat client over the daemon's loopback origin.

The desktop chat surface is the cloud-excluded React build produced by the
web repo's ``airunner-desktop`` target (#2230). The daemon serves it so the
page shares its origin with ``/api/v1/*``: ``wsHost()`` keeps resolving to
the daemon without a build-time host override, and the existing
loopback-token policy that guards the API guards the bundle too.

The bundle is optional. When it cannot be found nothing is mounted and the
daemon's routing is byte-for-byte what it was before.

Two sources are consulted, in order:

1. ``AIRUNNER_CLIENT_BUNDLE`` -- an explicit path. When it is set but does
   not contain an ``index.html`` nothing is mounted, because an operator's
   explicit choice is authoritative and must not silently fall back.
2. The release build output directory -- ``AIRUNNER_DESKTOP_BUILD_DIR``, or
   :data:`DEFAULT_BUILD_ROOT` -- at :data:`BUNDLE_SUBDIR`. Release builds
   place the client there (see ``scripts/package_desktop_client.py``), so a
   packaged install finds its surface without the operator setting any
   environment variable at all.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

BUNDLE_ENV = "AIRUNNER_CLIENT_BUNDLE"
BUILD_ROOT_ENV = "AIRUNNER_DESKTOP_BUILD_DIR"
DEFAULT_BUILD_ROOT = Path("/media/joe/Megatron/airunner-desktop-builds")
BUNDLE_SUBDIR = "desktop-client"
INDEX_FILE = "index.html"


def _has_index(directory: Path) -> bool:
    """Return whether ``directory`` holds a bundle entry document."""
    return (directory / INDEX_FILE).is_file()


def build_output_directory() -> Path:
    """Return the release build output root for the desktop client."""
    raw = (os.environ.get(BUILD_ROOT_ENV) or "").strip()
    if raw:
        return Path(raw).expanduser()
    return DEFAULT_BUILD_ROOT


def packaged_bundle_directory() -> Path:
    """Return where a release build places the client bundle."""
    return build_output_directory() / BUNDLE_SUBDIR


def bundle_directory() -> Optional[Path]:
    """Return the bundle directory to serve, or ``None`` when absent."""
    explicit = (os.environ.get(BUNDLE_ENV) or "").strip()
    if explicit:
        directory = Path(explicit).expanduser()
        return directory if _has_index(directory) else None
    packaged = packaged_bundle_directory()
    return packaged if _has_index(packaged) else None


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
    "BUNDLE_SUBDIR",
    "BUILD_ROOT_ENV",
    "DEFAULT_BUILD_ROOT",
    "INDEX_FILE",
    "build_output_directory",
    "bundle_directory",
    "mount_client_bundle",
    "packaged_bundle_directory",
]
