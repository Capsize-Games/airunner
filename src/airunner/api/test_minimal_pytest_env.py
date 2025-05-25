import sys
import types
import pytest
from unittest.mock import MagicMock


def test_import_art_services():
    import airunner.api.art_services

    assert True


def test_minimal():
    assert True


def test_art_service_instantiation():
    # Insert dummy modules/classes into sys.modules for dynamic import in ARTAPIService.__init__
    sys.modules["airunner.api.canvas_services"] = types.SimpleNamespace(
        CanvasAPIService=MagicMock()
    )
    sys.modules["airunner.api.embedding_services"] = types.SimpleNamespace(
        EmbeddingAPIServices=MagicMock()
    )
    sys.modules["airunner.api.lora_services"] = types.SimpleNamespace(
        LoraAPIServices=MagicMock()
    )
    sys.modules["airunner.api.image_filter_services"] = types.SimpleNamespace(
        ImageFilterAPIServices=MagicMock()
    )
    from airunner.api.art_services import ARTAPIService

    service = ARTAPIService(emit_signal=lambda *a, **kw: None)
    assert service is not None
