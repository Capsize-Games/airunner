"""Tests for filter_parameter_widget.py

Tests the FilterParameterWidget and related functionality.
"""

from unittest.mock import MagicMock


class TestFilterParameterWidgetCallbackSignature:
    """Test that filter parameter widget callback signatures are correct."""

    def test_value_changed_callback_no_extra_args(self, qapp):
        """Test that _handle_value_changed calls on_value_changed with
        no extra arguments.

        Regression test for bug where callback was being called with
        (filter_value.name, value) which caused TypeError when
        preview_filter() expects no arguments beyond self.
        """
        from airunner.components.art.gui.widgets.filter_parameter_widget import (
            FilterParameterWidget,
        )
        from airunner.components.art.utils.image_filter_utils import (
            FilterValueData,
        )
        from airunner.components.art.data.image_filter_value import (
            ImageFilterValue,
        )

        # Create a mock callback
        mock_callback = MagicMock()

        # Create a mock ImageFilterValue for FilterValueData
        mock_filter_value = MagicMock(spec=ImageFilterValue)
        mock_filter_value.id = 1
        mock_filter_value.name = "test_param"
        mock_filter_value.value = 5
        mock_filter_value.value_type = "int"
        mock_filter_value.min_value = 0
        mock_filter_value.max_value = 10
        mock_filter_value.image_filter_id = 1

        filter_value_data = FilterValueData(mock_filter_value)

        # Create filter widget with a filter value
        widget = FilterParameterWidget(
            filter_value=filter_value_data,
            on_value_changed=mock_callback,
        )

        # Simulate value change
        widget._handle_value_changed(5)

        # Verify callback was called with no arguments
        # (beyond self which is implicit)
        mock_callback.assert_called_once_with()
