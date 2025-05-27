"""
Business logic for CustomScene: image manipulation, history, filter, and settings logic.
Decoupled from PySide6 GUI code for testability.
"""

from typing import Optional, Dict, Tuple
from PySide6.QtCore import QPoint, QPointF
from airunner.enums import CanvasToolName
from PIL import Image


class CustomSceneLogic:
    def __init__(self, application_settings, update_application_settings):
        self.application_settings = application_settings
        self.update_application_settings = update_application_settings
        self.undo_history = []
        self.redo_history = []
        self.image_backup = None
        self.previewing_filter = False

    def add_image_to_undo(self, image):
        self.undo_history.append({"image": image if image is not None else None})

    def add_image_to_redo(self, image):
        self.redo_history.append({"image": image if image is not None else None})

    def clear_history(self):
        self.undo_history = []
        self.redo_history = []

    def apply_filter(self, image, filter_object):
        if not image:
            return None
        self.image_backup = image.copy()
        self.previewing_filter = True
        # filter_object may be a class (e.g. ImageFilter.BLUR), so use image.filter()
        return image.filter(filter_object)

    def cancel_filter(self):
        image = None
        if self.image_backup:
            image = self.image_backup.copy()
            self.image_backup = None
        self.previewing_filter = False
        return image

    def rotate_image(self, image, angle: float):
        if image is not None:
            return image.rotate(angle, expand=True)
        return None

    def get_pivot_point(self, settings) -> QPointF:
        try:
            return QPointF(settings.x_pos, settings.y_pos)
        except Exception:
            return QPointF(0, 0)

    def get_current_tool(self) -> Optional[CanvasToolName]:
        val = self.application_settings.current_tool
        if val is None:
            return None
        try:
            return CanvasToolName(val)
        except Exception:
            return None

    def resize_image(self, image):
        if image is None:
            return None
        max_size = (
            self.application_settings.working_width,
            self.application_settings.working_height,
        )
        image = image.copy()
        image.thumbnail(max_size, Image.Resampling.BICUBIC)
        return image

    def cut_image(self, image, copy_func, add_undo_func, delete_func):
        # copy_func: function to copy image to clipboard
        # add_undo_func: function to add image to undo history
        # delete_func: function to delete image from scene
        copied = copy_func(image)
        if copied is not None:
            add_undo_func(image)
            delete_func()
        return copied

    def copy_image(self, image, clipboard_func):
        # clipboard_func: function to copy image to clipboard
        return clipboard_func(image)

    def rotate_image_and_record(self, image, angle, add_undo_func=None):
        if image is not None:
            if add_undo_func:
                add_undo_func(image)
            return image.rotate(angle, expand=True)
        return None
