"""Optionally serve an explicitly configured client bundle.

The service does not discover or host client assets by default. A consuming
application may set ``AIRUNNER_CLIENT_BUNDLE`` to a directory containing an
``index.html`` file. When configured, the mounted files retain the daemon's
existing authentication policy.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.routing import Match, Mount
from starlette.types import Scope

BUNDLE_ENV = "AIRUNNER_CLIENT_BUNDLE"
INDEX_FILE = "index.html"


def _has_index(directory: Path) -> bool:
    """Return whether ``directory`` holds a bundle entry document.

    The bundle is optional: an unreadable configured directory counts as
    absent instead of failing service startup (issue #2243).
    """
    try:
        return (directory / INDEX_FILE).is_file()
    except OSError:
        return False


def bundle_directory() -> Optional[Path]:
    """Return the bundle directory to serve, or ``None`` when absent."""
    explicit = (os.environ.get(BUNDLE_ENV) or "").strip()
    if not explicit:
        return None
    directory = Path(explicit).expanduser()
    return directory if _has_index(directory) else None


class _BundleMount(Mount):
    """Static mount that yields to API routes on method mismatch.

    Starlette serves the first full match, so a plain ``"/"`` static
    mount would answer ``404`` for ``GET`` on a POST-only API path
    instead of the router's ``405``. Deferring on a sibling partial
    match keeps the documented precedence: API paths answer as before
    and only unmatched paths reach the bundle.
    """

    def matches(self, scope: Scope) -> tuple[Match, Scope]:
        """Claim no match when an API route matches the path."""
        if scope.get("type") in ("http", "websocket"):
            routes = getattr(scope.get("app"), "routes", [])
            for route in routes:
                if route is self or isinstance(route, Mount):
                    continue
                match, _ = route.matches(scope)
                if match == Match.PARTIAL:
                    return Match.NONE, {}
        return super().matches(scope)


def mount_client_bundle(app: FastAPI) -> bool:
    """Mount the configured client bundle at the site root when enabled.

    Registered after every API router, so API paths keep precedence and only
    unmatched paths (``/index.html``, ``/assets/*``) reach the bundle.
    """
    directory: Union[None, Path] = bundle_directory()
    if directory is None:
        return False
    app.routes.append(
        _BundleMount(
            "/",
            app=StaticFiles(directory=str(directory), html=True),
            name="client-bundle",
        )
    )
    return True


__all__ = [
    "BUNDLE_ENV",
    "INDEX_FILE",
    "bundle_directory",
    "mount_client_bundle",
]
