"""Canvas layer settings scope regression tests (issue #2489).

BrushSettings and MetadataSettings are global singletons with no
``layer_id`` column and no relationship to CanvasLayer; only
DrawingPadSettings, ImageToImageSettings and OutpaintSettings are
layer-scoped. These tests pin that scope so the removed dead TODO
design (a commented-out ``layer`` relationship that could never map)
does not come back as a half-wired FK, and so ``create_new_layer``
does not duplicate global rows once per layer.
"""

from __future__ import annotations

import pytest
from sqlalchemy import inspect as sa_inspect

from airunner_services.api.services.canvas_services import CanvasAPIService
from airunner_services.database import reset_engine, setup_database
from airunner_services.database.models.brush_settings import BrushSettings
from airunner_services.database.models.drawingpad_settings import (
    DrawingPadSettings,
)
from airunner_services.database.models.image_to_image_settings import (
    ImageToImageSettings,
)
from airunner_services.database.models.metadata_settings import (
    MetadataSettings,
)
from airunner_services.database.models.outpaint_settings import (
    OutpaintSettings,
)


@pytest.fixture()
def test_db(tmp_path, monkeypatch) -> str:
    """Point the ORM at a temp SQLite file."""
    db_url = f"sqlite:///{tmp_path / 'canvas_layer_scope.sqlite'}"
    monkeypatch.setenv("AIRUNNER_DATABASE_URL", db_url)
    monkeypatch.setenv("AIRUNNER_DISABLE_DB_SETUP_CACHE", "1")
    reset_engine()
    setup_database()
    return db_url


def test_global_settings_have_no_layer_scope(test_db: str) -> None:
    """Brush/metadata settings carry no layer FK or relationship."""
    for model in (BrushSettings, MetadataSettings):
        columns = {column.name for column in sa_inspect(model).columns}
        relationships = set(sa_inspect(model).relationships.keys())
        assert "layer_id" not in columns
        assert "layer" not in relationships


def _service_without_layer_signals() -> CanvasAPIService:
    """Return a canvas service with layer signals neutralized.

    ``begin/commit/cancel_layer_operation`` resolve signal codes that
    do not exist in the shared ``SignalCode`` enum (pre-existing gap,
    unrelated to layer settings scope); stub them so this test
    exercises only the database writes under test.
    """
    service = CanvasAPIService()
    service.begin_layer_operation = lambda *a, **k: None
    service.commit_layer_operation = lambda *a, **k: None
    service.cancel_layer_operation = lambda *a, **k: None
    return service


def test_layer_scoped_settings_round_trip_layer_id(test_db: str) -> None:
    """Per-layer settings persist against their canvas layer row."""
    service = _service_without_layer_signals()
    layer = service.create_new_layer(name="scope-probe")
    assert layer is not None

    for model in (
        DrawingPadSettings,
        ImageToImageSettings,
        OutpaintSettings,
    ):
        row = model.objects.filter_by_first(layer_id=layer.id)
        assert row is not None
        assert row.layer_id == layer.id


def test_create_new_layer_does_not_duplicate_globals(
    test_db: str,
) -> None:
    """One new layer adds no brush/metadata rows (global singletons)."""
    service = _service_without_layer_signals()
    assert BrushSettings.objects.all() == []
    assert MetadataSettings.objects.all() == []

    layer = service.create_new_layer(name="no-global-dupes")
    assert layer is not None

    assert BrushSettings.objects.all() == []
    assert MetadataSettings.objects.all() == []
