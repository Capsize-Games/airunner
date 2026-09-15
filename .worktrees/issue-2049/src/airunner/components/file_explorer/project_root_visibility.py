"""Helpers for showing multiple workspace roots in one tree view."""

import os


def normalize_root_paths(paths: list[str]) -> list[str]:
    """Return normalized absolute root paths in stable order."""
    normalized_paths: list[str] = []
    seen_paths: set[str] = set()
    for path in paths:
        normalized = os.path.normpath(os.path.abspath(path))
        if normalized in seen_paths:
            continue
        normalized_paths.append(normalized)
        seen_paths.add(normalized)
    return normalized_paths


def common_parent_for_roots(root_paths: list[str]) -> str:
    """Return the common parent directory for configured roots."""
    normalized_paths = normalize_root_paths(root_paths)
    if not normalized_paths:
        return os.path.normpath(os.getcwd())
    if len(normalized_paths) == 1:
        return normalized_paths[0]
    return os.path.commonpath(normalized_paths)


def path_visible_in_roots(
    candidate_path: str,
    root_paths: list[str],
    common_parent: str,
) -> bool:
    """Return whether a tree path should remain visible."""
    normalized_candidate = os.path.normpath(os.path.abspath(candidate_path))
    normalized_parent = os.path.normpath(os.path.abspath(common_parent))
    for root_path in normalize_root_paths(root_paths):
        if _is_within(normalized_candidate, root_path):
            return True
        if _is_within(root_path, normalized_candidate):
            return _is_within(normalized_candidate, normalized_parent)
    return normalized_candidate == normalized_parent


def is_configured_root(candidate_path: str, root_paths: list[str]) -> bool:
    """Return whether a path is one of the configured workspace roots."""
    normalized_candidate = os.path.normpath(os.path.abspath(candidate_path))
    return normalized_candidate in normalize_root_paths(root_paths)


def _is_within(candidate_path: str, parent_path: str) -> bool:
    """Return whether a path is equal to or nested inside a parent."""
    try:
        return os.path.commonpath([candidate_path, parent_path]) == parent_path
    except ValueError:
        return False