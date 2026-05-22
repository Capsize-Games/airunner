"""Focused brush-scene tests for the fixed-document contract."""

from types import SimpleNamespace
from unittest.mock import Mock

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage

from airunner.components.art.gui.widgets.canvas.brush_scene import BrushScene
from airunner.enums import CanvasToolName


def test_active_item_uses_document_surface_when_item_contains_document():
    """Document-sized layer items should be treated as fixed surfaces."""
    item = SimpleNamespace(
        sceneBoundingRect=lambda: QRectF(24.0, 18.0, 640.0, 512.0),
        qimage=QImage(640, 512, QImage.Format.Format_ARGB32),
    )
    scene = SimpleNamespace(
        views=lambda: [
            SimpleNamespace(
                document_rect=lambda: QRectF(24.0, 18.0, 640.0, 512.0),
                document_size=lambda: (640.0, 512.0),
            )
        ]
    )

    assert BrushScene._active_item_uses_document_surface(scene, item) is True


def test_active_item_uses_document_surface_when_sizes_match():
    """Document-sized layers should stay fixed even before exact containment."""
    item = SimpleNamespace(
        sceneBoundingRect=lambda: QRectF(0.0, 0.0, 512.0, 512.0),
        qimage=QImage(512, 512, QImage.Format.Format_ARGB32),
    )
    scene = SimpleNamespace(
        views=lambda: [
            SimpleNamespace(
                document_rect=lambda: QRectF(37.0, 37.0, 512.0, 512.0),
                document_size=lambda: (512.0, 512.0),
            )
        ]
    )

    assert BrushScene._active_item_uses_document_surface(scene, item) is True


def test_active_item_uses_display_document_surface_when_offsets_apply():
    """Document-surface detection should use display-space document bounds."""
    item = SimpleNamespace(
        sceneBoundingRect=lambda: QRectF(-6.0, -2.0, 640.0, 512.0),
        qimage=QImage(640, 512, QImage.Format.Format_ARGB32),
    )
    scene = SimpleNamespace(
        views=lambda: [
            SimpleNamespace(
                document_rect=lambda: QRectF(24.0, 18.0, 640.0, 512.0),
                document_size=lambda: (640.0, 512.0),
                canvas_offset=QPointF(50.0, 30.0),
                grid_compensation_offset=QPointF(20.0, 10.0),
            )
        ]
    )

    assert BrushScene._active_item_uses_document_surface(scene, item) is True


def test_ensure_draw_space_skips_growth_for_document_surface():
    """Brush draws should not expand items that already cover the document."""
    item = object()
    ensure_item_contains = Mock()
    scene = SimpleNamespace(
        drawing_pad_settings=SimpleNamespace(mask_layer_enabled=False),
        _get_active_layer_item=Mock(return_value=item),
        item=None,
        draw_button_down=True,
        current_tool=CanvasToolName.BRUSH,
        _active_item_uses_document_surface=Mock(return_value=True),
        brush_settings=SimpleNamespace(size=12),
        _ensure_item_contains_scene_point=ensure_item_contains,
    )

    expanded = BrushScene._ensure_draw_space(scene, QPointF(10.0, 10.0))

    assert expanded is False
    ensure_item_contains.assert_not_called()


def test_clamp_scene_point_to_document_projects_to_edge():
    """Stroke points outside the document should clamp to the edge."""
    document_rect = QRectF(24.0, 18.0, 640.0, 512.0)
    scene = SimpleNamespace(
        views=lambda: [SimpleNamespace(document_rect=lambda: document_rect)]
    )
    scene._document_rect = BrushScene._document_rect.__get__(
        scene,
        BrushScene,
    )

    clamped = BrushScene._clamp_scene_point_to_document(
        scene,
        QPointF(4.0, 700.0),
    )

    assert clamped == QPointF(document_rect.left(), document_rect.bottom())


def test_document_rect_converts_to_display_space_with_offsets():
    """Brush hit testing should use the display-space document rect."""
    scene = SimpleNamespace(
        views=lambda: [
            SimpleNamespace(
                document_rect=lambda: QRectF(24.0, 18.0, 640.0, 512.0),
                canvas_offset=QPointF(50.0, 30.0),
                grid_compensation_offset=QPointF(20.0, 10.0),
            )
        ]
    )

    rect = BrushScene._document_rect(scene)

    assert rect == QRectF(-6.0, -2.0, 640.0, 512.0)


def test_scene_point_in_document_rejects_outside_point():
    """Brush presses that start outside the document should be ignored."""
    document_rect = QRectF(24.0, 18.0, 640.0, 512.0)
    scene = SimpleNamespace(
        views=lambda: [SimpleNamespace(document_rect=lambda: document_rect)]
    )
    scene._document_rect = BrushScene._document_rect.__get__(
        scene,
        BrushScene,
    )

    assert BrushScene._scene_point_in_document(
        scene,
        QPointF(4.0, 40.0),
    ) is False


def test_compose_stroke_image_overlays_brush_buffer():
    """Brush previews should composite buffered color onto the base image."""
    scene = SimpleNamespace(
        drawing_pad_settings=SimpleNamespace(mask_layer_enabled=False)
    )
    scene._stroke_composition_mode = BrushScene._stroke_composition_mode.__get__(
        scene,
        BrushScene,
    )
    base = QImage(4, 4, QImage.Format.Format_ARGB32)
    base.fill(Qt.GlobalColor.transparent)
    stroke = QImage(4, 4, QImage.Format.Format_ARGB32)
    stroke.fill(Qt.GlobalColor.transparent)
    stroke.setPixelColor(1, 1, QColor(255, 0, 0, 255))

    composed = BrushScene._compose_stroke_image(scene, base, stroke, False)

    assert composed.pixelColor(1, 1) == QColor(255, 0, 0, 255)


def test_compose_stroke_image_erases_with_destination_out():
    """Eraser previews should clear pixels from the base image."""
    scene = SimpleNamespace(
        drawing_pad_settings=SimpleNamespace(mask_layer_enabled=False)
    )
    scene._stroke_composition_mode = BrushScene._stroke_composition_mode.__get__(
        scene,
        BrushScene,
    )
    base = QImage(4, 4, QImage.Format.Format_ARGB32)
    base.fill(QColor(255, 0, 0, 255))
    stroke = QImage(4, 4, QImage.Format.Format_ARGB32)
    stroke.fill(Qt.GlobalColor.transparent)
    stroke.setPixelColor(1, 1, QColor(255, 255, 255, 255))

    composed = BrushScene._compose_stroke_image(scene, base, stroke, True)

    assert composed.pixelColor(1, 1).alpha() == 0
    assert composed.pixelColor(0, 0).alpha() == 255


def test_update_active_item_image_can_skip_scene_invalidation():
    """Brush preview should not invalidate the scene during paint."""
    active_item = Mock()
    active_item.scene.return_value = Mock()
    scene = SimpleNamespace(active_item=active_item)

    image = QImage(4, 4, QImage.Format.Format_ARGB32)

    BrushScene._update_active_item_image(
        scene,
        image,
        invalidate_scene=False,
    )

    active_item.updateImage.assert_called_once_with(
        image,
        invalidate_scene=False,
    )
    active_item.scene.return_value.update.assert_not_called()


def test_active_item_prefers_layer_canvas_item_over_legacy_item():
    """Main brush canvas should not fall back to stale self.item."""
    layer_item = SimpleNamespace(qimage=object())
    scene = SimpleNamespace(
        drawing_pad_settings=SimpleNamespace(mask_layer_enabled=False),
        _get_active_layer_item=Mock(return_value=None),
        _layer_items={4: layer_item},
        item=object(),
        _uses_layer_canvas=lambda: True,
        _get_layer_canvas_item=lambda: layer_item,
        image=object(),
    )

    assert BrushScene.active_item.fget(scene) is layer_item
    assert BrushScene.active_image.fget(scene) is layer_item.qimage


def test_current_paint_target_does_not_use_legacy_item_on_layer_canvas():
    """Painting should stop rather than target a stale fallback surface."""
    scene = SimpleNamespace(
        drawing_pad_settings=SimpleNamespace(mask_layer_enabled=False),
        _layer_items={1: object()},
        _uses_layer_canvas=lambda: True,
        _get_layer_canvas_item=lambda: None,
        image=object(),
    )

    assert BrushScene._current_paint_target(scene) is None