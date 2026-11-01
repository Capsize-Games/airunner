"""Require the existing administrative credential for privileged actions."""

import os
import secrets

from fastapi import HTTPException, Request


def require_admin_key(request: Request) -> None:
    """Require an admin key in addition to ordinary transport auth."""
    expected = (os.environ.get("AIRUNNER_ADMIN_KEY") or "").strip()
    if not expected:
        raise HTTPException(403, "Admin operations are disabled")
    provided = (request.headers.get("x-admin-key") or "").strip()
    if not provided:
        auth = (request.headers.get("authorization") or "").strip()
        if auth.lower().startswith("bearer "):
            provided = auth.split(" ", 1)[-1].strip()
    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(403, "Forbidden")
