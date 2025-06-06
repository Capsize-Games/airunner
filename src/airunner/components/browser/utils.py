"""
browser/utils.py

Utility functions for browser-related operations in AI Runner.

This module provides shared helpers for browser widgets, mixins, and tools.
"""

from typing import AnyStr


def normalize_url(url: AnyStr) -> str:
    """
    Normalize a URL for browser navigation.

    Ensures the URL starts with 'https://'. If the URL starts with 'http://', it is upgraded to 'https://'.
    If the URL does not start with 'http', 'https://' is prepended.

    Args:
        url (str): The input URL (may be bare domain, http, or https).

    Returns:
        str: A normalized URL starting with 'https://'.
    """
    url = url.strip()
    if url.startswith("https://"):
        return url
    if url.startswith("http://"):
        return "https://" + url[len("http://") :]
    return "https://" + url
