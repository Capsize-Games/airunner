"""Unit tests for image filter utilities."""

import pytest
from unittest.mock import Mock, patch

from airunner.components.art.utils.image_filter_utils import (
    FilterValueData,
    build_filter_kwargs,
    build_filter_instance,
)
from airunner.components.art.filters.pixel_art import PixelFilter


class TestFilterValueData:
    """Test suite for FilterValueData."""

    @pytest.fixture
    def mock_filter_value(self):
        """Create a mock ImageFilterValue."""
        mock = Mock()
        mock.id = 1
        mock.name = "test_param"
        mock.value = "42"
        mock.value_type = "int"
        mock.min_value = "0"
        mock.max_value = "100"
        mock.image_filter_id = 1
        return mock

    def test_filter_value_data_initialization(self, mock_filter_value):
        """Test FilterValueData initializes correctly."""
        fvd = FilterValueData(mock_filter_value)

        assert fvd.id == 1
        assert fvd.name == "test_param"
        assert fvd.value == "42"
        assert fvd.value_type == "int"
        assert fvd.min_value == "0"
        assert fvd.max_value == "100"
        assert fvd.image_filter_id == 1

    def test_filter_value_data_to_dict(self, mock_filter_value):
        """Test FilterValueData.to_dict() method."""
        fvd = FilterValueData(mock_filter_value)

        result = fvd.to_dict()

        assert isinstance(result, dict)
        assert result["id"] == 1
        assert result["name"] == "test_param"
        assert result["value"] == "42"


class TestBuildFilterKwargs:
    """Test suite for build_filter_kwargs function."""

    def test_build_kwargs_with_int_values(self):
        """Test building kwargs with integer values."""
        mock_fv = Mock()
        mock_fv.name = "number_of_colors"
        mock_fv.value = "24"
        mock_fv.value_type = "int"

        filter_values = [FilterValueData(mock_fv)]

        kwargs = build_filter_kwargs(filter_values)

        assert kwargs["number_of_colors"] == 24
        assert isinstance(kwargs["number_of_colors"], int)

    def test_build_kwargs_with_float_values(self):
        """Test building kwargs with float values."""
        mock_fv = Mock()
        mock_fv.name = "radius"
        mock_fv.value = "2.5"
        mock_fv.value_type = "float"

        filter_values = [FilterValueData(mock_fv)]

        kwargs = build_filter_kwargs(filter_values)

        assert kwargs["radius"] == 2.5
        assert isinstance(kwargs["radius"], float)

    def test_build_kwargs_with_bool_values(self):
        """Test building kwargs with boolean values."""
        mock_fv_true = Mock()
        mock_fv_true.name = "enabled"
        mock_fv_true.value = "True"
        mock_fv_true.value_type = "bool"

        mock_fv_false = Mock()
        mock_fv_false.name = "disabled"
        mock_fv_false.value = "False"
        mock_fv_false.value_type = "bool"

        filter_values = [
            FilterValueData(mock_fv_true),
            FilterValueData(mock_fv_false),
        ]

        kwargs = build_filter_kwargs(filter_values)

        assert kwargs["enabled"] is True
        assert kwargs["disabled"] is False

    def test_build_kwargs_with_overrides(self):
        """Test building kwargs with parameter overrides."""
        mock_fv = Mock()
        mock_fv.name = "number_of_colors"
        mock_fv.value = "24"
        mock_fv.value_type = "int"

        filter_values = [FilterValueData(mock_fv)]
        overrides = {"number_of_colors": 48}

        kwargs = build_filter_kwargs(filter_values, overrides)

        # Override should take precedence
        assert kwargs["number_of_colors"] == 48

    def test_build_kwargs_handles_invalid_int(self):
        """Test building kwargs handles invalid int conversion."""
        mock_fv = Mock()
        mock_fv.name = "number_of_colors"
        mock_fv.value = "invalid"
        mock_fv.value_type = "int"

        filter_values = [FilterValueData(mock_fv)]

        kwargs = build_filter_kwargs(filter_values)

        # Should keep original value on conversion failure
        assert kwargs["number_of_colors"] == "invalid"

    def test_build_kwargs_handles_invalid_float(self):
        """Test building kwargs handles invalid float conversion."""
        mock_fv = Mock()
        mock_fv.name = "radius"
        mock_fv.value = "not_a_float"
        mock_fv.value_type = "float"

        filter_values = [FilterValueData(mock_fv)]

        kwargs = build_filter_kwargs(filter_values)

        # Should keep original value on conversion failure
        assert kwargs["radius"] == "not_a_float"

    def test_build_kwargs_with_multiple_values(self):
        """Test building kwargs with multiple filter values."""
        mock_fv1 = Mock()
        mock_fv1.name = "number_of_colors"
        mock_fv1.value = "24"
        mock_fv1.value_type = "int"

        mock_fv2 = Mock()
        mock_fv2.name = "base_size"
        mock_fv2.value = "256"
        mock_fv2.value_type = "int"

        mock_fv3 = Mock()
        mock_fv3.name = "smoothing"
        mock_fv3.value = "0"
        mock_fv3.value_type = "int"

        filter_values = [
            FilterValueData(mock_fv1),
            FilterValueData(mock_fv2),
            FilterValueData(mock_fv3),
        ]

        kwargs = build_filter_kwargs(filter_values)

        assert len(kwargs) == 3
        assert kwargs["number_of_colors"] == 24
        assert kwargs["base_size"] == 256
        assert kwargs["smoothing"] == 0


class TestBuildFilterInstance:
    """Test suite for build_filter_instance function."""

    @patch(
        "airunner.components.art.utils.image_filter_utils.get_filter_by_name"
    )
    @patch(
        "airunner.components.art.utils.image_filter_utils.get_filter_values"
    )
    def test_build_pixel_filter_instance(
        self, mock_get_values, mock_get_filter
    ):
        """Test building a PixelFilter instance."""
        # Mock the filter
        mock_filter = Mock()
        mock_filter.id = 1
        mock_filter.name = "pixel_art"
        mock_filter.filter_class = "PixelFilter"
        mock_get_filter.return_value = mock_filter

        # Mock the filter values
        mock_fv1 = Mock()
        mock_fv1.name = "number_of_colors"
        mock_fv1.value = "24"
        mock_fv1.value_type = "int"

        mock_fv2 = Mock()
        mock_fv2.name = "base_size"
        mock_fv2.value = "256"
        mock_fv2.value_type = "int"

        mock_fv3 = Mock()
        mock_fv3.name = "smoothing"
        mock_fv3.value = "0"
        mock_fv3.value_type = "int"

        mock_get_values.return_value = [
            FilterValueData(mock_fv1),
            FilterValueData(mock_fv2),
            FilterValueData(mock_fv3),
        ]

        # Build the filter
        result = build_filter_instance("pixel_art")

        assert result is not None
        assert isinstance(result, PixelFilter)
        assert result.number_of_colors == 24
        assert result.base_size == 256
        assert result.smoothing == 0

    @patch(
        "airunner.components.art.utils.image_filter_utils.get_filter_by_name"
    )
    def test_build_filter_instance_not_found(self, mock_get_filter):
        """Test building filter when filter not found."""
        mock_get_filter.return_value = None

        result = build_filter_instance("nonexistent_filter")

        assert result is None

    @patch(
        "airunner.components.art.utils.image_filter_utils.get_filter_by_name"
    )
    @patch(
        "airunner.components.art.utils.image_filter_utils.get_filter_values"
    )
    def test_build_filter_with_overrides(
        self, mock_get_values, mock_get_filter
    ):
        """Test building filter with parameter overrides."""
        # Mock the filter
        mock_filter = Mock()
        mock_filter.id = 1
        mock_filter.name = "pixel_art"
        mock_filter.filter_class = "PixelFilter"
        mock_get_filter.return_value = mock_filter

        # Mock the filter values
        mock_fv = Mock()
        mock_fv.name = "number_of_colors"
        mock_fv.value = "24"
        mock_fv.value_type = "int"

        mock_get_values.return_value = [FilterValueData(mock_fv)]

        # Build with override
        overrides = {"number_of_colors": 48}
        result = build_filter_instance("pixel_art", overrides)

        assert result is not None
        assert result.number_of_colors == 48
