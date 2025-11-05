"""Integration tests for filter system with database."""

import pytest
from PIL import Image
import numpy as np

from airunner.components.art.data.image_filter import ImageFilter
from airunner.components.art.data.image_filter_value import ImageFilterValue
from airunner.components.art.utils.image_filter_utils import (
    get_filter_values,
    build_filter_instance,
)


class TestFilterDatabaseIntegration:
    """Integration tests for filter system with database."""

    @pytest.fixture
    def test_image(self):
        """Create a test image."""
        img_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        return Image.fromarray(img_array, "RGB")

    def test_pixel_art_filter_from_database(self, test_image):
        """Test loading and applying pixel_art filter from database."""
        # Get filter from database
        filters = ImageFilter.objects.filter_by(name="pixel_art")

        if not filters:
            pytest.skip("pixel_art filter not in database")

        filter_obj = filters[0]

        # Get filter values
        filter_values = get_filter_values(filter_obj.id)

        assert len(filter_values) > 0, "No filter values found"

        # Build filter instance
        filter_instance = build_filter_instance("pixel_art")

        assert filter_instance is not None, "Failed to build filter instance"

        # Apply filter
        result = filter_instance.filter(test_image)

        assert result is not None
        assert isinstance(result, Image.Image)
        assert result.size == test_image.size

    def test_all_filters_can_be_built(self):
        """Test that all filters in database can be instantiated."""
        all_filters = ImageFilter.objects.all()

        failed_filters = []

        for filter_obj in all_filters:
            try:
                instance = build_filter_instance(filter_obj.name)
                if instance is None:
                    failed_filters.append(
                        (
                            filter_obj.name,
                            "build_filter_instance returned None",
                        )
                    )
            except Exception as e:
                failed_filters.append((filter_obj.name, str(e)))

        assert (
            len(failed_filters) == 0
        ), f"Failed to build filters: {failed_filters}"

    def test_pixel_art_filter_parameters_are_valid(self):
        """Test pixel_art filter parameters have correct types and ranges."""
        filters = ImageFilter.objects.filter_by(name="pixel_art")

        if not filters:
            pytest.skip("pixel_art filter not in database")

        filter_obj = filters[0]
        values = ImageFilterValue.objects.filter_by(
            image_filter_id=filter_obj.id
        )

        # Expected parameters
        expected_params = {
            "number_of_colors": {"type": "int", "min": 2, "max": 1024},
            "base_size": {"type": "int", "min": 2, "max": 256},
            "smoothing": {"type": "int", "min": 0, "max": 100},
        }

        for value in values:
            if value.name in expected_params:
                expected = expected_params[value.name]

                # Check type
                assert (
                    value.value_type == expected["type"]
                ), f"{value.name} should be {expected['type']}, got {value.value_type}"

                # Check min/max are set
                assert (
                    value.min_value is not None
                ), f"{value.name} missing min_value"
                assert (
                    value.max_value is not None
                ), f"{value.name} missing max_value"

                # Check min/max values are correct
                min_val = float(value.min_value)
                max_val = float(value.max_value)

                assert (
                    min_val == expected["min"]
                ), f"{value.name} min should be {expected['min']}, got {min_val}"
                assert (
                    max_val == expected["max"]
                ), f"{value.name} max should be {expected['max']}, got {max_val}"

    def test_filter_value_conversion_works(self):
        """Test that filter values convert correctly from strings."""
        filters = ImageFilter.objects.filter_by(name="pixel_art")

        if not filters:
            pytest.skip("pixel_art filter not in database")

        filter_obj = filters[0]
        values = ImageFilterValue.objects.filter_by(
            image_filter_id=filter_obj.id
        )

        for value in values:
            # All values should be stored as strings
            assert isinstance(
                value.value, str
            ), f"{value.name} value should be string, got {type(value.value)}"

            # But should be convertible to their type
            if value.value_type == "int":
                try:
                    int(value.value)
                except ValueError:
                    pytest.fail(
                        f"{value.name} value '{value.value}' not convertible to int"
                    )
            elif value.value_type == "float":
                try:
                    float(value.value)
                except ValueError:
                    pytest.fail(
                        f"{value.name} value '{value.value}' not convertible to float"
                    )

    def test_filter_with_corrupted_zero_value_fails_gracefully(
        self, test_image
    ):
        """Test that filter handles corrupted zero value gracefully."""
        # Simulate corrupted value (like the bug we fixed)
        from airunner.components.art.filters.pixel_art import PixelFilter

        # Create filter with zero colors (corrupted state)
        filter_instance = PixelFilter(
            number_of_colors=0, base_size=256, smoothing=0
        )

        # Should not crash
        result = filter_instance.filter(test_image)

        # Should return an image (even if unchanged)
        assert result is not None
        assert isinstance(result, Image.Image)
