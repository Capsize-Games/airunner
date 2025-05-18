import os
from PySide6.QtWidgets import QSpacerItem, QSizePolicy
from PySide6.QtGui import QPixmap, Qt
from PySide6.QtWidgets import QWidget
from typing import Dict
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.canvas.templates.batch_container_ui import (
    Ui_batch_conatiner,
)
from airunner.gui.widgets.canvas.templates.image_layer_item_ui import (
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
        super().__init__(*args, **kwargs)

    def _add_image_layer_item(self, image_path: str, total: int, layout):
        pixmap = QPixmap(image_path)
        pixmap = pixmap.scaled(
            256,
            256,
            aspectMode=Qt.KeepAspectRatio,
            mode=Qt.SmoothTransformation,
        )
        image_layer_item = ImageLayerItemWidget()
        image_layer_item.ui.image.setPixmap(pixmap)
        if total is not None:
            image_layer_item.ui.total_images.setText(f"{total} in batch")
            image_layer_item.ui.total_images.setVisible(True)
        else:
            # Hide the label for individual images (not part of a batch)
            image_layer_item.ui.total_images.setVisible(False)
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
            self.populate_today_batches()

    def find_today_loose_images(self) -> list:
        """Return a list of loose images (not in batches) for today."""
        today_folder = get_today_folder(self.path_settings.image_path)
        loose_images = sorted(
            [
                os.path.join(today_folder, f)
                for f in os.listdir(today_folder)
                if os.path.isfile(os.path.join(today_folder, f))
            ]
        )
        return loose_images

    def find_today_batches(self) -> list:
        """Return a list of batch folders and their images for today."""
        today_folder = get_today_folder(self.path_settings.image_path)
        batch_folders = sorted(
            [
                os.path.join(today_folder, d)
                for d in os.listdir(today_folder)
                if os.path.isdir(os.path.join(today_folder, d))
                and d.startswith("batch_")
            ]
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

    def populate_today_batches(self):
        """Find today's batches and loose images and add them to the layout as image_layer_item widgets."""
        # Get batches
        batches = self.find_today_batches()
        # Get loose images
        loose_images = self.find_today_loose_images()

        container = self.ui.scrollArea.widget()
        layout = container.layout()
        self._clear_layout(layout)

        # Add batch images
        for batch in batches:
            images = batch["images"]
            if not images:
                continue
            self._add_image_layer_item(images[0], len(images), layout)

        # Add loose images
        for image_path in loose_images:
            self._add_image_layer_item(image_path, None, layout)

        spacer = QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        layout.addItem(spacer)

    def update_batch_images(self, data: Dict):
        images = data.get("images", [])
        if not images:
            return
        container = self.ui.scrollArea.widget()
        layout = container.layout()
        # Remove any bottom spacer before adding a new item
        if layout.count() > 0:
            last_item = layout.itemAt(layout.count() - 1)
            if isinstance(last_item, QSpacerItem):
                layout.takeAt(layout.count() - 1)
        self._add_image_layer_item(images[0], len(images), layout)
        spacer = QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        layout.addItem(spacer)


class ImageLayerItemWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = Ui_image_layer_item()
        self.ui.setupUi(self)
        self.ui.image.setFixedSize(256, 256)
