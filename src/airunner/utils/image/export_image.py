from typing import List, Dict, AnyStr, Any
from PIL import Image, PngImagePlugin
import os


def export_image(
    image: Image,
    file_path: AnyStr,
    metadata: Dict = None
):
    base, ext = os.path.splitext(file_path)
    current_path = file_path
    counter = 1
    while os.path.exists(current_path):
        current_path = f"{base}_{counter}{ext}"
        counter += 1

    if metadata and ext.lower() == '.png':
        png_info = PngImagePlugin.PngInfo()
        for key, value in metadata.items():
            png_info.add_text(key, str(value))
        image.save(current_path, pnginfo=png_info)
    else:
        image.save(current_path)


def export_images(
    images: List[Any],
    file_path: AnyStr,
    metadata: List[Dict] = None
) -> None:
    base, ext = os.path.splitext(file_path)
    for i, image in enumerate(images):
        current_path = file_path
        counter = 1
        while os.path.exists(current_path):
            current_path = f"{base}_{counter}{ext}"
            counter += 1
        export_image(image, current_path, metadata[i] if metadata else None)
