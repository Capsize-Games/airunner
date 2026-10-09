"""Optional client bundle never fails the boot (issue #2243).

_has_index treats an unreadable bundle directory as absent: the
service user cannot traverse the release build root, and the bundle
is documented as optional.

CPU-only: no model, network, GPU, or database use.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from airunner_services.api.routes import client_bundle


def test_has_index_false_for_missing_dir(tmp_path: Path) -> None:
    """A missing directory simply has no bundle index."""
    assert client_bundle._has_index(tmp_path / "absent") is False


def test_has_index_true_for_index(tmp_path: Path) -> None:
    """A directory with index.html reports its bundle index."""
    (tmp_path / "index.html").write_text("x", encoding="utf-8")
    assert client_bundle._has_index(tmp_path) is True


def test_has_index_false_for_unreadable_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Permission errors count as absent instead of raising."""

    def _raise(self: Path) -> bool:
        raise PermissionError("denied for test")

    monkeypatch.setattr(Path, "is_file", _raise)
    assert client_bundle._has_index(tmp_path) is False
