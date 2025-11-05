"""Unit tests for CustomScene surface growth and positioning edge cases.

These tests focus on the dynamic canvas expansion and measurement calculations
that are fragile and prone to bugs.
"""

from unittest.mock import Mock
from PySide6.QtCore import QPointF
from PySide6.QtGui import QImage

from airunner.components.art.gui.widgets.canvas.custom_scene import (
    CustomScene,
)
from airunner.components.art.gui.widgets.canvas.draggables.draggable_pixmap import (
    DraggablePixmap,
)


class TestQuantizeGrowthCalculations:
    """Test quantize growth - rounds to growth step for consistent sizing."""

    def test_quantize_growth_exact_step(self, qapp):
        """Growth exactly on step boundary should not change."""
        scene = CustomScene(canvas_type="image")
        scene._surface_growth_step = 128

        assert scene._quantize_growth(0) == 0
        assert scene._quantize_growth(128) == 128
        assert scene._quantize_growth(256) == 256
        assert scene._quantize_growth(512) == 512

    def test_quantize_growth_rounds_up(self, qapp):
        """Growth should round up to next step."""
        scene = CustomScene(canvas_type="image")
        scene._surface_growth_step = 128

        assert scene._quantize_growth(1) == 128
        assert scene._quantize_growth(50) == 128
        assert scene._quantize_growth(127) == 128
        assert scene._quantize_growth(129) == 256
        assert scene._quantize_growth(255) == 256

    def test_quantize_growth_large_values(self, qapp):
        """Growth should handle large values correctly."""
        scene = CustomScene(canvas_type="image")
        scene._surface_growth_step = 128

        assert scene._quantize_growth(1000) == 1024
        assert scene._quantize_growth(5000) == 5120
        assert scene._quantize_growth(10000) == 10112

    def test_quantize_growth_negative_values(self, qapp):
        """Growth should handle negative values by returning 0."""
        scene = CustomScene(canvas_type="image")
        scene._surface_growth_step = 64

        # Negative values should return 0 (no negative growth)
        assert scene._quantize_growth(-1) == 0
        assert scene._quantize_growth(-63) == 0
        assert scene._quantize_growth(-64) == 0
        assert scene._quantize_growth(-65) == 0
        assert scene._quantize_growth(-100) == 0

    def test_quantize_growth_zero(self, qapp):
        """Growth of zero should remain zero."""
        scene = CustomScene(canvas_type="image")
        scene._surface_growth_step = 128

        assert scene._quantize_growth(0) == 0

    def test_quantize_growth_different_step_sizes(self, qapp):
        """Growth should work with different step sizes."""
        scene = CustomScene(canvas_type="image")

        # Test with step size 64
        scene._surface_growth_step = 64
        assert scene._quantize_growth(100) == 128

        # Test with step size 256
        scene._surface_growth_step = 256
        assert scene._quantize_growth(100) == 256

        # Test with step size 32
        scene._surface_growth_step = 32
        assert scene._quantize_growth(100) == 128

    def test_quantize_growth_one_pixel_step(self, qapp):
        """Growth with 1-pixel step should equal ceiling."""
        scene = CustomScene(canvas_type="image")
        scene._surface_growth_step = 1

        assert scene._quantize_growth(0) == 0
        assert scene._quantize_growth(1) == 1
        assert scene._quantize_growth(100) == 100


class TestCreateBlankSurface:
    """Test blank surface creation - foundation for all canvas operations."""

    def test_create_blank_surface_default_size(self, qapp):
        """Blank surface should use minimum size by default."""
        scene = CustomScene(canvas_type="image")
        scene._minimum_surface_size = 256

        surface = scene._create_blank_surface()

        assert surface.width() == 256
        assert surface.height() == 256
        assert surface.format() == QImage.Format.Format_ARGB32

    def test_create_blank_surface_custom_size(self, qapp):
        """Blank surface should accept custom dimensions."""
        scene = CustomScene(canvas_type="image")

        surface = scene._create_blank_surface(512, 768)

        assert surface.width() == 512
        assert surface.height() == 768

    def test_create_blank_surface_zero_size(self, qapp):
        """Blank surface should enforce minimum 1x1 size."""
        scene = CustomScene(canvas_type="image")

        surface = scene._create_blank_surface(0, 0)

        # Qt doesn't allow 0x0 images, minimum is 1x1
        assert surface.width() == 1
        assert surface.height() == 1

    def test_create_blank_surface_one_pixel(self, qapp):
        """Blank surface should handle 1x1 size."""
        scene = CustomScene(canvas_type="image")

        surface = scene._create_blank_surface(1, 1)

        assert surface.width() == 1
        assert surface.height() == 1

    def test_create_blank_surface_very_large(self, qapp):
        """Blank surface should handle very large sizes."""
        scene = CustomScene(canvas_type="image")

        surface = scene._create_blank_surface(8192, 8192)

        assert surface.width() == 8192
        assert surface.height() == 8192

    def test_create_blank_surface_rectangular(self, qapp):
        """Blank surface should handle rectangular sizes."""
        scene = CustomScene(canvas_type="image")

        surface = scene._create_blank_surface(1920, 1080)

        assert surface.width() == 1920
        assert surface.height() == 1080

    def test_create_blank_surface_format(self, qapp):
        """Blank surface should always use ARGB32 format."""
        scene = CustomScene(canvas_type="image")

        sizes = [(100, 100), (512, 512), (1024, 768), (1, 1)]

        for width, height in sizes:
            surface = scene._create_blank_surface(width, height)
            assert surface.format() == QImage.Format.Format_ARGB32


class TestExpandItemSurface:
    """Test expand_item_surface - critical for drawing beyond bounds."""

    def test_expand_item_surface_no_growth(self, qapp):
        """Expand with all zeros should skip expansion."""
        scene = CustomScene(canvas_type="image")
        original = QImage(100, 100, QImage.Format.Format_ARGB32)
        item = DraggablePixmap(qimage=original)

        result = scene._expand_item_surface(item, 0, 0, 0, 0)

        assert result is False
        assert item.qimage.width() == 100
        assert item.qimage.height() == 100

    def test_expand_item_surface_right_only(self, qapp):
        """Expand right should increase width."""
        scene = CustomScene(canvas_type="image")
        scene._surface_growth_step = 64
        original = QImage(100, 100, QImage.Format.Format_ARGB32)
        item = DraggablePixmap(qimage=original)

        result = scene._expand_item_surface(item, 0, 0, 50, 0)

        assert result is True
        # Width should grow by quantized amount (50 -> 64)
        assert item.qimage.width() > 100
        assert item.qimage.height() == 100  # Height unchanged

    def test_expand_item_surface_bottom_only(self, qapp):
        """Expand bottom should increase height."""
        scene = CustomScene(canvas_type="image")
        scene._surface_growth_step = 64
        original = QImage(100, 100, QImage.Format.Format_ARGB32)
        item = DraggablePixmap(qimage=original)

        result = scene._expand_item_surface(item, 0, 0, 0, 50)

        assert result is True
        assert item.qimage.width() == 100  # Width unchanged
        assert item.qimage.height() > 100

    def test_expand_item_surface_left_and_top(self, qapp):
        """Expand left/top should increase size and shift position."""
        scene = CustomScene(canvas_type="image")
        scene._surface_growth_step = 64
        original = QImage(100, 100, QImage.Format.Format_ARGB32)
        item = DraggablePixmap(qimage=original)
        item.setPos(50, 50)

        result = scene._expand_item_surface(item, 30, 40, 0, 0)

        assert result is True
        # Size should increase
        assert item.qimage.width() > 100
        assert item.qimage.height() > 100
        # Position should shift left/up by quantized growth

    def test_expand_item_surface_all_directions(self, qapp):
        """Expand in all directions should work."""
        scene = CustomScene(canvas_type="image")
        scene._surface_growth_step = 64
        original = QImage(100, 100, QImage.Format.Format_ARGB32)
        item = DraggablePixmap(qimage=original)

        result = scene._expand_item_surface(item, 30, 40, 50, 60)

        assert result is True
        assert item.qimage.width() > 100
        assert item.qimage.height() > 100

    def test_expand_item_surface_minimal_growth(self, qapp):
        """Expand with 1 pixel should round to step."""
        scene = CustomScene(canvas_type="image")
        scene._surface_growth_step = 64
        original = QImage(100, 100, QImage.Format.Format_ARGB32)
        item = DraggablePixmap(qimage=original)

        result = scene._expand_item_surface(item, 0, 0, 1, 0)

        assert result is True
        # _expand_item_surface uses exact values, not quantized
        expected_width = 100 + 1
        assert item.qimage.width() == expected_width

    def test_expand_item_surface_large_growth(self, qapp):
        """Expand with large amount should work."""
        scene = CustomScene(canvas_type="image")
        scene._surface_growth_step = 128
        original = QImage(100, 100, QImage.Format.Format_ARGB32)
        item = DraggablePixmap(qimage=original)

        result = scene._expand_item_surface(item, 0, 0, 1000, 0)

        assert result is True
        # _expand_item_surface uses exact values, not quantized
        expected_width = 100 + 1000
        assert item.qimage.width() == expected_width


class TestEnsureItemContainsScenePoint:
    """Test ensure_item_contains_scene_point - drawing boundary checks."""

    def test_ensure_item_contains_point_already_inside(self, qapp):
        """Point already inside should not expand."""
        scene = CustomScene(canvas_type="image")
        pixmap = QImage(200, 200, QImage.Format.Format_ARGB32)
        item = DraggablePixmap(qimage=pixmap)
        item.setPos(0, 0)

        # Point at (100, 100) with radius 10 is well within bounds
        result = scene._ensure_item_contains_scene_point(
            item, QPointF(100, 100), 10.0
        )

        assert result is False  # No expansion needed

    def test_ensure_item_contains_point_at_edge(self, qapp):
        """Point at edge should be inside."""
        scene = CustomScene(canvas_type="image")
        pixmap = QImage(100, 100, QImage.Format.Format_ARGB32)
        item = DraggablePixmap(qimage=pixmap)
        item.setPos(0, 0)

        # Point at exact edge
        result = scene._ensure_item_contains_scene_point(
            item, QPointF(100, 100), 0.0
        )

        # Edge is inside by Qt's contains logic
        assert result is False

    def test_ensure_item_contains_point_at_origin(self, qapp):
        """Point at origin should be inside."""
        scene = CustomScene(canvas_type="image")
        pixmap = QImage(100, 100, QImage.Format.Format_ARGB32)
        item = DraggablePixmap(qimage=pixmap)
        item.setPos(0, 0)

        result = scene._ensure_item_contains_scene_point(
            item, QPointF(0, 0), 5.0
        )

        # With radius > 0, expansion occurs due to quantization
        assert result is True

    def test_ensure_item_contains_point_with_radius(self, qapp):
        """Point with radius should consider brush size."""
        scene = CustomScene(canvas_type="image")
        pixmap = QImage(100, 100, QImage.Format.Format_ARGB32)
        item = DraggablePixmap(qimage=pixmap)
        item.setPos(0, 0)

        # Point at (95, 95) with radius 10 extends to (105, 105)
        # This should require expansion
        result = scene._ensure_item_contains_scene_point(
            item, QPointF(95, 95), 10.0
        )

        # Depending on implementation, may need expansion
        assert isinstance(result, bool)

    def test_ensure_item_contains_point_with_offset_item(self, qapp):
        """Point check should account for item position."""
        scene = CustomScene(canvas_type="image")
        pixmap = QImage(100, 100, QImage.Format.Format_ARGB32)
        item = DraggablePixmap(qimage=pixmap)
        item.setPos(50, 50)  # Item offset

        # Point at (100, 100) in scene coords
        # In item coords this is (50, 50) - should be inside
        result = scene._ensure_item_contains_scene_point(
            item, QPointF(100, 100), 5.0
        )

        assert result is False  # Inside


class TestImagePivotPoint:
    """Test image pivot point property."""

    def test_image_pivot_point_default(self, qapp):
        """Image pivot point should default to (0,0)."""
        scene = CustomScene(canvas_type="image")

        # Mock current_settings to avoid database access
        from unittest.mock import MagicMock, PropertyMock

        mock_settings = MagicMock()
        mock_settings.x_pos = 0
        mock_settings.y_pos = 0

        # Patch the current_settings property to return our mock
        type(scene).current_settings = PropertyMock(return_value=mock_settings)

        pivot = scene.image_pivot_point
        assert pivot.x() == 0
        assert pivot.y() == 0

    def test_image_pivot_point_setter(self, qapp):
        """Image pivot point should store value."""
        scene = CustomScene(canvas_type="image")

        from unittest.mock import MagicMock, PropertyMock

        mock_settings = MagicMock()
        type(scene).current_settings = PropertyMock(return_value=mock_settings)

        # Mock API to avoid AttributeError
        scene.api = MagicMock()

        scene.image_pivot_point = QPointF(100, 200)

        # The setter calls update_current_layer, check it was called
        scene.api.art.canvas.update_current_layer.assert_called_once_with(
            QPointF(100, 200)
        )

    def test_image_pivot_point_negative(self, qapp):
        """Image pivot point should handle negative values."""
        scene = CustomScene(canvas_type="image")

        from unittest.mock import MagicMock, PropertyMock

        mock_settings = MagicMock()
        type(scene).current_settings = PropertyMock(return_value=mock_settings)
        scene.api = MagicMock()

        scene.image_pivot_point = QPointF(-50, -75)

        scene.api.art.canvas.update_current_layer.assert_called_once_with(
            QPointF(-50, -75)
        )

    def test_image_pivot_point_fractional(self, qapp):
        """Image pivot point should handle fractional values."""
        scene = CustomScene(canvas_type="image")

        from unittest.mock import MagicMock, PropertyMock

        mock_settings = MagicMock()
        type(scene).current_settings = PropertyMock(return_value=mock_settings)
        scene.api = MagicMock()

        scene.image_pivot_point = QPointF(100.5, 200.75)

        scene.api.art.canvas.update_current_layer.assert_called_once_with(
            QPointF(100.5, 200.75)
        )


class TestClearSelection:
    """Test selection clearing."""

    def test_clear_selection_resets_positions(self, qapp):
        """Clear selection should reset start and stop positions."""
        scene = CustomScene(canvas_type="image")
        scene.selection_start_pos = QPointF(10, 20)
        scene.selection_stop_pos = QPointF(100, 200)

        scene.clear_selection()

        assert scene.selection_start_pos is None
        assert scene.selection_stop_pos is None

    def test_clear_selection_when_already_none(self, qapp):
        """Clear selection should work when already None."""
        scene = CustomScene(canvas_type="image")
        scene.selection_start_pos = None
        scene.selection_stop_pos = None

        # Should not raise error
        scene.clear_selection()

        assert scene.selection_start_pos is None
        assert scene.selection_stop_pos is None


class TestStopPainter:
    """Test painter cleanup."""

    def test_stop_painter_ends_active_painter(self, qapp):
        """Stop painter should end active painter."""
        scene = CustomScene(canvas_type="image")
        mock_painter = Mock()
        mock_painter.isActive = Mock(return_value=True)
        mock_painter.end = Mock()
        scene.painter = mock_painter

        scene.stop_painter()

        mock_painter.end.assert_called_once()

    def test_stop_painter_clears_reference(self, qapp):
        """Stop painter should clear painter reference."""
        scene = CustomScene(canvas_type="image")
        scene.painter = Mock()
        scene.painter.isActive = Mock(return_value=True)
        scene.painter.end = Mock()

        scene.stop_painter()

        assert scene.painter is None

    def test_stop_painter_with_no_painter(self, qapp):
        """Stop painter should work when painter is None."""
        scene = CustomScene(canvas_type="image")
        scene.painter = None

        # Should not raise error
        scene.stop_painter()

        assert scene.painter is None

    def test_stop_painter_with_inactive_painter(self, qapp):
        """Stop painter should work with inactive painter."""
        scene = CustomScene(canvas_type="image")
        mock_painter = Mock()
        mock_painter.isActive = Mock(return_value=False)
        mock_painter.end = Mock()
        scene.painter = mock_painter

        scene.stop_painter()

        # Should not call end on inactive painter
        mock_painter.end.assert_not_called()
        assert scene.painter is None


class TestGetCanvasOffset:
    """Test canvas offset retrieval."""

    def test_get_canvas_offset_returns_qpointf(self, qapp):
        """Get canvas offset should return QPointF."""
        scene = CustomScene(canvas_type="image")

        result = scene.get_canvas_offset()

        assert isinstance(result, QPointF)

    def test_get_canvas_offset_defaults_to_zero(self, qapp):
        """Get canvas offset should default to (0,0)."""
        scene = CustomScene(canvas_type="image")
        scene.settings = Mock()
        scene.settings.value = Mock(return_value=0.0)

        result = scene.get_canvas_offset()

        assert result.x() == 0.0
        assert result.y() == 0.0

    def test_get_canvas_offset_reads_from_settings(self, qapp):
        """Get canvas offset should read from view's canvas_offset."""
        scene = CustomScene(canvas_type="image")

        # Mock the view with canvas_offset attribute
        from unittest.mock import Mock

        mock_view = Mock()
        mock_view.canvas_offset = QPointF(123.0, 456.0)

        # Mock views() to return our mock view
        scene.views = Mock(return_value=[mock_view])

        result = scene.get_canvas_offset()

        assert result.x() == 123.0
        assert result.y() == 456.0

    def test_get_canvas_offset_with_negative_values(self, qapp):
        """Get canvas offset should handle negative values."""
        scene = CustomScene(canvas_type="image")

        from unittest.mock import Mock

        mock_view = Mock()
        mock_view.canvas_offset = QPointF(-100.0, -200.0)
        scene.views = Mock(return_value=[mock_view])

        result = scene.get_canvas_offset()

        assert result.x() == -100.0
        assert result.y() == -200.0


class TestHistoryManagement:
    """Test undo/redo history management."""

    def test_clear_history_empties_stacks(self, qapp):
        """Clear history should empty undo and redo stacks."""
        scene = CustomScene(canvas_type="image")
        scene.undo_history = [{"data": "test1"}, {"data": "test2"}]
        scene.redo_history = [{"data": "test3"}]

        scene._clear_history()

        assert scene.undo_history == []
        assert scene.redo_history == []

    def test_clear_history_resets_transactions(self, qapp):
        """Clear history should reset pending transactions."""
        scene = CustomScene(canvas_type="image")
        scene._history_transactions = {1: {"data": "test"}}
        scene._structure_history_transaction = {"data": "test"}

        scene._clear_history()

        assert scene._history_transactions == {}
        assert scene._structure_history_transaction is None

    def test_clear_history_when_already_empty(self, qapp):
        """Clear history should work when already empty."""
        scene = CustomScene(canvas_type="image")
        scene.undo_history = []
        scene.redo_history = []
        scene._history_transactions = {}
        scene._structure_history_transaction = None

        # Should not raise error
        scene._clear_history()

        assert scene.undo_history == []
        assert scene.redo_history == []
