"""Tests for CanvasLayerMixin layer display functionality.

Verifies that layer items are created correctly with proper image handling.
"""

import pytest
from unittest.mock import MagicMock, patch
from PIL import Image
import io

from airunner.components.art.gui.widgets.canvas.mixins.canvas_layer_mixin import (
    CanvasLayerMixin,
)
from airunner.components.art.data.canvas_layer import CanvasLayer
from airunner.components.art.data.drawingpad_settings import (
    DrawingPadSettings,
)


class TestCanvasLayerMixin:
    """Test suite for CanvasLayerMixin._create_new_layer_item."""

    @pytest.fixture
    def layer_mixin(self, qapp):
        """Create a minimal CanvasLayerMixin instance for testing."""
        # Create mock class with necessary attributes
        mixin = CanvasLayerMixin()
        mixin._layer_items = {}
        mixin.addItem = MagicMock()
        return mixin

    @pytest.fixture
    def sample_layer_data(self):
        """Create sample layer data dict."""
        return {"visible": True, "opacity": 0.8, "order": 1}

    @pytest.fixture
    def sample_image(self):
        """Create a simple PIL Image for testing."""
        img = Image.new("RGB", (100, 100), color="red")
        # Convert to binary format as stored in database
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format="PNG")
        img_byte_arr.seek(0)
        return img_byte_arr.read()

    def test_create_new_layer_item_with_valid_image(
        self, layer_mixin, sample_layer_data, sample_image
    ):
        """Test layer item creation when DrawingPadSettings has valid image."""
        layer_id = 1

        # Mock CanvasLayer.objects.get
        mock_layer = MagicMock()
        mock_layer.id = layer_id

        # Mock DrawingPadSettings.objects.filter_by_first
        mock_drawing_pad = MagicMock()
        mock_drawing_pad.image = sample_image

        # Create mock Qt objects before the test
        mock_qimage = MagicMock()
        mock_item = MagicMock()

        with patch.object(CanvasLayer.objects, "get", return_value=mock_layer):
            with patch.object(
                DrawingPadSettings.objects,
                "filter_by_first",
                return_value=mock_drawing_pad,
            ):
                with patch(
                    "airunner.components.art.gui.widgets.canvas.mixins.canvas_layer_mixin.convert_binary_to_image"
                ) as mock_convert:
                    # Mock successful image conversion
                    mock_pil_image = Image.new("RGB", (100, 100))
                    mock_convert.return_value = mock_pil_image

                    # Mock QImage conversion using the utility function
                    with patch(
                        "airunner.components.art.gui.widgets.canvas.mixins.canvas_layer_mixin.pil_to_qimage",
                        return_value=mock_qimage,
                    ):
                        # Mock LayerImageItem to prevent actual Qt object creation
                        with patch(
                            "airunner.components.art.gui.widgets.canvas.mixins.canvas_layer_mixin.LayerImageItem",
                            return_value=mock_item,
                        ):
                            # Execute
                            layer_mixin._create_new_layer_item(
                                layer_id, sample_layer_data
                            )

                            # Verify
                            mock_convert.assert_called_once_with(sample_image)
                            layer_mixin.addItem.assert_called_once()
                            assert layer_id in layer_mixin._layer_items

    def test_create_new_layer_item_missing_layer(
        self, layer_mixin, sample_layer_data
    ):
        """Test layer item creation fails gracefully when layer not found."""
        layer_id = 999

        with patch.object(CanvasLayer.objects, "get", return_value=None):
            # Execute
            layer_mixin._create_new_layer_item(layer_id, sample_layer_data)

            # Verify - no item should be created
            layer_mixin.addItem.assert_not_called()
            assert layer_id not in layer_mixin._layer_items

    def test_create_new_layer_item_missing_drawing_pad(
        self, layer_mixin, sample_layer_data
    ):
        """Test layer creation fails when DrawingPadSettings not found."""
        layer_id = 1
        mock_layer = MagicMock()
        mock_layer.id = layer_id

        with patch.object(CanvasLayer.objects, "get", return_value=mock_layer):
            with patch.object(
                DrawingPadSettings.objects,
                "filter_by_first",
                return_value=None,
            ):
                # Execute
                layer_mixin._create_new_layer_item(layer_id, sample_layer_data)

                # Verify - no item should be created
                layer_mixin.addItem.assert_not_called()
                assert layer_id not in layer_mixin._layer_items

    def test_create_new_layer_item_no_image_data(
        self, layer_mixin, sample_layer_data
    ):
        """Test layer creation fails when DrawingPadSettings has no image."""
        layer_id = 1
        mock_layer = MagicMock()
        mock_drawing_pad = MagicMock()
        mock_drawing_pad.image = None  # No image data

        with patch.object(CanvasLayer.objects, "get", return_value=mock_layer):
            with patch.object(
                DrawingPadSettings.objects,
                "filter_by_first",
                return_value=mock_drawing_pad,
            ):
                # Execute
                layer_mixin._create_new_layer_item(layer_id, sample_layer_data)

                # Verify - no item should be created
                layer_mixin.addItem.assert_not_called()
                assert layer_id not in layer_mixin._layer_items

    def test_create_new_layer_item_image_conversion_fails(
        self, layer_mixin, sample_layer_data, sample_image
    ):
        """Test layer creation fails when image conversion returns None."""
        layer_id = 1
        mock_layer = MagicMock()
        mock_drawing_pad = MagicMock()
        mock_drawing_pad.image = sample_image

        with patch.object(CanvasLayer.objects, "get", return_value=mock_layer):
            with patch.object(
                DrawingPadSettings.objects,
                "filter_by_first",
                return_value=mock_drawing_pad,
            ):
                with patch(
                    "airunner.components.art.gui.widgets.canvas.mixins.canvas_layer_mixin.convert_binary_to_image",
                    return_value=None,
                ):
                    # Execute
                    layer_mixin._create_new_layer_item(
                        layer_id, sample_layer_data
                    )

                    # Verify - no item should be created
                    layer_mixin.addItem.assert_not_called()
                    assert layer_id not in layer_mixin._layer_items

    def test_create_new_layer_item_qimage_conversion_fails(
        self, layer_mixin, sample_layer_data, sample_image
    ):
        """Test layer creation fails when QImage conversion returns None."""
        layer_id = 1
        mock_layer = MagicMock()
        mock_drawing_pad = MagicMock()
        mock_drawing_pad.image = sample_image
        mock_pil_image = Image.new("RGB", (100, 100))

        with patch.object(CanvasLayer.objects, "get", return_value=mock_layer):
            with patch.object(
                DrawingPadSettings.objects,
                "filter_by_first",
                return_value=mock_drawing_pad,
            ):
                with patch(
                    "airunner.utils.image.convert_binary_to_image",
                    return_value=mock_pil_image,
                ):
                    # Mock QImage conversion failure
                    with patch(
                        "airunner.components.art.gui.widgets.canvas.mixins.canvas_layer_mixin.pil_to_qimage",
                        return_value=None,
                    ):
                        # Execute
                        layer_mixin._create_new_layer_item(
                            layer_id, sample_layer_data
                        )

                        # Verify - no item should be created
                        layer_mixin.addItem.assert_not_called()
                        assert layer_id not in layer_mixin._layer_items

    def test_layer_item_is_layer_image_item_not_qgraphicspixmapitem(
        self, layer_mixin, sample_layer_data, sample_image
    ):
        """Test that _create_new_layer_item uses LayerImageItem instead of
        QGraphicsPixmapItem.

        Regression test for bug where QGraphicsPixmapItem was used,
        which doesn't have updateImage() method needed for undo operations.
        LayerImageItem provides updateImage() and other layer-specific
        functionality.
        """
        from airunner.components.art.gui.widgets.canvas.draggables.layer_image_item import (
            LayerImageItem,
        )

        layer_id = 1

        # Mock CanvasLayer with image data
        mock_layer = MagicMock(spec=CanvasLayer)
        mock_layer.id = layer_id

        # Mock DrawingPadSettings with image
        mock_drawing_pad = MagicMock(spec=DrawingPadSettings)
        mock_drawing_pad.image = sample_image

        # Mock PIL Image
        mock_pil_image = Image.new("RGB", (100, 100), color="red")

        with patch.object(CanvasLayer.objects, "get", return_value=mock_layer):
            with patch.object(
                DrawingPadSettings.objects,
                "filter_by_first",
                return_value=mock_drawing_pad,
            ):
                with patch(
                    "airunner.utils.image.convert_binary_to_image",
                    return_value=mock_pil_image,
                ):
                    # Execute
                    layer_mixin._create_new_layer_item(
                        layer_id, sample_layer_data
                    )

                    # Verify item was created and is a LayerImageItem
                    assert layer_id in layer_mixin._layer_items
                    item = layer_mixin._layer_items[layer_id]

                    # Critical: Must be LayerImageItem, not QGraphicsPixmapItem
                    assert isinstance(
                        item, LayerImageItem
                    ), f"Expected LayerImageItem, got {type(item)}"

                    # Verify LayerImageItem has updateImage method
                    # (this is what failed with QGraphicsPixmapItem)
                    assert hasattr(
                        item, "updateImage"
                    ), "LayerImageItem missing updateImage method"

                    # Verify it was initialized with correct parameters
                    layer_mixin.addItem.assert_called_once()
