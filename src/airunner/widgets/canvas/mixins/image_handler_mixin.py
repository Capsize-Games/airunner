from PIL import ImageFilter, Image

from airunner.widgets.canvas.draggables.draggable_pixmap import DraggablePixmap


class ImageHandlerMixin:
    def __init__(self, image=None):
        self._image = image
        self.image_backup = None
        self.previewing_filter = False

    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, value):
        self._image = value

    def load_image(self, image_path: str) -> Image:
        image = Image.open(image_path)
        return image

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
