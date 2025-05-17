from PIL.ImageQt import ImageQt
from PySide6.QtWidgets import QSpacerItem, QSizePolicy
from PySide6.QtGui import QImage
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


class BatchContainer(BaseWidget):
    widget_class_ = Ui_batch_conatiner

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.SD_UPDATE_BATCH_IMAGES_SIGNAL: self.update_batch_images,
        }
        super().__init__(*args, **kwargs)

    def update_batch_images(self, data: Dict):
        images = data.get("images", [])
        if not images:
            return
        # Always show only the first image in the batch for this call
        image = images[0]
        if isinstance(image, str):
            pixmap = QPixmap(image)
        else:
            qimage = ImageQt(image)
            pixmap = QPixmap.fromImage(QImage(qimage))
        pixmap = pixmap.scaled(
            256,
            256,
            aspectMode=Qt.KeepAspectRatio,
            mode=Qt.SmoothTransformation,
        )
        image_layer_item = ImageLayerItemWidget()
        image_layer_item.ui.image.setPixmap(pixmap)
        image_layer_item.ui.total_images.setText(f"{len(images)} in batch")
        container = self.ui.scrollArea.widget()
        layout = container.layout()
        # Remove any bottom spacer before adding a new item
        if layout.count() > 0:
            last_item = layout.itemAt(layout.count() - 1)
            if isinstance(last_item, QSpacerItem):
                layout.takeAt(layout.count() - 1)
        layout.addWidget(image_layer_item)
        # Add a single vertical spacer at the bottom
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
