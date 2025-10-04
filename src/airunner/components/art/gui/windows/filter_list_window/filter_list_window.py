from typing import Dict

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QDialogButtonBox,
    QWidget,
    QApplication,
)
from PySide6.QtCore import Qt

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
        for f in filters:
            item = QListWidgetItem(f.display_name or f.name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if f.auto_apply else Qt.Unchecked)
            # store id for later
            item.setData(Qt.UserRole, f.id)
            self._list.addItem(item)

        self._list.itemChanged.connect(self._on_item_changed)

    def _on_item_changed(self, item: QListWidgetItem):
        try:
            fid = item.data(Qt.UserRole)
            checked = item.checkState() == Qt.Checked
            ImageFilter.objects.update(fid, auto_apply=checked)
            # Do NOT apply to current canvas image when toggled; these flags
            # are for auto-applying to future generated images. The DB update
            # above is sufficient.
        except Exception:
            pass

    def accept(self):
        super().accept()

    def reject(self):
        super().reject()
