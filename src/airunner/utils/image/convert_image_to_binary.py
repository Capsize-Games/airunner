from typing import Optional
import io
from PIL import Image


def convert_image_to_binary(image: Image) -> Optional[bytes]:
    if image is None:
        raise ValueError("Image is None")
    img_byte_arr = io.BytesIO()
    try:
        image.save(img_byte_arr, format='PNG')
    except AttributeError as e:
        print(f"Something went wrong with image conversion to binary: {e}")
        return None
    img_byte_arr = img_byte_arr.getvalue()
    return img_byte_arr
