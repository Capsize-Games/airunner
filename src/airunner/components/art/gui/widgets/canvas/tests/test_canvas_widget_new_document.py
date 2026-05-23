"""Tests for new document workflow in the canvas widget."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

from PySide6.QtCore import QPoint, QPointF

from airunner.components.art.gui.dialogs.new_document_dialog import (
    NewDocumentConfig,
)
from airunner_model.models.drawingpad_settings import (
    DrawingPadSettings,
)
from airunner_model.models.controlnet_settings import (
    ControlnetSettings,
)
from airunner_model.models.image_to_image_settings import (
    ImageToImageSettings,
)
from airunner_model.models.outpaint_settings import OutpaintSettings
from airunner_model.models.brush_settings import BrushSettings
from airunner_model.models.metadata_settings import MetadataSettings
from airunner.components.art.gui.widgets.canvas.canvas_widget import (
    CanvasWidget,
)


def test_start_new_document_flow_uses_dialog_config():
    """Accepted dialog results should reset the canvas with one size."""
    config = NewDocumentConfig(width=1920, height=1080)
    widget = SimpleNamespace(
        _show_new_document_dialog=Mock(return_value=config),
        _reset_canvas_document=Mock(),
    )

    CanvasWidget.start_new_document_flow(widget)

    widget._reset_canvas_document.assert_called_once_with(config)


def test_start_new_document_flow_ignores_cancelled_dialog():
    """Cancelled dialog results should not reset the canvas."""
    widget = SimpleNamespace(
        _show_new_document_dialog=Mock(return_value=None),
        _reset_canvas_document=Mock(),
    )

    CanvasWidget.start_new_document_flow(widget)

    widget._reset_canvas_document.assert_not_called()


def test_resolve_document_config_prefers_explicit_document_size():
    """Saved document metadata should override legacy size inference."""
    widget = SimpleNamespace(
        _infer_legacy_document_config=Mock(),
    )

    config = CanvasWidget._resolve_document_config(
        widget,
        {"document": {"width": 2048, "height": 1152}},
        [],
    )

    assert config == NewDocumentConfig(width=2048, height=1152)
    widget._infer_legacy_document_config.assert_not_called()


def test_infer_legacy_document_config_uses_first_layer_image():
    """Legacy files should infer size from the first image payload."""
    widget = SimpleNamespace(
        application_settings=SimpleNamespace(working_width=512, working_height=512),
        _extract_legacy_layer_size=Mock(
            side_effect=[None, (1600, 900), (2048, 2048)]
        ),
    )
    layers_data = [{}, {}, {}]

    config = CanvasWidget._infer_legacy_document_config(widget, layers_data)

    assert config == NewDocumentConfig(width=1600, height=900)


def test_decode_binary_image_size_reads_airaw_header():
    """AIRAW1 payloads should expose width and height without decoding."""
    raw = (
        b"AIRAW1"
        + (320).to_bytes(4, "big")
        + (240).to_bytes(4, "big")
        + b"\x00" * (320 * 240 * 4)
    )

    assert CanvasWidget._decode_binary_image_size(raw) == (320, 240)


def test_fit_document_to_viewport_redraws_and_fits_canvas():
    """Document changes should redraw and fit the canvas view."""
    view = SimpleNamespace(
        do_draw=Mock(),
        fit_document_in_view=Mock(),
    )
    widget = SimpleNamespace(ui=SimpleNamespace(canvas_container=view))

    CanvasWidget._fit_document_to_viewport(widget)

    view.do_draw.assert_called_once_with(force_draw=True)
    view.fit_document_in_view.assert_called_once_with()


def test_apply_document_size_updates_document_and_working_dimensions():
    """New documents should persist fixed bounds separately from grid size."""
    updates = []
    widget = SimpleNamespace(
        update_application_settings=lambda **kwargs: updates.append(kwargs),
    )

    CanvasWidget._apply_document_size(
        widget,
        NewDocumentConfig(width=1600, height=900),
    )

    assert updates == [
        {"document_width": 1600},
        {"document_height": 900},
        {"working_width": 1600},
        {"working_height": 900},
    ]


def test_reset_new_document_view_anchor_reseeds_active_grid_origin():
    """Fresh documents should align the document and active-grid anchors."""
    view = SimpleNamespace(
        get_recentered_position=Mock(return_value=(144.0, 44.0)),
        get_centered_total_offset=Mock(return_value=QPointF(88.0, 66.0)),
        save_canvas_offset=Mock(),
        center_pos=QPointF(999.0, 999.0),
        _grid_compensation_offset=QPointF(4.0, 6.0),
        canvas_offset=QPointF(8.0, 10.0),
    )
    widget = SimpleNamespace(
        ui=SimpleNamespace(canvas_container=view),
        update_active_grid_settings=Mock(),
    )

    CanvasWidget._reset_new_document_view_anchor(
        widget,
        NewDocumentConfig(width=512, height=512),
    )

    assert view.center_pos == QPointF(144.0, 44.0)
    assert view._grid_compensation_offset == QPointF(0.0, 0.0)
    assert view.canvas_offset == QPointF(0.0, 0.0)
    view.get_centered_total_offset.assert_not_called()
    view.save_canvas_offset.assert_called_once_with()
    widget.update_active_grid_settings.assert_called_once_with(
        pos_x=144,
        pos_y=44,
    )


def test_ensure_drawing_pad_defaults_creates_document_sized_blank_layer():
    """New layers should start with a transparent image for the document."""
    widget = SimpleNamespace(
        _document_origin=Mock(return_value=(144, 44)),
        _create_blank_document_binary=Mock(return_value=b"blank-image"),
        update_drawing_pad_settings=Mock(),
    )

    with patch.object(
        DrawingPadSettings.objects,
        "filter_by_first",
        return_value=None,
    ):
        CanvasWidget._ensure_drawing_pad_defaults(widget, 7)

    widget.update_drawing_pad_settings.assert_called_once_with(
        layer_id=7,
        image=b"blank-image",
        x_pos=144,
        y_pos=44,
    )


def test_initialize_layer_defaults_skips_global_settings_models():
    """Brush and metadata settings are global, not per-layer rows."""
    widget = SimpleNamespace(_ensure_drawing_pad_defaults=Mock())

    with patch.object(
        ControlnetSettings.objects,
        "filter_by",
        return_value=[object()],
    ), patch.object(
        ImageToImageSettings.objects,
        "filter_by",
        return_value=[object()],
    ), patch.object(
        OutpaintSettings.objects,
        "filter_by",
        return_value=[object()],
    ), patch.object(
        BrushSettings.objects,
        "filter_by",
    ) as brush_filter, patch.object(
        BrushSettings.objects,
        "create",
    ) as brush_create, patch.object(
        MetadataSettings.objects,
        "filter_by",
    ) as metadata_filter, patch.object(
        MetadataSettings.objects,
        "create",
    ) as metadata_create:
        CanvasWidget._initialize_layer_defaults(widget, 1)

    widget._ensure_drawing_pad_defaults.assert_called_once_with(1)
    brush_filter.assert_not_called()
    brush_create.assert_not_called()
    metadata_filter.assert_not_called()
    metadata_create.assert_not_called()


def test_clear_canvas_state_clears_scene_reset_caches():
    """Document reset should clear scene caches before the clear signal."""
    scene = SimpleNamespace(
        original_item_positions={object(): QPointF(10.0, 12.0)},
        _pending_layer_images={1: object()},
        _skip_recenter_on_clear=False,
    )
    clear_flags = []
    widget = SimpleNamespace(
        api=SimpleNamespace(
            art=SimpleNamespace(
                canvas=SimpleNamespace(
                    clear=lambda: clear_flags.append(
                        scene._skip_recenter_on_clear
                    )
                )
            )
        ),
        ui=SimpleNamespace(canvas_container=SimpleNamespace(scene=scene)),
        images=[object()],
        current_image_index=3,
        draggable_pixmaps_in_scene=[object()],
        active_grid_area_pivot_point=QPoint(4, 5),
        active_grid_area_position=QPoint(6, 7),
    )

    CanvasWidget._clear_canvas_state(widget)

    assert clear_flags == [True]
    assert scene.original_item_positions == {}
    assert scene._pending_layer_images == {}
    assert scene._skip_recenter_on_clear is False
    assert widget.images == []
    assert widget.current_image_index == 0
    assert widget.draggable_pixmaps_in_scene == []
    assert widget.active_grid_area_pivot_point == QPoint(0, 0)
    assert widget.active_grid_area_position == QPoint(0, 0)