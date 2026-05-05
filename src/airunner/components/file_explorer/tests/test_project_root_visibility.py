"""Unit tests for multi-root file-explorer visibility helpers."""

from airunner.components.file_explorer.project_root_visibility import (
    common_parent_for_roots,
    is_configured_root,
    normalize_root_paths,
    path_visible_in_roots,
)


def test_normalize_root_paths_removes_duplicates(tmp_path):
    """Duplicate root paths should collapse to one normalized entry."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    roots = normalize_root_paths([str(workspace), str(workspace)])

    assert roots == [str(workspace)]


def test_common_parent_for_roots_uses_single_root_verbatim(tmp_path):
    """Single-root explorers should keep the existing root behavior."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    assert common_parent_for_roots([str(workspace)]) == str(workspace)


def test_path_visible_in_roots_keeps_selected_roots_and_children(tmp_path):
    """Multi-root filtering should keep only chosen roots and descendants."""
    workspace = tmp_path / "workspace"
    shared = tmp_path / "shared"
    ignored = tmp_path / "ignored"
    child = workspace / "pkg"
    workspace.mkdir()
    shared.mkdir()
    ignored.mkdir()
    child.mkdir()
    common_parent = common_parent_for_roots([str(workspace), str(shared)])

    assert path_visible_in_roots(
        str(workspace),
        [str(workspace), str(shared)],
        common_parent,
    )
    assert path_visible_in_roots(
        str(child),
        [str(workspace), str(shared)],
        common_parent,
    )
    assert not path_visible_in_roots(
        str(ignored),
        [str(workspace), str(shared)],
        common_parent,
    )


def test_is_configured_root_matches_exact_root_only(tmp_path):
    """Configured-root checks should not treat children as root nodes."""
    workspace = tmp_path / "workspace"
    child = workspace / "pkg"
    workspace.mkdir()
    child.mkdir()

    assert is_configured_root(str(workspace), [str(workspace)])
    assert not is_configured_root(str(child), [str(workspace)])