"""Mixin for initialization logic in CustomGraphicsView.

This mixin handles attribute initialization and signal registration.
"""

from typing import Optional, Dict
from PySide6.QtCore import QPointF, QPoint, Qt, QTimer
from PySide6.QtWidgets import QGraphicsItemGroup, QGraphicsView
from PySide6.QtGui import QColor

from airunner.components.art.gui.widgets.canvas.draggables.active_grid_area import (
    ActiveGridArea,
)
from airunner.components.art.gui.widgets.canvas.zoom_handler import ZoomHandler
from airunner.enums import SignalCode
from airunner.utils.settings import get_qsettings


class InitializationMixin:
    """Provides initialization logic for graphics view.

    This mixin manages:
    - Attribute initialization
    - Signal handler registration
    - View configuration
    - Timer setup

    Dependencies:
        - self.zero_point: Zero point property
        - self.viewport(): Qt viewport method
        - self.setAlignment(): Qt alignment method
        - self.setViewportUpdateMode(): Qt viewport update mode
        - self.setOptimizationFlags(): Qt optimization flags
        - self.setFrameShape(): Qt frame shape
        - self.setMouseTracking(): Qt mouse tracking
        - self.register(): Signal registration from MediatorMixin
        - Various signal handler methods
    """

    def _initialize_attributes(self):
        """Initialize all instance attributes.

        Sets up text dragging state, scene references, drawing flags,
        zoom handler, offsets, timers, and caches.
        """
        # Text area drag/creation state
        self._text_dragging = False
        self._text_drag_start = None
        self._temp_rubberband = None

        # Scene and initialization flags
        self._initialized = False
        self._scene = None
        self._scene_is_active = False
        self.initialized = False

        # Visual state
        self._canvas_color: str = "#000000"
        self.current_background_color: Optional[QColor] = None
        self.active_grid_area: Optional[ActiveGridArea] = None

        # Drawing state
        self.do_draw_layers: bool = True
        self.drawing: bool = False
        self.pixmaps: Dict = {}
        self.line_group: Optional[QGraphicsItemGroup] = None
        self.grid_item = None

        # Position tracking
        self.last_pos: QPoint = self.zero_point
        self.center_pos: QPointF = QPointF(0, 0)
        self._canvas_offset = QPointF(0, 0)
        self._grid_compensation_offset = QPointF(0, 0)

        # Text items
        self._text_items = []
        self._text_item_layer_map = {}
        self._editing_text_item = None

        # Resize and restoration state
        self._last_viewport_size = self.viewport().size()
        self._is_restoring_state = False

        # Panning state
        self._middle_mouse_pressed: bool = False
        self._pending_pan_event = False

        # Handlers and utilities
        self.zoom_handler: ZoomHandler = ZoomHandler()
        self.settings = get_qsettings()
        self._cursor_cache = {}

    def _configure_view_settings(self):
        """Configure Qt view settings for proper rendering.

        Sets alignment, viewport update mode, optimization flags,
        frame shape, and mouse tracking.
        """
        # Enable mouse tracking
        self.setMouseTracking(True)

        # Handle negative coordinates properly
        self.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )

        # Ensure proper repaints when items mutate
        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.SmartViewportUpdate
        )

        # Optimization flags for performance
        self.setOptimizationFlags(
            QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing
            | QGraphicsView.OptimizationFlag.DontSavePainterState
        )

        # No frame border
        self.setFrameShape(QGraphicsView.Shape.NoFrame)

    def _register_signal_handlers(self):
        """Register all signal handlers for canvas events.

        Connects signal codes to their respective handler methods.
        """
        signal_handlers = {
            SignalCode.APPLICATION_TOOL_CHANGED_SIGNAL: self.on_tool_changed_signal,
            SignalCode.CANVAS_ZOOM_LEVEL_CHANGED: self.on_zoom_level_changed_signal,
            SignalCode.SET_CANVAS_COLOR_SIGNAL: self.set_canvas_color,
            SignalCode.UPDATE_SCENE_SIGNAL: self.update_scene,
            SignalCode.CANVAS_CLEAR_LINES_SIGNAL: self.clear_lines,
            SignalCode.SCENE_DO_DRAW_SIGNAL: self.on_canvas_do_draw_signal,
            SignalCode.APPLICATION_MAIN_WINDOW_LOADED_SIGNAL: self.on_main_window_loaded_signal,
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: self.on_application_settings_changed_signal,
            SignalCode.MASK_GENERATOR_WORKER_RESPONSE_SIGNAL: self.on_mask_generator_worker_response_signal,
            SignalCode.RECENTER_GRID_SIGNAL: self.on_recenter_grid_signal,
            SignalCode.CANVAS_IMAGE_UPDATED_SIGNAL: self.on_canvas_image_updated_signal,
            SignalCode.CANVAS_UPDATE_IMAGE_POSITIONS: self.updateImagePositions,
        }
        for signal_code, handler in signal_handlers.items():
            self.register(signal_code, handler)

    def _setup_pan_timer(self):
        """Setup timer for pan update batching.

        Creates a single-shot timer that calls _do_pan_update
        to batch multiple pan events together.
        """
        self._pan_update_timer = QTimer()
        self._pan_update_timer.setSingleShot(True)
        self._pan_update_timer.timeout.connect(self._do_pan_update)
