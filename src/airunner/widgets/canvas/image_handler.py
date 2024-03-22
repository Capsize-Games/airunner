from PIL import ImageFilter, Image

from airunner.mediator_mixin import MediatorMixin
from airunner.widgets.canvas.draggables.draggable_pixmap import DraggablePixmap
from airunner.windows.main.settings_mixin import SettingsMixin


class ImageHandler(
    SettingsMixin,
    MediatorMixin
):
    def __init__(self, image=None):
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        self.image = image
        self.image_backup = None
        self.previewing_filter = False

    def load_image(self, image_path: str) -> Image:
        image = Image.open(image_path)
        return image

    def save_image(
        self,
        image_path: str,
        image: Image = None,
        scene_items: list = None
    ):
        if image is None and scene_items is not None:
            for item in scene_items:
                if isinstance(item, DraggablePixmap):
                    image = item.pixmap.toImage()
                    image.save(image_path)
        else:
            image.save(image_path)

    def rotate_image(
        self,
        angle: float,
        image: Image = None
    ):
        return image.transpose(angle) if image else image

    def apply_filter(self, _filter_object: ImageFilter.Filter):
        self.previewing_filter = False
        self.image_backup = None

    def cancel_filter(self) -> Image:
        image = None
        if self.image_backup:
            image = self.image_backup.copy()
            self.image_backup = None
        self.previewing_filter = False
        return image

    def preview_filter(
        self,
        image: Image,
        filter_object: ImageFilter.Filter
    ):
        if not image:
            return
        if not self.previewing_filter:
            self.image_backup = image.copy()
            self.previewing_filter = True
        else:
            image = self.image_backup.copy()
        filtered_image = filter_object.filter(image)
        return filtered_image
