from typing import Optional
import io
from PIL import Image

# Simple in-memory buffer pool (very small) to reduce allocations for frequent conversions
_PNG_BUFFER_POOL: list[io.BytesIO] = []
_PNG_BUFFER_POOL_MAX = 4


def _acquire_buffer() -> io.BytesIO:
    try:
        buf = _PNG_BUFFER_POOL.pop()
        buf.seek(0)
        buf.truncate(0)
        return buf
    except IndexError:
        return io.BytesIO()


def _release_buffer(buf: io.BytesIO):
    if len(_PNG_BUFFER_POOL) < _PNG_BUFFER_POOL_MAX:
        _PNG_BUFFER_POOL.append(buf)


def convert_image_to_binary(image: Image) -> Optional[bytes]:
    if image is None:
        raise ValueError("Image is None")
    if not isinstance(image, Image.Image):
        print(
            f"convert_image_to_binary: Refusing to convert non-image type: {type(image)}"
        )
        return None

    buf = _acquire_buffer()
    try:
        # Use minimal compression for speed; Pillow interprets compression level via pnginfo/parameters
        # optimize=False and no additional parameters keeps it fast.
        image.save(buf, format="PNG", optimize=False)
        data = buf.getvalue()
    except AttributeError as e:
        print(f"Something went wrong with image conversion to binary: {e}")
        data = None
    finally:
        _release_buffer(buf)
    return data
