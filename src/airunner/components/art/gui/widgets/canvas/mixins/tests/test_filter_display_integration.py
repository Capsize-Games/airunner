"""Integration test verifying filter display with layer system.

This test ensures that the fix for filter display works correctly
when layers are present.
"""

from unittest.mock import Mock
from PIL import Image
from PySide6.QtCore import QPoint
from PySide6.QtGui import QImage


def test_filter_updates_layer_in_real_workflow():
    """Integration test: Filter should update active layer item.

    This test simulates the real workflow:
    1. Canvas has layers (layer system active)
    2. User applies a filter
    3. Filter executes successfully
    4. Filtered image should update the active layer item visually

    This test verifies the fix for the bug where filters wouldn't
    display when layers were present.
    """
    # Create mock canvas with layer system
    mock_canvas = Mock()

    # Setup: Layer system is active
    mock_layer_item = Mock()
    mock_canvas._layer_items = {1: mock_layer_item}
    mock_canvas._get_active_layer_item = Mock(return_value=mock_layer_item)
    mock_canvas._get_current_selected_layer_id = Mock(return_value=1)

    # Setup: Legacy system is bypassed (self.item is None when layers exist)
    mock_canvas.item = None

    # Setup: Filter processing mocks
    mock_canvas.current_active_image = Image.new(
        "RGB", (256, 256), color="blue"
    )
    mock_canvas.logger = Mock()

    # Setup: QImage conversion
    test_qimage = QImage(256, 256, QImage.Format.Format_RGB888)
    mock_canvas._convert_and_cache_qimage = Mock(return_value=test_qimage)

    # Import the actual mixin method
    from airunner.components.art.gui.widgets.canvas.mixins.canvas_scene_management_mixin import (
        CanvasSceneManagementMixin,
    )

    # Create a filtered image (simulating filter execution)
    filtered_image = Image.new("RGB", (256, 256), color="green")

    # Execute the update (this is what _add_image_to_scene calls)
    CanvasSceneManagementMixin._update_or_create_item(
        mock_canvas,
        filtered_image,
        QPoint(0, 0),
        QPoint(0, 0),
    )

    # CRITICAL ASSERTIONS: Verify layer item was updated
    assert (
        mock_layer_item.updateImage.called
    ), "Layer item should have been updated with filtered image"

    # Verify correct QImage was passed
    call_args = mock_layer_item.updateImage.call_args
    assert (
        call_args[0][0] == test_qimage
    ), "Layer item should receive the converted QImage"

    # Verify property was also updated for consistency
    assert (
        mock_canvas.current_active_image == filtered_image
    ), "current_active_image property should be updated"

    # Verify info log was emitted
    mock_canvas.logger.info.assert_called_with(
        "Updated active layer item with filtered image"
    )

    print("✅ Integration test passed: Filter correctly updates layer item!")


def test_filter_with_legacy_system_still_works():
    """Integration test: Ensure legacy system (no layers) still works.

    Backward compatibility test to ensure the fix doesn't break
    the legacy single-item system.
    """
    # Create mock canvas WITHOUT layer system
    mock_canvas = Mock()

    # Setup: No active layer
    mock_canvas._get_active_layer_item = Mock(return_value=None)
    mock_canvas._layer_items = {}

    # Setup: Legacy system is active (self.item exists)
    mock_legacy_item = Mock()
    mock_canvas.item = mock_legacy_item

    # Setup: Mocks for legacy update path
    test_qimage = QImage(256, 256, QImage.Format.Format_RGB888)
    mock_canvas._convert_and_cache_qimage = Mock(return_value=test_qimage)
    mock_canvas._update_existing_item_image = Mock()
    mock_canvas._update_item_position = Mock()
    mock_canvas.logger = Mock()

    # Import the actual mixin method
    from airunner.components.art.gui.widgets.canvas.mixins.canvas_scene_management_mixin import (
        CanvasSceneManagementMixin,
    )

    # Create a filtered image
    filtered_image = Image.new("RGB", (256, 256), color="red")

    # Execute the update
    CanvasSceneManagementMixin._update_or_create_item(
        mock_canvas,
        filtered_image,
        QPoint(10, 20),
        QPoint(5, 5),
    )

    # CRITICAL ASSERTIONS: Verify legacy system was used
    mock_canvas._update_existing_item_image.assert_called_once_with(
        test_qimage
    ), "Legacy system should update via _update_existing_item_image"

    mock_canvas._update_item_position.assert_called_once(), "Legacy system should update position"

    print("✅ Integration test passed: Legacy system still works!")


if __name__ == "__main__":
    """Run tests standalone for quick verification."""
    try:
        test_filter_updates_layer_in_real_workflow()
        test_filter_with_legacy_system_still_works()
        print("\n✅ ALL INTEGRATION TESTS PASSED!")
        print("The filter display fix is working correctly.")
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
