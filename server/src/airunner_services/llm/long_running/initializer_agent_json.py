"""JSON extraction helpers for initializer-agent generation."""

from __future__ import annotations

import json
import re
from typing import Optional


def extract_json_from_response(content: str) -> Optional[str]:
    """Extract one JSON array from an LLM response."""
    json_match = re.search(r"\[[\s\S]*\]", content)
    if json_match and is_valid_json(json_match.group()):
        return json_match.group()
    if is_valid_json(content):
        return content
    return None


def is_valid_json(content: str) -> bool:
    """Return whether one string parses as JSON."""
    try:
        json.loads(content)
        return True
    except json.JSONDecodeError:
        return False
