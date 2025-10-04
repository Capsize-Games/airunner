from typing import Dict

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QDialogButtonBox,
    QWidget,
    QApplication,
    QCheckBox,
    QHBoxLayout,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor

import logging

from airunner.components.art.data.image_filter import ImageFilter
from airunner.components.art.utils.image_filter_utils import (
    build_filter_object_from_model,
)


class FilterListWindow(QDialog):
    """Simple dialog listing available image filters with checkboxes to toggle
    auto-apply. Checking a filter updates the `auto_apply` column in the DB
    immediately.
    """

    def __init__(self, parent=None):
        # Initialize QDialog with an optional parent and show it non-modally
        super().__init__(parent)
        self.setWindowTitle("Image Filters")
        # Provide a sensible default size so the window isn't tiny
        try:
            self.resize(420, 480)
            self.setMinimumSize(300, 240)
        except Exception:
            pass
        self._list = QListWidget(self)
        self._list.setSelectionMode(QListWidget.NoSelection)
        # Inherit the application's stylesheet (if any) so dialog visuals
        # match the rest of the app. Fall back to parent's stylesheet first
        # then to the QApplication stylesheet.
        try:
            app = QApplication.instance()
            parent_ss = None
            if parent is not None and hasattr(parent, "styleSheet"):
                parent_ss = parent.styleSheet()
            if parent_ss:
                self.setStyleSheet(parent_ss)
            elif app is not None and app.styleSheet():
                self.setStyleSheet(app.styleSheet())
        except Exception:
            pass

        # Styling is provided by the app theme QSS (inherited above).

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self._list)
        layout.addWidget(self._buttons)

        self._load_filters()
        # Show non-modally and raise so it appears on top
        self.show()
        try:
            self.raise_()
        except Exception:
            pass

    def _load_filters(self):
        self._list.clear()
        filters = ImageFilter.objects.all() or []
        logger = logging.getLogger(__name__)
        for f in filters:
            # Create an empty list item and a widget containing a real QCheckBox
            item = QListWidgetItem()
            container = QWidget()
            row_layout = QHBoxLayout(container)
            row_layout.setContentsMargins(4, 2, 4, 2)
            row_layout.setSpacing(8)

            checkbox = QCheckBox(f.display_name or f.name, container)
            checkbox.setChecked(bool(f.auto_apply))

            # Connect directly to update DB when toggled so we don't rely on
            # QListWidget's itemChanged which may not trigger QCheckBox styling.
            def _on_checkbox_state_changed(state, fid=f.id):
                try:
                    logger.debug(
                        "Updating ImageFilter id=%s auto_apply=%s",
                        fid,
                        state == Qt.Checked,
                    )
                    success = ImageFilter.objects.update(
                        fid, auto_apply=(state == Qt.Checked)
                    )
                    logger.debug("ImageFilter update success=%s", success)
                except Exception:
                    logger.exception(
                        "Failed to update ImageFilter(id=%s) auto_apply", fid
                    )

            checkbox.stateChanged.connect(_on_checkbox_state_changed)

            row_layout.addWidget(checkbox)
            row_layout.addStretch(1)

            item.setSizeHint(container.sizeHint())
            # store id for later if needed
            item.setData(Qt.UserRole, f.id)
            self._list.addItem(item)
            self._list.setItemWidget(item, container)

        # We use embedded QCheckBox widgets and connect their stateChanged
        # signals directly to the DB update. Avoid connecting the legacy
        # QListWidget.itemChanged handler because it reads the
        # QListWidgetItem.checkState() and can overwrite updates when the
        # list item isn't actually used as the checkbox owner.

    def _on_item_changed(self, item: QListWidgetItem):
        try:
            fid = item.data(Qt.UserRole)
            checked = item.checkState() == Qt.Checked
            ImageFilter.objects.update(fid, auto_apply=checked)
            # Do NOT apply to current canvas image when toggled; these flags
            # are for auto-applying to future generated images. The DB update
            # above is sufficient.
        except Exception:
            logging.getLogger(__name__).exception(
                "Error handling itemChanged for ImageFilter id=%s", fid
            )

    def accept(self):
        super().accept()

    def reject(self):
        super().reject()
