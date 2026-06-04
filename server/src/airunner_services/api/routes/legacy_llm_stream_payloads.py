"""Payload builders for legacy LLM stream compatibility routes."""

from __future__ import annotations

import json

from fastapi.responses import JSONResponse


def keepalive_payload(action_str: str) -> dict:
    """Return the keepalive payload used for slow legacy stream starts."""
    return {
        "message": "",
        "is_first_message": False,
        "is_end_of_message": False,
        "done": False,
        "sequence_number": 0,
        "action": action_str,
        "keepalive": True,
    }


def timeout_payload(action_str: str) -> dict:
    """Return the timeout payload used for idle legacy LLM streams."""
    return {
        "message": (
            "Error invoking LLM: request timed out waiting for model "
            "output."
        ),
        "is_first_message": True,
        "is_end_of_message": True,
        "done": True,
        "sequence_number": 0,
        "action": action_str,
        "error": True,
    }


def error_payload(message: str, action_str: str) -> bytes:
    """Return the NDJSON error line for one stream failure.

    The message is truncated to prevent internal stack-trace details
    from being exposed to the client.
    """
    safe_message = message[:500] if message else ""
    body = JSONResponse(
        content={
            "message": safe_message,
            "is_first_message": True,
            "is_end_of_message": True,
            "sequence_number": 0,
            "action": action_str,
            "error": True,
        }
    ).body
    return bytes(body or b"") + b"\n"


def ndjson_line(payload: dict) -> bytes:
    """Return one NDJSON line for the given payload dict."""
    body = JSONResponse(content=payload).body
    return bytes(body or b"") + b"\n"
