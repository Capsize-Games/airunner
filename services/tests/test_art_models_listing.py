"""Regression tests for issue #2228.

GET /api/v1/art/models must list every installed art model grouped
by version (with the ``model`` value to send) plus the valid
schedulers, and must never fail with a 500 when the database is
missing, empty, or returns an unusable settings record.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import DetachedInstanceError

import airunner_services.api.routes.art_model_base as model_base_mod
from airunner_common.contract_enums import Scheduler
from airunner_services.api.server import create_app
from airunner_services.database.base import BaseModel
from airunner_services.database.db.engine import (
    create_configured_engine,
)
from airunner_services.database.models.path_settings import PathSettings
from airunner_services.database.models.schedulers import Schedulers
from airunner_services.database.session import reset_engine

_ART_MODELS_ROUTE = "/api/v1/art/models"

_TREE: dict[str, bytes] = {
    "art/models/SDXL 1.0/txt2img/sdxl.safetensors": b"0123456789",
    "art/models/Z-Image Turbo/txt2img/z.safetensors": b"abcdef",
    "art/models/Z-Image Turbo/img2img/styled.ckpt": b"gh",
    "art/models/Z-Image Turbo/img2img/bundle/model_index.json": b"{}",
    "art/models/Safety Checker/config.json": b"{}",
    "art/models/civitai/loose.safetensors": b"zz",
    "art/models/Z-Image Turbo/txt2img/notes.txt": b"ignore me",
}


class _FakeApi:
    """Minimal app surface used by the route tests."""

    def __init__(self) -> None:
        self.llm = None

    def emit_signal(self, _code: object, _data: object = None) -> None:
        """Ignore signal emissions during route tests."""

    def worker_response(self, code: object, message: object) -> None:
        """Ignore worker responses during route tests."""


@pytest.fixture
def isolated_db_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[str]:
    """Point the service database at a scratch sqlite file."""
    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "1")
    url = f"sqlite:///{tmp_path / 'models-listing.sqlite3'}"
    monkeypatch.setenv("AIRUNNER_DATABASE_URL", url)
    reset_engine()
    yield url
    reset_engine()


def _write_tree(root: Path) -> Path:
    """Write the scratch models tree and return the models base."""
    for relative, content in _TREE.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return root / "art" / "models"


def _seed_database(
    url: str, base_path: str, schedulers: list[tuple[str, str]]
) -> None:
    """Create tables and seed base path plus scheduler rows."""
    engine = create_configured_engine(url)
    BaseModel.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(PathSettings(base_path=base_path))
    for name, display_name in schedulers:
        session.add(Schedulers(name=name, display_name=display_name))
    session.commit()
    session.close()


def _get_models() -> Response:
    """GET the art models route on a fresh app."""
    app = create_app(
        allowed_origins=["http://localhost"],
        enable_cors=False,
        app_instance=_FakeApi(),
    )
    with TestClient(app) as client:
        return client.get(_ART_MODELS_ROUTE)


def _paths_by_version(body: dict[str, Any]) -> dict[str, list[str]]:
    """Return sorted model paths keyed by version name."""
    grouped: dict[str, list[str]] = {}
    for entry in body["versions"]:
        grouped[entry["version"]] = sorted(
            model["path"] for model in entry["models"]
        )
    return grouped


def _assert_version_groups(
    body: dict[str, Any], models_base: Path
) -> dict[str, list[str]]:
    """Assert the expected per-version groups and return them."""
    grouped = _paths_by_version(body)
    assert sorted(grouped) == ["SDXL 1.0", "Z-Image Turbo"]
    assert grouped["SDXL 1.0"] == [
        str(models_base / "SDXL 1.0" / "txt2img" / "sdxl.safetensors")
    ]
    assert grouped["Z-Image Turbo"] == [
        str(models_base / "Z-Image Turbo" / "img2img" / "bundle"),
        str(models_base / "Z-Image Turbo" / "img2img" / "styled.ckpt"),
        str(models_base / "Z-Image Turbo" / "txt2img" / "z.safetensors"),
    ]
    return grouped


def _assert_flat_models(
    body: dict[str, Any],
    grouped: dict[str, list[str]],
    models_base: Path,
) -> None:
    """Assert the flat list matches the groups with live paths."""
    flat = {model["path"]: model for model in body["models"]}
    assert set(flat) == {path for paths in grouped.values() for path in paths}
    checkpoint = str(models_base / "SDXL 1.0" / "txt2img" / "sdxl.safetensors")
    assert flat[checkpoint]["size_bytes"] == 10
    bundle = str(models_base / "Z-Image Turbo" / "img2img" / "bundle")
    assert flat[bundle]["pipeline"] == "img2img"
    assert all(Path(path).exists() for path in flat)


def test_lists_installed_models_grouped_by_version(
    tmp_path: Path, isolated_db_url: str
) -> None:
    """Every loadable model is listed with its sendable value."""
    models_base = _write_tree(tmp_path)
    _seed_database(isolated_db_url, str(tmp_path), [])
    response = _get_models()
    assert response.status_code == 200
    body = response.json()
    assert body["base_dir"] == str(models_base)
    grouped = _assert_version_groups(body, models_base)
    _assert_flat_models(body, grouped, models_base)


def test_schedulers_come_from_database(
    tmp_path: Path, isolated_db_url: str
) -> None:
    """Stored scheduler display names are the valid values."""
    _write_tree(tmp_path)
    _seed_database(
        isolated_db_url,
        str(tmp_path),
        [
            ("EulerAncestralDiscreteScheduler", "Euler a"),
            ("FlowMatchEulerDiscreteScheduler", "Flow Match Euler"),
        ],
    )
    response = _get_models()
    assert response.status_code == 200
    assert response.json()["schedulers"] == [
        "Euler a",
        "Flow Match Euler",
    ]


def test_schedulers_fall_back_without_tables(
    tmp_path: Path,
    isolated_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing schema still yields contract schedulers plus files."""
    models_base = _write_tree(tmp_path)
    monkeypatch.setattr(model_base_mod, "_DEFAULT_BASE_PATH", tmp_path)
    response = _get_models()
    assert response.status_code == 200
    body = response.json()
    assert body["schedulers"] == [item.value for item in Scheduler]
    assert body["base_dir"] == str(models_base)
    assert len(body["models"]) == 4


def test_poisoned_settings_record_still_serves_filesystem(
    tmp_path: Path,
    isolated_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unreadable settings record must not cause a 500."""
    models_base = _write_tree(tmp_path)

    class _UnreadableRecord:
        """Settings row whose fields raise like a detached row."""

        @property
        def base_path(self) -> str:
            """Raise exactly as an expired ORM attribute does."""
            raise DetachedInstanceError("expired attributes")

    monkeypatch.setattr(
        model_base_mod, "query_first", lambda _model: _UnreadableRecord()
    )
    monkeypatch.setattr(model_base_mod, "_DEFAULT_BASE_PATH", tmp_path)
    response = _get_models()
    assert response.status_code == 200
    body = response.json()
    assert body["base_dir"] == str(models_base)
    assert _paths_by_version(body)["SDXL 1.0"] == [
        str(models_base / "SDXL 1.0" / "txt2img" / "sdxl.safetensors")
    ]
    assert body["schedulers"] == [item.value for item in Scheduler]


def test_empty_models_dir_returns_empty_lists(
    tmp_path: Path, isolated_db_url: str
) -> None:
    """No installed versions is a 200 with empty model lists."""
    models_base = tmp_path / "art" / "models"
    models_base.mkdir(parents=True)
    _seed_database(isolated_db_url, str(tmp_path), [])
    response = _get_models()
    assert response.status_code == 200
    body = response.json()
    assert body["base_dir"] == str(models_base)
    assert body["models"] == []
    assert body["versions"] == []
    assert body["schedulers"] == [item.value for item in Scheduler]
