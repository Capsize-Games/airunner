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


def test_ensure_draw_space_skips_growth_for_layer_canvas_items():
    """Brush draws should not auto-grow smaller layer-backed surfaces."""
    item = object()
    ensure_item_contains = Mock()
    scene = SimpleNamespace(
        drawing_pad_settings=SimpleNamespace(mask_layer_enabled=False),
        _get_active_layer_item=Mock(return_value=item),
        _uses_layer_canvas=lambda: True,
        item=None,
        draw_button_down=True,
        current_tool=CanvasToolName.BRUSH,
        _active_item_uses_document_surface=Mock(return_value=False),
        brush_settings=SimpleNamespace(size=12),
        _ensure_item_contains_scene_point=ensure_item_contains,
    )

    expanded = BrushScene._ensure_draw_space(scene, QPointF(10.0, 10.0))

    assert expanded is False
    ensure_item_contains.assert_not_called()


def test_start_stroke_buffer_uses_document_size_and_origin(qapp):
    """Stroke startup should seed a document-sized scratch overlay."""
    base = QImage(128, 64, QImage.Format.Format_ARGB32)
    base.fill(Qt.GlobalColor.transparent)
    active_item = SimpleNamespace(zValue=lambda: 4.0)
    view = SimpleNamespace(
        document_size=lambda: (640.0, 512.0),
        document_rect=lambda: QRectF(24.0, 18.0, 640.0, 512.0),
        document_origin=lambda: QPointF(24.0, 18.0),
    )
    scene = SimpleNamespace(
        drawing_pad_settings=SimpleNamespace(mask_layer_enabled=False),
        current_tool=CanvasToolName.BRUSH,
        active_item=active_item,
        views=lambda: [view],
        addItem=Mock(),
        _stroke_item=None,
        _stroke_base_image=None,
        _stroke_buffer_image=None,
        _stroke_buffer_erasing=False,
    )
    scene._current_paint_target = Mock(return_value=base)
    scene._remove_stroke_item = BrushScene._remove_stroke_item.__get__(
        scene,
        BrushScene,
    )
    scene._document_size = BrushScene._document_size.__get__(
        scene,
        BrushScene,
    )
    scene._document_absolute_origin = (
        BrushScene._document_absolute_origin.__get__(
            scene,
            BrushScene,
        )
    )
    scene._document_rect = BrushScene._document_rect.__get__(
        scene,
        BrushScene,
    )
    scene._document_display_origin = (
        BrushScene._document_display_origin.__get__(
            scene,
            BrushScene,
        )
    )
    scene._stroke_item_z_value = BrushScene._stroke_item_z_value.__get__(
        scene,
        BrushScene,
    )
    scene._sync_stroke_item = BrushScene._sync_stroke_item.__get__(
        scene,
        BrushScene,
    )

    BrushScene._start_stroke_buffer(scene)

    assert scene._stroke_base_image is base
    assert scene._stroke_buffer_image.width() == 640
    assert scene._stroke_buffer_image.height() == 512
    assert scene._stroke_item is not None
    assert scene._stroke_item.pos() == QPointF(24.0, 18.0)
    assert scene._stroke_item.zValue() == 5.0
    scene.addItem.assert_called_once_with(scene._stroke_item)


def test_start_stroke_buffer_skips_overlay_for_eraser(qapp):
    """Eraser strokes should not preview through the raw scratch overlay."""
    base = QImage(128, 64, QImage.Format.Format_ARGB32)
    base.fill(Qt.GlobalColor.transparent)
    active_item = SimpleNamespace(zValue=lambda: 4.0)
    view = SimpleNamespace(
        document_size=lambda: (640.0, 512.0),
        document_rect=lambda: QRectF(24.0, 18.0, 640.0, 512.0),
        document_origin=lambda: QPointF(24.0, 18.0),
    )
    scene = SimpleNamespace(
        drawing_pad_settings=SimpleNamespace(mask_layer_enabled=False),
        current_tool=CanvasToolName.ERASER,
        active_item=active_item,
        views=lambda: [view],
        addItem=Mock(),
        _stroke_item=None,
        _stroke_base_image=None,
        _stroke_buffer_image=None,
        _stroke_buffer_erasing=False,
        _stroke_target_item=None,
        _stroke_target_layer_id=None,
    )
    scene._current_paint_target = Mock(return_value=base)
    scene._remove_stroke_item = BrushScene._remove_stroke_item.__get__(
        scene,
        BrushScene,
    )
    scene._document_size = BrushScene._document_size.__get__(
        scene,
        BrushScene,
    )
    scene._document_absolute_origin = (
        BrushScene._document_absolute_origin.__get__(
            scene,
            BrushScene,
        )
    )
    scene._document_rect = BrushScene._document_rect.__get__(
        scene,
        BrushScene,
    )
    scene._document_display_origin = (
        BrushScene._document_display_origin.__get__(
            scene,
            BrushScene,
        )
    )
    scene._stroke_item_z_value = BrushScene._stroke_item_z_value.__get__(
        scene,
        BrushScene,
    )
    scene._sync_stroke_item = BrushScene._sync_stroke_item.__get__(
        scene,
        BrushScene,
    )

    BrushScene._start_stroke_buffer(scene)

    assert scene._stroke_buffer_erasing is True
    assert scene._stroke_item is None
    scene.addItem.assert_not_called()


def test_build_document_stroke_base_blits_layer_at_saved_origin(qapp):
    """Stroke base should normalize layer pixels into document space."""
    qimage = QImage(3, 3, QImage.Format.Format_ARGB32)
    qimage.fill(Qt.GlobalColor.transparent)
    qimage.setPixelColor(0, 0, QColor(255, 0, 0, 255))
    item = Mock()
    item.qimage = qimage
    item.drawing_pad_settings = SimpleNamespace(x_pos=120, y_pos=70)
    view = SimpleNamespace(
        document_size=lambda: (40.0, 30.0),
        document_origin=lambda: QPointF(100.0, 50.0),
        document_rect=lambda: QRectF(100.0, 50.0, 40.0, 30.0),
    )
    scene = SimpleNamespace(
        views=lambda: [view],
        original_item_positions={},
    )
    scene._document_size = BrushScene._document_size.__get__(
        scene,
        BrushScene,
    )
    scene._document_absolute_origin = (
        BrushScene._document_absolute_origin.__get__(
            scene,
            BrushScene,
        )
    )
    scene._layer_absolute_origin = BrushScene._layer_absolute_origin.__get__(
        scene,
        BrushScene,
    )

    base_image = BrushScene._build_document_stroke_base(scene, item)

    assert base_image is not None
    assert base_image.width() == 40
    assert base_image.height() == 30
    assert base_image.pixelColor(20, 20) == QColor(255, 0, 0, 255)


def test_handle_left_mouse_release_promotes_target_layer_to_document(qapp):
    """Release should merge into the locked target layer at document origin."""
    base_image = QImage(16, 16, QImage.Format.Format_ARGB32)
    base_image.fill(Qt.GlobalColor.transparent)
    stroke_image = QImage(16, 16, QImage.Format.Format_ARGB32)
    stroke_image.fill(Qt.GlobalColor.transparent)
    stroke_image.setPixelColor(5, 7, QColor(0, 255, 0, 255))
    merged_image = QImage(16, 16, QImage.Format.Format_ARGB32)
    merged_image.fill(Qt.GlobalColor.transparent)
    merged_image.setPixelColor(5, 7, QColor(0, 255, 0, 255))
    target_item = Mock()
    target_item.layer_image_data = {}
    scene = SimpleNamespace(
        draw_button_down=True,
        drawing_pad_settings=SimpleNamespace(mask_layer_enabled=False),
        active_image=None,
        _stroke_base_image=base_image,
        _stroke_buffer_image=stroke_image,
        _stroke_buffer_erasing=False,
        _stroke_target_item=target_item,
        _stroke_target_layer_id=7,
        _pending_brush_history_layer=7,
        original_item_positions={},
        stop_painter=Mock(),
        _compose_stroke_image=Mock(return_value=merged_image),
        _update_item_image=Mock(),
        _document_display_origin=Mock(return_value=QPointF(24.0, 18.0)),
        _document_absolute_origin=Mock(return_value=QPointF(100.0, 50.0)),
        _get_current_selected_layer_id=Mock(return_value=7),
        update_drawing_pad_settings=Mock(),
        _clear_stroke_buffer=Mock(),
        _commit_layer_history_transaction=Mock(),
        api=SimpleNamespace(
            art=SimpleNamespace(
                canvas=SimpleNamespace(
                    image_updated=Mock(),
                )
            )
        ),
        current_active_image=None,
        _pending_image_binary=None,
        _current_active_image_binary=None,
    )

    BrushScene._handle_left_mouse_release(scene, Mock())

    scene._update_item_image.assert_called_once_with(target_item, merged_image)
    target_item.setPos.assert_called_once_with(QPointF(24.0, 18.0))
    assert scene.original_item_positions[target_item] == QPointF(100.0, 50.0)
    update_call = scene.update_drawing_pad_settings.call_args.kwargs
    assert update_call["layer_id"] == 7
    assert update_call["x_pos"] == 100
    assert update_call["y_pos"] == 50
    assert update_call["image"].startswith(b"AIRAW1")
    assert scene._pending_image_binary is not None
    assert scene._current_active_image_binary is not None
    scene._commit_layer_history_transaction.assert_called_once_with(7, "image")


def test_preview_document_stroke_erasing_updates_target_item():
    """Eraser preview should show the composed erased result immediately."""
    preview_item = Mock()
    preview_image = QImage(4, 4, QImage.Format.Format_ARGB32)
    scene = SimpleNamespace(
        drawing_pad_settings=SimpleNamespace(mask_layer_enabled=False),
        _stroke_buffer_image=QImage(4, 4, QImage.Format.Format_ARGB32),
        _stroke_buffer_erasing=True,
        _stroke_base_image=QImage(4, 4, QImage.Format.Format_ARGB32),
        _stroke_target_item=preview_item,
        active_item=None,
        _document_display_origin=Mock(return_value=QPointF(24.0, 18.0)),
        _compose_stroke_image=Mock(return_value=preview_image),
        _update_item_image=Mock(),
    )

    handled = BrushScene._preview_document_stroke(scene)

    assert handled is True
    scene._compose_stroke_image.assert_called_once_with(
        scene._stroke_base_image,
        scene._stroke_buffer_image,
        True,
    )
    scene._update_item_image.assert_called_once_with(
        preview_item,
        preview_image,
        invalidate_scene=False,
    )
    preview_item.setPos.assert_called_once_with(QPointF(24.0, 18.0))


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