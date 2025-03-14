import io

import PIL
from PIL import Image


def convert_binary_to_image(binary_data: bytes) -> Image:
    if binary_data is None:
        return None
    try:
        bytes_ = io.BytesIO(binary_data)
        return Image.open(bytes_)
    except PIL.UnidentifiedImageError as e:
        print(f"Something went wrong with binary data conversion to image: {e}")
        return None
    except TypeError as e:
        print(f"Something went wrong with binary data conversion to image: {e}")
        return None
