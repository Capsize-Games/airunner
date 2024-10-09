import base64
import io
import PIL
from PIL import Image


def convert_base64_to_image(base_64_image) -> Image:
    if base_64_image is None:
        return base_64_image
    try:
        decoded = base64.b64decode(base_64_image)
        bytes_ = io.BytesIO(decoded)
        return Image.open(bytes_)
    except PIL.UnidentifiedImageError as e:
        return None
