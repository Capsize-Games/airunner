"""Boundary tests for the layered service and shared runtime surfaces."""

from __future__ import annotations

from pathlib import Path


def _iter_runtime_python_files(
    root: Path,
    *,
    excluded_parts: set[str],
) -> list[Path]:
    """Return runtime source files while skipping tests and history."""
    return sorted(
        path
        for path in root.rglob("*.py")
        if not any(part in excluded_parts for part in path.parts)
    )


def test_service_runtime_sources_do_not_import_qt_or_qsettings() -> None:
    """Service runtime modules should stay free of Qt and QSettings."""
    repo_root = Path(__file__).resolve().parents[4]
    service_root = repo_root / "services" / "src" / "airunner_services"
    runtime_files = _iter_runtime_python_files(
        service_root,
        excluded_parts={"tests", "alembic"},
    )

    for path in runtime_files:
        source = path.read_text(encoding="utf-8")
        assert "from PySide6" not in source, path.as_posix()
        assert "import PySide6" not in source, path.as_posix()
        assert "shared_qsettings" not in source, path.as_posix()
        assert "QSettings" not in source, path.as_posix()


def test_shared_runtime_directory_is_removed() -> None:
    """The legacy shared package directory should be fully deleted."""
    repo_root = Path(__file__).resolve().parents[4]

    assert not (repo_root / "shared").exists()