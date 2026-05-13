"""Tests for icon manager resource resolution."""

from types import SimpleNamespace

from airunner.components.icons.managers import icon_manager as module
from airunner.components.icons.managers.icon_manager import IconManager


def test_resolve_icon_path_prefers_lucide(monkeypatch):
    """Shared names should resolve to Lucide first during migration."""
    paths = {
        ":/dark/icons/lucide/dark/folder.svg": True,
        ":/dark/icons/feather/dark/folder.svg": True,
    }
    manager = IconManager([], SimpleNamespace())

    monkeypatch.setattr(
        module.QFile,
        "exists",
        lambda path: paths.get(path, False),
    )

    assert manager._resolve_icon_path("folder", "dark") == (
        ":/dark/icons/lucide/dark/folder.svg"
    )


def test_resolve_icon_path_falls_back_to_feather(monkeypatch):
    """Legacy Feather-only icons should still resolve correctly."""
    manager = IconManager([], SimpleNamespace())

    monkeypatch.setattr(
        module.QFile,
        "exists",
        lambda path: path == ":/light/icons/feather/light/dice-game-icon.svg",
    )

    assert manager._resolve_icon_path("dice-game-icon", "light") == (
        ":/light/icons/feather/light/dice-game-icon.svg"
    )


def test_resolve_icon_path_supports_explicit_icon_set(monkeypatch):
    """Widgets can opt into a specific icon family during migration."""
    manager = IconManager([], SimpleNamespace())

    monkeypatch.setattr(
        module.QFile,
        "exists",
        lambda path: path == ":/dark/icons/feather/dark/folder.svg",
    )

    assert manager._resolve_icon_path("feather:folder", "dark") == (
        ":/dark/icons/feather/dark/folder.svg"
    )