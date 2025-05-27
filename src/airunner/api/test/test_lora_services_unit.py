"""
Unit tests for LoraAPIServices.
Tests signal emission for LoRA (Low-Rank Adaptation) operations.
"""

import pytest
from unittest.mock import MagicMock
from airunner.api.lora_services import LoraAPIServices
from airunner.enums import SignalCode


class TestLoraAPIServices:
    """Test cases for LoraAPIServices"""

    @pytest.fixture
    def mock_emit_signal(self):
        """Mock the emit_signal property to capture signal emissions"""
        mock_emit_signal = MagicMock()
        return mock_emit_signal

    @pytest.fixture
    def lora_service(self, mock_emit_signal):
        """Create LoraAPIServices instance with mocked emit_signal"""
        service = LoraAPIServices(emit_signal=mock_emit_signal)
        yield service

    def test_update_happy_path(self, lora_service, mock_emit_signal):
        """Test update operation"""
        lora_service.update()

        mock_emit_signal.assert_called_once_with(SignalCode.LORA_UPDATE_SIGNAL)

    def test_status_changed_happy_path(self, lora_service, mock_emit_signal):
        """Test status_changed operation"""
        lora_service.status_changed()

        mock_emit_signal.assert_called_once_with(SignalCode.LORA_STATUS_CHANGED)

    def test_delete_with_widget(self, lora_service, mock_emit_signal):
        """Test delete with lora widget object"""
        lora_widget = MagicMock()
        lora_widget.name = "test_lora"

        lora_service.delete(lora_widget)

        mock_emit_signal.assert_called_once_with(
            SignalCode.LORA_DELETE_SIGNAL, {"lora_widget": lora_widget}
        )

    def test_delete_with_none_widget(self, lora_service, mock_emit_signal):
        """Test delete with None widget"""
        lora_service.delete(None)

        mock_emit_signal.assert_called_once_with(
            SignalCode.LORA_DELETE_SIGNAL, {"lora_widget": None}
        )

    def test_delete_with_string_widget(self, lora_service, mock_emit_signal):
        """Test delete with string widget identifier"""
        lora_widget = "lora_widget_123"

        lora_service.delete(lora_widget)

        mock_emit_signal.assert_called_once_with(
            SignalCode.LORA_DELETE_SIGNAL, {"lora_widget": lora_widget}
        )

    def test_delete_with_dict_widget(self, lora_service, mock_emit_signal):
        """Test delete with dictionary widget data"""
        lora_widget = {
            "id": "lora_001",
            "name": "portrait_style",
            "path": "/models/lora/portrait.safetensors",
        }

        lora_service.delete(lora_widget)

        mock_emit_signal.assert_called_once_with(
            SignalCode.LORA_DELETE_SIGNAL, {"lora_widget": lora_widget}
        )

    def test_all_methods_called_sequentially(self, lora_service, mock_emit_signal):
        """Test calling all methods in sequence"""
        lora_widget = {"id": "test_lora"}

        # Call all methods
        lora_service.update()
        lora_service.status_changed()
        lora_service.delete(lora_widget)

        # Verify all calls were made
        assert mock_emit_signal.call_count == 3
        calls = mock_emit_signal.call_args_list

        assert calls[0][0] == (SignalCode.LORA_UPDATE_SIGNAL,)
        assert calls[1][0] == (SignalCode.LORA_STATUS_CHANGED,)
        assert calls[2][0] == (
            SignalCode.LORA_DELETE_SIGNAL,
            {"lora_widget": lora_widget},
        )

    def test_multiple_updates(self, lora_service, mock_emit_signal):
        """Test multiple update calls"""
        lora_service.update()
        lora_service.update()
        lora_service.update()

        assert mock_emit_signal.call_count == 3
        for call in mock_emit_signal.call_args_list:
            assert call[0] == (SignalCode.LORA_UPDATE_SIGNAL,)

    def test_multiple_status_changes(self, lora_service, mock_emit_signal):
        """Test multiple status_changed calls"""
        lora_service.status_changed()
        lora_service.status_changed()

        assert mock_emit_signal.call_count == 2
        for call in mock_emit_signal.call_args_list:
            assert call[0] == (SignalCode.LORA_STATUS_CHANGED,)
