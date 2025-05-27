"""
Unit tests for EmbeddingAPIServices.
Covers all signal emission paths: happy, unhappy, and bad inputs.
"""

import pytest
from unittest.mock import MagicMock
from airunner.api.embedding_services import EmbeddingAPIServices
from airunner.enums import SignalCode


class TestEmbeddingAPIServices:
    @pytest.fixture
    def mock_emit_signal(self):
        return MagicMock()

    @pytest.fixture
    def embedding_service(self, mock_emit_signal):
        service = EmbeddingAPIServices(emit_signal=mock_emit_signal)
        yield service

    def test_delete_happy_path(self, embedding_service, mock_emit_signal):
        widget = MagicMock()
        embedding_service.delete(widget)
        mock_emit_signal.assert_called_once_with(
            SignalCode.EMBEDDING_DELETE_SIGNAL, {"embedding_widget": widget}
        )

    def test_delete_none(self, embedding_service, mock_emit_signal):
        embedding_service.delete(None)
        mock_emit_signal.assert_called_once_with(
            SignalCode.EMBEDDING_DELETE_SIGNAL, {"embedding_widget": None}
        )

    def test_delete_string(self, embedding_service, mock_emit_signal):
        embedding_service.delete("widget_id")
        mock_emit_signal.assert_called_once_with(
            SignalCode.EMBEDDING_DELETE_SIGNAL,
            {"embedding_widget": "widget_id"},
        )

    def test_status_changed(self, embedding_service, mock_emit_signal):
        embedding_service.status_changed()
        mock_emit_signal.assert_called_once_with(SignalCode.EMBEDDING_STATUS_CHANGED)

    def test_update(self, embedding_service, mock_emit_signal):
        embedding_service.update()
        mock_emit_signal.assert_called_once_with(SignalCode.EMBEDDING_UPDATE_SIGNAL)

    def test_get_all_results_happy(self, embedding_service, mock_emit_signal):
        embeddings = [1, 2, 3]
        embedding_service.get_all_results(embeddings)
        mock_emit_signal.assert_called_once_with(
            SignalCode.EMBEDDING_GET_ALL_RESULTS_SIGNAL,
            {"embeddings": embeddings},
        )

    def test_get_all_results_empty(self, embedding_service, mock_emit_signal):
        embedding_service.get_all_results([])
        mock_emit_signal.assert_called_once_with(
            SignalCode.EMBEDDING_GET_ALL_RESULTS_SIGNAL, {"embeddings": []}
        )

    def test_get_all_results_none(self, embedding_service, mock_emit_signal):
        embedding_service.get_all_results(None)
        mock_emit_signal.assert_called_once_with(
            SignalCode.EMBEDDING_GET_ALL_RESULTS_SIGNAL, {"embeddings": None}
        )

    def test_get_all_results_invalid_type(self, embedding_service, mock_emit_signal):
        embedding_service.get_all_results(42)
        mock_emit_signal.assert_called_once_with(
            SignalCode.EMBEDDING_GET_ALL_RESULTS_SIGNAL, {"embeddings": 42}
        )
