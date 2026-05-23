"""Tests for CanvasLayerMixin layer display functionality.

Verifies that layer items are created correctly with proper image handling.
"""

import pytest
from unittest.mock import MagicMock, patch
from PIL import Image
import io
from PySide6.QtCore import QPointF

from airunner.components.art.gui.widgets.canvas.mixins.canvas_layer_mixin import (
    CanvasLayerMixin,
)
from airunner_model.models.canvas_layer import CanvasLayer
from airunner_model.models.controlnet_settings import ControlnetSettings
from airunner_model.models.drawingpad_settings import (
    DrawingPadSettings,
)
from airunner_model.models.image_to_image_settings import (
    ImageToImageSettings,
)
from airunner_model.models.outpaint_settings import OutpaintSettings
from airunner_model.models.brush_settings import BrushSettings
from airunner_model.models.metadata_settings import MetadataSettings


class TestCanvasLayerMixin:
    """Test suite for CanvasLayerMixin._create_new_layer_item."""

    @pytest.fixture
    def layer_mixin(self, qapp):
        """Create a minimal CanvasLayerMixin instance for testing."""
        # Create mock class with necessary attributes
        mixin = CanvasLayerMixin()
        mixin._layer_items = {}
        mixin._pending_layer_images = {}
        mixin.original_item_positions = {}
        mixin.addItem = MagicMock()
        mixin.views = MagicMock(return_value=[])
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
        mock_drawing_pad.x_pos = 0
        mock_drawing_pad.y_pos = 0

        # Create mock Qt objects before the test
        mock_qimage = MagicMock()
        mock_qimage.isNull.return_value = False
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
                            mock_item.setPos.assert_called_once_with(
                                QPointF(0.0, 0.0)
                            )
                            assert layer_id in layer_mixin._layer_items

    def test_create_new_layer_item_uses_saved_absolute_position_with_view_transform(
        self, layer_mixin, sample_layer_data, sample_image
    ):
        """New layer items should be positioned from saved absolute coords."""
        layer_id = 1
        mock_layer = MagicMock()
        mock_layer.id = layer_id
        mock_qimage = MagicMock()
        mock_qimage.isNull.return_value = False
        mock_item = MagicMock()
        mock_drawing_pad = MagicMock()
        mock_drawing_pad.image = sample_image
        mock_drawing_pad.x_pos = 144
        mock_drawing_pad.y_pos = 44
        mock_view = MagicMock()
        mock_view.canvas_offset = QPointF(128, 64)
        mock_view._grid_compensation_offset = QPointF(16, 8)
        layer_mixin.views = MagicMock(return_value=[mock_view])

        with patch.object(CanvasLayer.objects, "get", return_value=mock_layer):
            with patch.object(
                DrawingPadSettings.objects,
                "filter_by_first",
                return_value=mock_drawing_pad,
            ):
                with patch(
                    "airunner.components.art.gui.widgets.canvas.mixins.canvas_layer_mixin.convert_binary_to_image",
                    return_value=Image.new("RGB", (100, 100), color="red"),
                ):
                    with patch(
                        "airunner.components.art.gui.widgets.canvas.mixins.canvas_layer_mixin.pil_to_qimage",
                        return_value=mock_qimage,
                    ):
                        with patch(
                            "airunner.components.art.gui.widgets.canvas.mixins.canvas_layer_mixin.LayerImageItem",
                            return_value=mock_item,
                        ):
                            layer_mixin._create_new_layer_item(
                                layer_id, sample_layer_data
                            )

        mock_item.setPos.assert_called_once_with(QPointF(32.0, -12.0))
        assert layer_mixin.original_item_positions[mock_item] == QPointF(
            144.0, 44.0
        )

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

        def test_capture_layers_state_skips_global_settings_models(
            self, layer_mixin
        ):
            """Layer snapshots should not query global brush/metadata tables."""
            layer_record = MagicMock(id=1)
            serialized = {"id": 1}
            layer_mixin._serialize_record = MagicMock(return_value=serialized)

            with patch.object(CanvasLayer.objects, "get", return_value=layer_record):
                with patch.object(
                    DrawingPadSettings.objects,
                    "filter_by_first",
                    return_value=MagicMock(),
                ), patch.object(
                    ControlnetSettings.objects,
                    "filter_by_first",
                    return_value=MagicMock(),
                ), patch.object(
                    ImageToImageSettings.objects,
                    "filter_by_first",
                    return_value=MagicMock(),
                ), patch.object(
                    OutpaintSettings.objects,
                    "filter_by_first",
                    return_value=MagicMock(),
                ), patch.object(
                    BrushSettings.objects,
                    "filter_by_first",
                ) as brush_filter, patch.object(
                    MetadataSettings.objects,
                    "filter_by_first",
                ) as metadata_filter:
                    snapshots = layer_mixin._capture_layers_state([1])

            assert snapshots == [
                {
                    "layer": serialized,
                    "drawing_pad": serialized,
                    "controlnet": serialized,
                    "image_to_image": serialized,
                    "outpaint": serialized,
                }
            ]
            brush_filter.assert_not_called()
            metadata_filter.assert_not_called()

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

    def test_create_new_layer_item_uses_pending_generated_image(
        self, layer_mixin, sample_layer_data
    ):
        """Test new layer creation prefers the in-memory generated image."""
        layer_id = 1
        pending_image = Image.new("RGB", (100, 100), color="blue")
        mock_layer = MagicMock()
        mock_layer.id = layer_id
        mock_qimage = MagicMock()
        mock_qimage.isNull.return_value = False
        mock_item = MagicMock()
        mock_drawing_pad = MagicMock()
        mock_drawing_pad.x_pos = 0
        mock_drawing_pad.y_pos = 0

        layer_mixin._pending_layer_images[layer_id] = pending_image
        layer_mixin._convert_and_cache_qimage = MagicMock(
            return_value=mock_qimage
        )

        with patch.object(CanvasLayer.objects, "get", return_value=mock_layer):
            with patch.object(
                DrawingPadSettings.objects,
                "filter_by_first",
                return_value=mock_drawing_pad,
            ) as mock_filter:
                with patch(
                    "airunner.components.art.gui.widgets.canvas.mixins.canvas_layer_mixin.LayerImageItem",
                    return_value=mock_item,
                ):
                    layer_mixin._create_new_layer_item(
                        layer_id, sample_layer_data
                    )

        mock_filter.assert_called_once_with(layer_id=layer_id)
        layer_mixin._convert_and_cache_qimage.assert_called_once_with(
            pending_image
        )
        mock_item.setPos.assert_called_once_with(QPointF(0.0, 0.0))
        assert layer_id in layer_mixin._layer_items
        assert layer_id not in layer_mixin._pending_layer_images

    def test_update_existing_layer_item_uses_pending_generated_image(
        self, layer_mixin, sample_layer_data
    ):
        """Test existing layer updates prefer the in-memory generated image."""
        layer_id = 1
        pending_image = Image.new("RGB", (100, 100), color="green")
        mock_qimage = MagicMock()
        mock_qimage.isNull.return_value = False
        mock_item = MagicMock()

        layer_mixin._layer_items[layer_id] = mock_item
        layer_mixin._pending_layer_images[layer_id] = pending_image
        layer_mixin._convert_and_cache_qimage = MagicMock(
            return_value=mock_qimage
        )

        with patch.object(
            DrawingPadSettings.objects,
            "filter_by_first",
        ) as mock_filter:
            layer_mixin._update_existing_layer_item(
                layer_id,
                {"visible": True, "opacity": 0.8, "order": 1},
            )

        mock_filter.assert_not_called()
        mock_item.updateImage.assert_called_once_with(mock_qimage)
        assert layer_id not in layer_mixin._pending_layer_images
