"""Canvas Persistence Mixin.

Handles image persistence operations including export, import, load from files/URLs,
and asynchronous image data persistence to the database.
"""

from concurrent.futures import ThreadPoolExecutor
import os
import weakref
from PIL import Image
from PySide6.QtWidgets import QFileDialog
from PySide6.QtCore import Slot
from airunner.utils.image import export_image
from airunner.settings import AIRUNNER_VALID_IMAGE_FILES
from airunner.utils.image.dispatch_persist_result import (
    dispatch_persist_result,
)
from airunner.utils.image.persist_image_worker import persist_image_worker

PERSIST_EXECUTOR = ThreadPoolExecutor(max_workers=1)


class CanvasPersistenceMixin:
    """Provides image persistence functionality to canvas scenes.

    Handles:
    - Export/import images via file dialogs
    - Load images from file paths
    - Asynchronous image data persistence to database
    - Pending image flush mechanism
    """

    def on_export_image_signal(self):
        """Export current active image to a file.

        Opens a file dialog for the user to select export location and format.
        Supports all valid AI Runner image formats.
        """
        image = self.current_active_image
        if image:
            parent_window = self.views()[0].window()
            initial_dir = (
                self.last_export_path if self.last_export_path else ""
            )
            file_dialog = QFileDialog(
                parent_window,
                "Save Image",
                initial_dir,
                f"Image Files ({' '.join(AIRUNNER_VALID_IMAGE_FILES)})",
            )
            file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
            if file_dialog.exec() == QFileDialog.DialogCode.Accepted:
                file_path = file_dialog.selectedFiles()[0]
                if file_path == "":
                    return
                self.last_export_path = os.path.dirname(file_path)
                if not file_path.endswith(AIRUNNER_VALID_IMAGE_FILES):
                    file_path = f"{file_path}.png"
                export_image(image, file_path)

    def on_import_image_signal(self):
        """Import an image from a file.

        Opens a file dialog for the user to select an image file to import.
        Only works for drawing pad settings context.
        """
        if self.settings_key != "drawing_pad_settings":
            return
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Open Image",
            "",
            f"Image Files ({' '.join(AIRUNNER_VALID_IMAGE_FILES)})",
        )
        if file_path == "":
            return
        self.on_load_image_signal(file_path)

    def on_load_image_from_path(self, message):
        """Load an image from a file path provided in a message dict.

        Args:
            message: Dict containing 'image_path' key
        """
        image_path = message["image_path"]
        if image_path is None or image_path == "":
            return
        image = Image.open(image_path)
        self._load_image_from_object(image)

    def on_load_image_signal(self, image_path: str):
        """Load an image from a file path with undo history support.

        Args:
            image_path: Path to the image file to load
        """
        layer_id = self._add_image_to_undo()
        image = self._load_image(image_path)
        if self.application_settings.resize_on_paste:
            image = self._resize_image(image)
        self.current_active_image = image
        self.initialize_image(image)
        self._commit_layer_history_transaction(layer_id, "image")

    def _flush_pending_image(self):
        """Persist pending image data asynchronously to avoid UI stalls.

        Handles deferred image persistence using a background worker thread.
        Skips persistence if user is actively drawing or if no changes detected.
        """
        if self._is_user_interacting or getattr(
            self, "draw_button_down", False
        ):
            self._persist_timer.start(self._persist_delay_ms)
            return

        has_pending_image = self._pending_image_ref is not None
        has_pending_binary = self._pending_image_binary is not None
        if not has_pending_image and not has_pending_binary:
            return

        image_obj = self._pending_image_ref
        binary = self._pending_image_binary

        self._pending_image_ref = None
        self._pending_image_binary = None

        if binary is not None and binary == self._current_active_image_binary:
            return

        if binary is not None:
            self._current_active_image_binary = binary

        image_payload = None
        if has_pending_image and isinstance(image_obj, Image.Image):
            image_payload = image_obj

        if binary is None and image_payload is None:
            return

        try:
            layer_id = self._get_current_selected_layer_id()
        except Exception:
            layer_id = None

        self._persist_generation += 1
        generation = self._persist_generation

        future = PERSIST_EXECUTOR.submit(
            persist_image_worker,
            self.settings_key,
            layer_id,
            "image",
            image_payload,
            binary,
            self._raw_image_storage_enabled,
            generation,
        )
        self._active_persist_future = future
        future.add_done_callback(
            lambda fut, scene_ref=weakref.ref(self): dispatch_persist_result(
                scene_ref, fut
            )
        )

    @Slot(object)
    def _handle_persist_result(self, payload: object):
        """Handle the result from async image persistence worker.

        Args:
            payload: Result dict from persistence worker containing:
                - generation: Persistence generation number
                - error: Error message if persistence failed
                - binary: Persisted binary data
                - table_name: Database table name
                - column_name: Database column name
        """
        if not isinstance(payload, dict):
            return

        generation = payload.get("generation", 0)
        if generation < self._persist_generation:
            return

        self._active_persist_future = None

        error = payload.get("error")
        if error:
            if hasattr(self, "logger") and self.logger:
                self.logger.error(f"Image persistence failed: {error}")
            return

        binary = payload.get("binary")
        if binary is not None:
            self._current_active_image_binary = binary

        table_name = payload.get("table_name")
        column_name = payload.get("column_name")

        if table_name and column_name:
            try:
                self._notify_setting_updated(
                    setting_name=table_name,
                    column_name=column_name,
                    val=binary,
                )
            except Exception as exc:  # pragma: no cover - defensive
                if hasattr(self, "logger") and self.logger:
                    self.logger.error(
                        f"Failed to notify settings update for {table_name}.{column_name}: {exc}"
                    )

    @staticmethod
    def _load_image(image_path: str) -> Image:
        """Load an image from a file path.

        Args:
            image_path: Path to the image file

        Returns:
            Loaded PIL Image object
        """
        image = Image.open(image_path)
        return image
