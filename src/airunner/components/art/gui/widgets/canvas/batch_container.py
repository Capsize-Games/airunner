import datetime
import os
import re
from typing import Dict, List, Optional

from PySide6.QtCore import QModelIndex, QTimer, QSize
from PySide6.QtWidgets import QAbstractItemView, QListView

from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.art.gui.widgets.canvas.templates.batch_container_ui import (
    Ui_batch_conatiner,
)
from airunner.components.art.gui.widgets.canvas.thumbnail_model import (
    GalleryEntry,
    ThumbnailListModel,
)
from airunner.enums import SignalCode
from airunner.utils.image.export_image import get_today_folder


class BatchContainer(BaseWidget):
    """Widget that displays generated images grouped by date and batch."""

    widget_class_ = Ui_batch_conatiner

    def __init__(self, *args, **kwargs):
        self.initialized = False
        self.signal_handlers = {
            SignalCode.SD_UPDATE_BATCH_IMAGES_SIGNAL: self.update_batch_images,
        }
        self.current_date_folder: Optional[str] = None
        self.current_batch_folder: Optional[str] = None

        self._batch_update_timer = QTimer()
        self._batch_update_timer.setSingleShot(True)
        self._batch_update_timer.timeout.connect(self._do_batch_update)

        super().__init__(*args, **kwargs)

        cache_root = os.path.join(self.path_settings.image_path, ".thumbnails")
        self._model = ThumbnailListModel(thumb_size=256, cache_dir=cache_root)
        self.ui.galleryView.setModel(self._model)
        self._configure_gallery_view()
        self.setup_ui_connections()
        self._set_back_button_visible(False)

    def setup_ui_connections(self):
        """Set up UI signal connections."""

        self.ui.image_folders.currentTextChanged.connect(
            self.on_image_folders_currentTextChanged
        )
        self.ui.backButton.clicked.connect(self.on_back_button_clicked)
        self.ui.galleryView.clicked.connect(self._handle_item_clicked)
        self.ui.galleryView.activated.connect(self._handle_item_activated)

    def _configure_gallery_view(self) -> None:
        view = self.ui.galleryView
        view.setViewMode(QListView.IconMode)
        view.setResizeMode(QListView.Adjust)
        view.setMovement(QListView.Static)
        view.setUniformItemSizes(True)
        view.setIconSize(QSize(self._model.thumb_size, self._model.thumb_size))
        view.setSpacing(16)
        view.setWordWrap(True)
        view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        view.setSelectionMode(QAbstractItemView.SingleSelection)
        view.setSelectionRectVisible(False)
        view.setDragEnabled(True)
        view.setDragDropMode(QAbstractItemView.DragOnly)
        view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        view.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        if not self.initialized:
            self.initialized = True
            self.populate_date_folders()
            self.populate_current_folder()

    def populate_date_folders(self):
        """Populate the combo box with available date folders."""

        base_path = self.path_settings.image_path
        today = datetime.datetime.now().strftime("%Y%m%d")

        self.ui.image_folders.blockSignals(True)
        self.ui.image_folders.clear()

        if os.path.exists(base_path):
            folders = [
                d
                for d in os.listdir(base_path)
                if os.path.isdir(os.path.join(base_path, d))
                and len(d) == 8
                and d.isdigit()
            ]

            display_folders = []
            for folder in folders:
                try:
                    year = folder[0:4]
                    month = folder[4:6]
                    day = folder[6:8]
                    display_format = f"{year}-{month}-{day}"
                    display_folders.append((display_format, folder))
                except (ValueError, IndexError):
                    pass

            display_folders.sort(key=lambda x: x[1], reverse=True)

            for display_folder, _ in display_folders:
                self.ui.image_folders.addItem(display_folder)

            today_display = f"{today[0:4]}-{today[4:6]}-{today[6:8]}"
            index = self.ui.image_folders.findText(today_display)
            if index >= 0:
                self.ui.image_folders.setCurrentIndex(index)
            elif self.ui.image_folders.count() > 0:
                self.ui.image_folders.setCurrentIndex(0)

        self.ui.image_folders.blockSignals(False)

        if self.ui.image_folders.currentText():
            self.current_date_folder = self._get_date_folder_path(
                self.ui.image_folders.currentText()
            )
        else:
            self.current_date_folder = get_today_folder(
                self.path_settings.image_path
            )

    def _get_date_folder_path(self, display_date: str) -> str:
        try:
            date_parts = display_date.split("-")
            folder_name = f"{date_parts[0]}{date_parts[1]}{date_parts[2]}"
            return os.path.join(self.path_settings.image_path, folder_name)
        except (ValueError, IndexError):
            return get_today_folder(self.path_settings.image_path)

    def on_image_folders_currentTextChanged(self, text: str):
        """Handle selection change in the image_folders combobox."""

        if not text:
            return

        self.current_date_folder = self._get_date_folder_path(text)
        self.current_batch_folder = None
        self._set_back_button_visible(False)
        self.populate_current_folder()

    def on_back_button_clicked(self):
        """Return to the date folder view."""

        self.current_batch_folder = None
        self._set_back_button_visible(False)
        self.populate_current_folder()

    def on_batch_clicked(self, batch_folder: str):
        """Navigate into a batch folder."""

        self.current_batch_folder = batch_folder
        self._set_back_button_visible(True)
        self.populate_current_folder()

    def _handle_item_clicked(self, index: QModelIndex) -> None:
        entry = self._model.entry_at(index.row())
        if entry and entry.is_batch and entry.batch_folder:
            self.on_batch_clicked(entry.batch_folder)

    def _handle_item_activated(self, index: QModelIndex) -> None:
        self._handle_item_clicked(index)

    def _set_back_button_visible(self, visible: bool) -> None:
        self.ui.backButton.setVisible(visible)

    def find_date_loose_images(self, folder_path: str) -> List[str]:
        """Return loose (non-batch) image paths for the given date folder."""
        if not folder_path or not os.path.exists(folder_path):
            return []

        return sorted(
            [
                os.path.join(folder_path, f)
                for f in os.listdir(folder_path)
                if os.path.isfile(os.path.join(folder_path, f))
            ]
        )

    def find_date_batches(
        self, folder_path: str
    ) -> List[Dict[str, List[str]]]:
        """Return batch folders and their images within ``folder_path``."""
        if not folder_path or not os.path.exists(folder_path):
            return []

        batch_folders = sorted(
            [
                os.path.join(folder_path, d)
                for d in os.listdir(folder_path)
                if os.path.isdir(os.path.join(folder_path, d))
                and d.startswith("batch_")
            ],
            key=lambda path: natural_sort_key(os.path.basename(path)),
        )

        batches: List[Dict[str, List[str]]] = []
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

    def find_batch_images(self, batch_folder: str) -> List[str]:
        """Return image paths contained in the given batch folder."""
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
        """Populate the gallery view based on the current navigation state."""

        if not self.current_date_folder:
            self.current_date_folder = get_today_folder(
                self.path_settings.image_path
            )

        entries: List[GalleryEntry] = []

        if self.current_batch_folder:
            entries.extend(
                self._build_image_entries(self.current_batch_folder)
            )
        else:
            entries.extend(self._build_batch_entries(self.current_date_folder))
            entries.extend(self._build_loose_entries(self.current_date_folder))

        self._model.set_entries(entries)
        self.ui.galleryView.scrollToTop()

    def update_batch_images(self, data: Dict):
        """Schedule a refresh of the gallery view."""

        self._batch_update_timer.start(500)

    def _do_batch_update(self):
        if not self.current_date_folder:
            self.current_date_folder = get_today_folder(
                self.path_settings.image_path
            )
        self.populate_current_folder()

    def _build_batch_entries(self, folder_path: str) -> List[GalleryEntry]:
        """Create gallery entries for batch previews in ``folder_path``."""
        entries: List[GalleryEntry] = []
        batches = self.find_date_batches(folder_path)
        for batch in batches:
            images = batch.get("images", [])
            if not images:
                continue
            batch_folder = batch["batch_folder"]
            preview = images[0]
            total = len(images)
            name = os.path.basename(batch_folder)
            label = f"{name}\n{total} image{'s' if total != 1 else ''}"
            tooltip = (
                f"{batch_folder}\n{total} image{'s' if total != 1 else ''}"
            )
            entries.append(
                GalleryEntry(
                    path=preview,
                    display=label,
                    is_batch=True,
                    batch_folder=batch_folder,
                    total=total,
                    tooltip=tooltip,
                )
            )
        return entries

    def _build_loose_entries(self, folder_path: str) -> List[GalleryEntry]:
        """Create gallery entries for loose images in ``folder_path``."""
        entries: List[GalleryEntry] = []
        for image_path in self.find_date_loose_images(folder_path):
            name = os.path.basename(image_path)
            entries.append(
                GalleryEntry(
                    path=image_path,
                    display=name,
                    is_batch=False,
                    tooltip=image_path,
                )
            )
        return entries

    def _build_image_entries(self, batch_folder: str) -> List[GalleryEntry]:
        """Create gallery entries for images inside a batch folder."""
        entries: List[GalleryEntry] = []
        for image_path in self.find_batch_images(batch_folder):
            name = os.path.basename(image_path)
            entries.append(
                GalleryEntry(
                    path=image_path,
                    display=name,
                    is_batch=False,
                    tooltip=image_path,
                )
            )
        return entries


def natural_sort_key(value: str):
    """Helper for natural sorting (e.g. batch_2 before batch_10)."""

    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split(r"(\d+)", value)
    ]
