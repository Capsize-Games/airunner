"""
Unit tests for ImageFilterAPIServices.
Tests signal emission for image filter operations.
"""

import pytest
from unittest.mock import MagicMock
from airunner.api.image_filter_services import ImageFilterAPIServices
from airunner.enums import SignalCode


class TestImageFilterAPIServices:
    """Test cases for ImageFilterAPIServices"""

    @pytest.fixture
    def mock_emit_signal(self):
        """Mock the emit_signal property to capture signal emissions"""
        mock_emit_signal = MagicMock()
        return mock_emit_signal

    @pytest.fixture
    def filter_service(self, mock_emit_signal):
        """Create ImageFilterAPIServices instance with mocked emit_signal"""
        service = ImageFilterAPIServices(emit_signal=mock_emit_signal)
        yield service

    def test_cancel_happy_path(self, filter_service, mock_emit_signal):
        """Test cancel operation"""
        filter_service.cancel()

        mock_emit_signal.assert_called_once_with(SignalCode.CANVAS_CANCEL_FILTER_SIGNAL)

    def test_apply_with_filter_object(self, filter_service, mock_emit_signal):
        """Test apply with filter object"""
        filter_object = {"type": "blur", "radius": 5}

        filter_service.apply(filter_object)

        mock_emit_signal.assert_called_once_with(
            SignalCode.CANVAS_APPLY_FILTER_SIGNAL,
            {"filter_object": filter_object},
        )

    def test_apply_with_none_filter(self, filter_service, mock_emit_signal):
        """Test apply with None filter object"""
        filter_service.apply(None)

        mock_emit_signal.assert_called_once_with(
            SignalCode.CANVAS_APPLY_FILTER_SIGNAL, {"filter_object": None}
        )

    def test_apply_with_complex_filter(self, filter_service, mock_emit_signal):
        """Test apply with complex filter object"""
        filter_object = {
            "type": "composite",
            "filters": [
                {"type": "blur", "radius": 3},
                {"type": "brightness", "value": 1.2},
            ],
            "blend_mode": "multiply",
        }

        filter_service.apply(filter_object)

        mock_emit_signal.assert_called_once_with(
            SignalCode.CANVAS_APPLY_FILTER_SIGNAL,
            {"filter_object": filter_object},
        )

    def test_preview_with_filter_object(self, filter_service, mock_emit_signal):
        """Test preview with filter object"""
        filter_object = {"type": "sharpen", "amount": 0.5}

        filter_service.preview(filter_object)

        mock_emit_signal.assert_called_once_with(
            SignalCode.CANVAS_PREVIEW_FILTER_SIGNAL,
            {"filter_object": filter_object},
        )

    def test_preview_with_none_filter(self, filter_service, mock_emit_signal):
        """Test preview with None filter object"""
        filter_service.preview(None)

        mock_emit_signal.assert_called_once_with(
            SignalCode.CANVAS_PREVIEW_FILTER_SIGNAL, {"filter_object": None}
        )

    def test_preview_with_string_filter(self, filter_service, mock_emit_signal):
        """Test preview with string filter object"""
        filter_object = "grayscale"

        filter_service.preview(filter_object)

        mock_emit_signal.assert_called_once_with(
            SignalCode.CANVAS_PREVIEW_FILTER_SIGNAL,
            {"filter_object": filter_object},
        )

    def test_all_methods_called_sequentially(self, filter_service, mock_emit_signal):
        """Test calling all methods in sequence"""
        filter_object = {"type": "sepia"}

        # Call all methods
        filter_service.cancel()
        filter_service.apply(filter_object)
        filter_service.preview(filter_object)

        # Verify all calls were made
        assert mock_emit_signal.call_count == 3
        calls = mock_emit_signal.call_args_list

        assert calls[0][0] == (SignalCode.CANVAS_CANCEL_FILTER_SIGNAL,)
        assert calls[1][0] == (
            SignalCode.CANVAS_APPLY_FILTER_SIGNAL,
            {"filter_object": filter_object},
        )
        assert calls[2][0] == (
            SignalCode.CANVAS_PREVIEW_FILTER_SIGNAL,
            {"filter_object": filter_object},
        )
