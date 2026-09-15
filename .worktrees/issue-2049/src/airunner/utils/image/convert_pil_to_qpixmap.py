from PIL.ImageQt import QPixmap

from airunner.utils.image.convert_pil_to_qimage import pil_to_qimage


def convert_pil_to_qpixmap(image):
    qimage = pil_to_qimage(image)
    pixmap = QPixmap.fromImage(qimage)
    return pixmap
