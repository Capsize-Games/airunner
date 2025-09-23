import os
import datetime
import re
from PySide6.QtWidgets import QSpacerItem, QSizePolicy, QPushButton, QWidget
from PySide6.QtGui import QPixmap, Qt, QDrag
from PySide6.QtCore import QMimeData, QUrl
from typing import Dict
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.art.gui.widgets.canvas.templates.batch_container_ui import (
    Ui_batch_conatiner,
)
from airunner.components.art.gui.widgets.canvas.templates.image_layer_item_ui import (
    Ui_image_layer_item,
)
from airunner.enums import SignalCode
from airunner.utils.image.export_image import get_today_folder


class BatchContainer(BaseWidget):
    widget_class_ = Ui_batch_conatiner

    def __init__(self, *args, **kwargs):
        self.initialized = False
        self.signal_handlers = {
            SignalCode.SD_UPDATE_BATCH_IMAGES_SIGNAL: self.update_batch_images,
        }
        self.current_date_folder = (
            None  # Tracks the currently selected date folder
        )
        self.current_batch_folder = (
            None  # Tracks the currently selected batch folder
        )
        self.back_button = (
            None  # Reference to the back button when in a batch folder
        )
        super().__init__(*args, **kwargs)
        self.setup_ui_connections()

    def setup_ui_connections(self):
        """Set up UI signal connections."""
        self.ui.image_folders.currentTextChanged.connect(
            self.on_image_folders_currentTextChanged
        )

    def _add_image_layer_item(self, image_path: str, total: int, layout):
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            pixmap = pixmap.scaled(
                256,
                256,
                aspectMode=Qt.KeepAspectRatio,
                mode=Qt.SmoothTransformation,
            )
        image_layer_item = ImageLayerItemWidget(image_path)
        image_layer_item.ui.image.setPixmap(pixmap)

        if total is not None:
            image_layer_item.ui.total_images.setText(f"{total} in batch")
            image_layer_item.ui.total_images.setVisible(True)
            # Set up batch folder information for click handling
            image_layer_item.batch_folder = os.path.dirname(image_path)
            image_layer_item.is_batch = True
            image_layer_item.parent_widget = self
        else:
            # Hide the label for individual images (not part of a batch)
            image_layer_item.ui.total_images.setVisible(False)
            image_layer_item.is_batch = False

        layout.addWidget(image_layer_item)

    def _clear_layout(self, layout):
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.setParent(None)
            else:
                layout.takeAt(i)

    def showEvent(self, event):
        super().showEvent(event)
        if not self.initialized:
            self.initialized = True
            self.populate_date_folders()
            self.populate_current_folder()

    def populate_date_folders(self):
        """Populate the combo box with available date folders."""
        base_path = self.path_settings.image_path
        today = datetime.datetime.now().strftime("%Y%m%d")

        # Disconnect signal temporarily to prevent triggering while populating
        self.ui.image_folders.blockSignals(True)
        self.ui.image_folders.clear()

        # Get all folders in the base path
        if os.path.exists(base_path):
            folders = [
                d
                for d in os.listdir(base_path)
                if os.path.isdir(os.path.join(base_path, d))
                and len(d) == 8
                and d.isdigit()
            ]

            # Convert to display format and sort in reverse (newest first)
            display_folders = []
            for folder in folders:
                try:
                    year = folder[0:4]
                    month = folder[4:6]
                    day = folder[6:8]
                    display_format = f"{year}-{month}-{day}"
                    display_folders.append((display_format, folder))
                except (ValueError, IndexError):
                    # Skip folders that don't match the expected format
                    pass

            # Sort by actual date (newest first)
            display_folders.sort(key=lambda x: x[1], reverse=True)

            # Add to combo box
            for display_folder, _ in display_folders:
                self.ui.image_folders.addItem(display_folder)

            # Select today's date if it exists
            today_display = f"{today[0:4]}-{today[4:6]}-{today[6:8]}"
            index = self.ui.image_folders.findText(today_display)
            if index >= 0:
                self.ui.image_folders.setCurrentIndex(index)
            elif self.ui.image_folders.count() > 0:
                # Select first item if today doesn't exist
                self.ui.image_folders.setCurrentIndex(0)

        # Reconnect signal
        self.ui.image_folders.blockSignals(False)

        # Store the currently selected date folder
        if self.ui.image_folders.currentText():
            self.current_date_folder = self._get_date_folder_path(
                self.ui.image_folders.currentText()
            )
        else:
            # If no folders exist, use today's folder
            self.current_date_folder = get_today_folder(
                self.path_settings.image_path
            )

    def _get_date_folder_path(self, display_date: str) -> str:
        """Convert display date (YYYY-MM-DD) to folder path."""
        try:
            # Convert from display format to folder name format
            date_parts = display_date.split("-")
            folder_name = f"{date_parts[0]}{date_parts[1]}{date_parts[2]}"
            return os.path.join(self.path_settings.image_path, folder_name)
        except (ValueError, IndexError):
            # Default to today's folder if conversion fails
            return get_today_folder(self.path_settings.image_path)

    def on_image_folders_currentTextChanged(self, text: str):
        """Handle selection change in the image_folders combobox."""
        if not text:
            return

        # Update current date folder and reset batch folder
        self.current_date_folder = self._get_date_folder_path(text)
        self.current_batch_folder = None

        # Remove back button if it exists
        self._remove_back_button()

        # Populate the layout with the selected date folder content
        self.populate_current_folder()

    def _create_back_button(self):
        """Create and add a back button below the combobox."""
        if self.back_button is None:
            self.back_button = QPushButton("← Back to date folder")
            self.back_button.clicked.connect(self.on_back_button_clicked)
            self.ui.gridLayout.addWidget(self.back_button, 1, 0, 1, 1)
            # Move scroll area down one row
            self.ui.gridLayout.removeWidget(self.ui.scrollArea)
            self.ui.gridLayout.addWidget(self.ui.scrollArea, 2, 0, 1, 1)

    def _remove_back_button(self):
        """Remove the back button if it exists."""
        if self.back_button is not None:
            self.ui.gridLayout.removeWidget(self.back_button)
            self.back_button.deleteLater()
            self.back_button = None

            # Move scroll area back up
            self.ui.gridLayout.removeWidget(self.ui.scrollArea)
            self.ui.gridLayout.addWidget(self.ui.scrollArea, 1, 0, 1, 1)

    def on_back_button_clicked(self):
        """Handle back button click to return to date folder view."""
        self.current_batch_folder = None
        self._remove_back_button()
        self.populate_current_folder()

    def on_batch_clicked(self, batch_folder: str):
        """Handle batch folder click to navigate into the batch."""
        self.current_batch_folder = batch_folder
        self._create_back_button()
        self.populate_current_folder()

    def find_date_loose_images(self, folder_path: str) -> list:
        """Return a list of loose images (not in batches) for the given folder."""
        if not folder_path or not os.path.exists(folder_path):
            return []

        loose_images = sorted(
            [
                os.path.join(folder_path, f)
                for f in os.listdir(folder_path)
                if os.path.isfile(os.path.join(folder_path, f))
            ]
        )
        return loose_images

    def find_date_batches(self, folder_path: str) -> list:
        """Return a list of batch folders and their images for the given folder."""
        if not folder_path or not os.path.exists(folder_path):
            return []

        batch_folders = sorted(
            [
                os.path.join(folder_path, d)
                for d in os.listdir(folder_path)
                if os.path.isdir(os.path.join(folder_path, d))
                and d.startswith("batch_")
            ],
            key=lambda x: natural_sort_key(os.path.basename(x)),
        )
        batches = []
        for batch in batch_folders:
            images = sorted(
                [
                    os.path.join(batch, f)
                    for f in os.listdir(batch)
                    if os.path.isfile(os.path.join(batch, f))
                ]
            )
            batches.append({"batch_folder": batch, "images": images})
        return batches

    def find_batch_images(self, batch_folder: str) -> list:
        """Return a list of images in a specific batch folder."""
        if not os.path.exists(batch_folder):
            return []

        return sorted(
            [
                os.path.join(batch_folder, f)
                for f in os.listdir(batch_folder)
                if os.path.isfile(os.path.join(batch_folder, f))
            ]
        )

    def populate_current_folder(self):
        """Populate the layout based on the current navigation state."""
        container = self.ui.scrollArea.widget()
        layout = container.layout()
        self._clear_layout(layout)

        # Ensure we have a valid date folder before populating
        if not self.current_date_folder:
            self.current_date_folder = get_today_folder(
                self.path_settings.image_path
            )

        if self.current_batch_folder:
            # We're viewing a batch folder - display all images in this batch
            images = self.find_batch_images(self.current_batch_folder)
            for image_path in images:
                self._add_image_layer_item(image_path, None, layout)
        else:
            # We're viewing a date folder - display batches and loose images
            batches = self.find_date_batches(self.current_date_folder)
            loose_images = self.find_date_loose_images(
                self.current_date_folder
            )

            # Add batch images
            for batch in batches:
                images = batch["images"]
                if not images:
                    continue
                self._add_image_layer_item(images[0], len(images), layout)

            # Add loose images
            for image_path in loose_images:
                self._add_image_layer_item(image_path, None, layout)

        # Add spacer at the bottom
        spacer = QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        layout.addItem(spacer)

    def update_batch_images(self, data: Dict):
        """Update the layout with new batch images."""
        # Ensure current_date_folder is valid before refreshing
        if not self.current_date_folder:
            self.current_date_folder = get_today_folder(
                self.path_settings.image_path
            )
        # Always refresh the UI to show new batches or images
        self.populate_current_folder()


class ImageLayerItemWidget(QWidget):
    def __init__(self, image_path=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = Ui_image_layer_item()
        self.ui.setupUi(self)
        self.ui.image.setFixedSize(256, 256)
        self.image_path = image_path
        self.batch_folder = None  # Will be set for batch folder items
        self.is_batch = False  # Flag to identify if this is a batch item
        self.parent_widget = None  # Reference to the parent BatchContainer

        # Set the cursor for better UX
        self.setCursor(Qt.PointingHandCursor)
        self.setAcceptDrops(
            False
        )  # This widget is a drag source, not a target
        self._drag_start_pos = None

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()

    def mouseMoveEvent(self, event):
        if self.is_batch:
            # Don't allow drag for batch folders
            return
        if (
            self._drag_start_pos is not None
            and (event.pos() - self._drag_start_pos).manhattanLength() > 10
        ):
            drag = QDrag(self)
            mime_data = QMimeData()
            if self.image_path:
                mime_data.setUrls([QUrl.fromLocalFile(self.image_path)])
                mime_data.setText(self.image_path)
            drag.setMimeData(mime_data)

            # Set drag pixmap for visual feedback, centered on cursor
            pixmap = self.ui.image.pixmap()
            if pixmap is not None and not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                drag.setPixmap(scaled_pixmap)
                center = scaled_pixmap.rect().center()
                drag.setHotSpot(center)

            drag.exec(Qt.CopyAction)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        # If this is a batch item and we have a parent widget reference, navigate into the batch
        if self.is_batch and self.parent_widget and self.batch_folder:
            self.parent_widget.on_batch_clicked(self.batch_folder)
        self._drag_start_pos = None


def natural_sort_key(s):
    """Helper for natural sorting (e.g., batch_2 before batch_10)."""
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split(r"(\d+)", s)
    ]
