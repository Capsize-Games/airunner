from PIL import Image
from PySide6.QtGui import QPixmap, QImage


def image_to_pixmap(image: Image, size=None):
    """
    Converts a PIL image to a QPixmap.
    :param size:
    :param image:
    :return:
    """
    image_width = image.width
    image_height = image.height

    # scaale the image to the new width and height preserving the aspect ratio
    if size is not None:
        if image_width > 0 and image_height > 0:
            aspect_ratio = image_width / image_height
            if image_width > image_height:
                image_width = size
                image_height = int(image_width / aspect_ratio)
            else:
                image_height = size
                image_width = int(image_height * aspect_ratio)
    image_copy = image.copy()
    image_copy = image_copy.resize((image_width, image_height))
    new_image = Image.new("RGB", (size, size))
    new_image.paste(image_copy, (int((size - image_width) / 2), int((size - image_height) / 2)))
    return QPixmap.fromImage(
        QImage(
            new_image.tobytes("raw", "RGB"), size, size, QImage.Format.Format_RGB888
        )
    )


