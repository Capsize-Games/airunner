import base64
import io
from PIL import Image
from airunner.handlers.logger import Logger


def convert_image_to_base64(image: Image) -> str:
    if image is None:
        raise ValueError("Image is None")
    img_byte_arr = io.BytesIO()
    try:
        image.save(img_byte_arr, format='PNG')
    except AttributeError as e:
        logger = Logger(prefix="convert_image_to_base64")
        logger.error(f"Something went wrong with image conversion to base64: {e}")
        return None
    img_byte_arr = img_byte_arr.getvalue()
    image_base64 = base64.encodebytes(img_byte_arr).decode('ascii')
    return image_base64
