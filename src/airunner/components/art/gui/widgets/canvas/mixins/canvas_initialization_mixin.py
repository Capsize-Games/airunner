"""Canvas initialization mixin for signal registration and state setup."""

from typing import Dict, Any, Optional
from PySide6.QtCore import QTimer, QRect
from PySide6.QtGui import QImage
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)
from airunner.enums import SignalCode
from airunner.utils.settings.get_qsettings import get_qsettings


class CanvasInitializationMixin(MediatorMixin, SettingsMixin):
    """Handles canvas initialization and signal registration.

    This mixin provides functionality for:
    - Initializing canvas state variables
    - Setting up debounce timers
    - Registering signal handlers
    - Configuring performance caches
    """

    def _initialize_canvas_state(self, canvas_type: str) -> None:
        """Initialize all canvas state variables.

        Args:
            canvas_type: Type identifier for this canvas instance.
        """
        self._initialize_basic_state(canvas_type)
        self._initialize_mouse_state()
        self._initialize_history_state()
        self._initialize_event_state()
        self._initialize_persist_timer()
        self._initialize_cache_state()
        self._initialize_viewport_state()

    def _initialize_basic_state(self, canvas_type: str) -> None:
        """Initialize basic canvas state variables."""
        self._is_erasing = None
        self._is_drawing = None
        self.canvas_type = canvas_type
        self.image_backup = None
        self._current_active_image_ref = None
        self._current_active_image_binary = None
        self.previewing_filter = False
        self.painter = None
        self._painter_target = None
        self.image: Optional[QImage] = None
        self.item = None
        self._image_initialized: bool = False
        self.last_export_path = None
        self._target_size = None
        self.settings = get_qsettings()

    def _initialize_mouse_state(self) -> None:
        """Initialize mouse and interaction state variables."""
        self.last_pos = None
        self.start_pos = None
        self.selection_start_pos = None
        self.selection_stop_pos = None
        self.do_update = False
        self.generate_image_time_in_ms = 0.5
        self.do_generate_image = False
        self.generate_image_time = 0

    def _initialize_history_state(self) -> None:
        """Initialize history management state variables."""
        self.undo_history = []
        self.redo_history = []
        self._history_transactions: Dict[int | None, Dict[str, Any]] = {}
        self._structure_history_transaction: Optional[Dict[str, Any]] = None

    def _initialize_event_state(self) -> None:
        """Initialize event handling state variables."""
        self.right_mouse_button_pressed = False
        self.handling_event = False
        self._original_item_positions = {}

    def _initialize_persist_timer(self) -> None:
        """Initialize debounce timer for image persistence."""
        self._persist_timer = QTimer()
        self._persist_timer.setSingleShot(True)
        self._persist_timer.timeout.connect(self._flush_pending_image)
        self._pending_image_binary = None
        self._pending_image_ref = None
        self._persist_delay_ms = 1000
        self._active_persist_future = None
        self._persist_generation = 0

    def _initialize_cache_state(self) -> None:
        """Initialize performance caches and feature flags."""
        self._raw_image_storage_enabled = True
        self._current_active_image_hash = None
        self._qimage_cache = None
        self._qimage_cache_size = None
        self._qimage_cache_hash = None
        self._active_grid_cache = None
        self._active_grid_cache_time = 0

    def _initialize_viewport_state(self) -> None:
        """Initialize viewport and layer rendering state."""
        self._is_user_interacting = False
        self.is_dragging = False
        self._extended_viewport_rect = QRect(-2000, -2000, 4000, 4000)
        self._layer_items = {}
        self._layers_initialized = False
        self._surface_growth_step = 128
        self._minimum_surface_size = 128

    def _register_canvas_signals(self) -> None:
        """Register all signal handlers for canvas operations."""
        self._register_image_operation_signals()
        self._register_filter_signals()
        self._register_history_signals()
        self._register_layer_signals()

    def _register_image_operation_signals(self) -> None:
        """Register signals for image operations."""
        handlers = [
            (
                SignalCode.CANVAS_COPY_IMAGE_SIGNAL,
                self.on_canvas_copy_image_signal,
            ),
            (
                SignalCode.CANVAS_CUT_IMAGE_SIGNAL,
                self.on_canvas_cut_image_signal,
            ),
            (
                SignalCode.CANVAS_ROTATE_90_CLOCKWISE_SIGNAL,
                self.on_canvas_rotate_90_clockwise_signal,
            ),
            (
                SignalCode.CANVAS_ROTATE_90_COUNTER_CLOCKWISE_SIGNAL,
                self.on_canvas_rotate_90_counterclockwise_signal,
            ),
            (
                SignalCode.CANVAS_PASTE_IMAGE_SIGNAL,
                self.on_paste_image_from_clipboard,
            ),
            (
                SignalCode.CANVAS_EXPORT_IMAGE_SIGNAL,
                self.on_export_image_signal,
            ),
            (
                SignalCode.CANVAS_IMPORT_IMAGE_SIGNAL,
                self.on_import_image_signal,
            ),
            (
                SignalCode.SEND_IMAGE_TO_CANVAS_SIGNAL,
                self.on_send_image_to_canvas_signal,
            ),
            (
                SignalCode.CANVAS_LOAD_IMAGE_FROM_PATH_SIGNAL,
                self.on_load_image_from_path,
            ),
            (
                SignalCode.ENGINE_RESPONSE_WORKER_RESPONSE_SIGNAL,
                self.on_image_generated_signal,
            ),
            (SignalCode.CANVAS_CLEAR, self.on_canvas_clear_signal),
        ]
        for signal, handler in handlers:
            self.register(signal, handler)

    def _register_filter_signals(self) -> None:
        """Register signals for filter operations."""
        handlers = [
            (
                SignalCode.CANVAS_APPLY_FILTER_SIGNAL,
                self.on_apply_filter_signal,
            ),
            (
                SignalCode.CANVAS_CANCEL_FILTER_SIGNAL,
                self.on_cancel_filter_signal,
            ),
            (
                SignalCode.CANVAS_PREVIEW_FILTER_SIGNAL,
                self.on_preview_filter_signal,
            ),
        ]
        for signal, handler in handlers:
            self.register(signal, handler)

    def _register_history_signals(self) -> None:
        """Register signals for history operations."""
        handlers = [
            (SignalCode.UNDO_SIGNAL, self.on_action_undo_signal),
            (SignalCode.REDO_SIGNAL, self.on_action_redo_signal),
            (SignalCode.HISTORY_CLEAR_SIGNAL, self.on_clear_history_signal),
        ]
        for signal, handler in handlers:
            self.register(signal, handler)

    def _register_layer_signals(self) -> None:
        """Register signals for layer operations."""
        handlers = [
            (SignalCode.MASK_LAYER_TOGGLED, self.on_mask_layer_toggled),
            (
                SignalCode.LAYER_SELECTION_CHANGED,
                self._on_layer_selection_changed,
            ),
            (
                SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL,
                self.on_settings_changed,
            ),
            (
                SignalCode.LAYER_VISIBILITY_TOGGLED,
                self.on_layer_visibility_toggled,
            ),
            (SignalCode.LAYER_DELETED, self.on_layer_deleted),
            (SignalCode.LAYER_REORDERED, self.on_layer_reordered),
            (SignalCode.LAYERS_SHOW_SIGNAL, self.on_layers_show_signal),
            (SignalCode.LAYER_OPERATION_BEGIN, self.on_layer_operation_begin),
            (
                SignalCode.LAYER_OPERATION_COMMIT,
                self.on_layer_operation_commit,
            ),
            (
                SignalCode.LAYER_OPERATION_CANCEL,
                self.on_layer_operation_cancel,
            ),
        ]
        for signal, handler in handlers:
            self.register(signal, handler)
