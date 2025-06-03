from typing import List, Dict, AnyStr, Any
from PIL import Image, PngImagePlugin
import os
import datetime
import glob


def get_today_folder(base_path: str) -> str:
    """Return the path to today's folder in YYYYMMDD format, creating it if needed."""
    today = datetime.datetime.now().strftime("%Y%m%d")
    today_folder = os.path.join(base_path, today)
    os.makedirs(today_folder, exist_ok=True)
    return today_folder


def get_next_sequence_folder(parent_folder: str, prefix: str) -> str:
    """Return the next available sequential folder with the given prefix (e.g., batch_1, batch_2)."""
    existing = [
        d
        for d in os.listdir(parent_folder)
        if os.path.isdir(os.path.join(parent_folder, d))
        and d.startswith(prefix)
    ]
    nums = [
        int(d[len(prefix) :]) for d in existing if d[len(prefix) :].isdigit()
    ]
    next_num = max(nums, default=0) + 1
    folder = os.path.join(parent_folder, f"{prefix}{next_num}")
    os.makedirs(folder, exist_ok=True)
    return folder


def get_next_image_sequence(folder: str, ext: str) -> int:
    """Return the next available image sequence number in the folder."""
    files = glob.glob(os.path.join(folder, f"*{ext}"))
    nums = []
    for f in files:
        base = os.path.splitext(os.path.basename(f))[0]
        try:
            nums.append(int(base))
        except ValueError:
            pass
    return max(nums, default=0) + 1


def export_image(image: Image, file_path: AnyStr, metadata: Dict = None):
    # file_path is now the final destination, do not add a date folder here
    base, ext = os.path.splitext(file_path)
    current_path = file_path
    if metadata and ext.lower() == ".png":
        png_info = PngImagePlugin.PngInfo()
        for key, value in metadata.items():
            png_info.add_text(key, str(value))
        image.save(current_path, pnginfo=png_info)
    else:
        image.save(current_path)


def export_images(
    images: List[Any], file_path: AnyStr, metadata: List[Dict] = None
) -> None:
    base, ext = os.path.splitext(file_path)
    today_folder = get_today_folder(os.path.dirname(base))
    if len(images) > 1:
        batch_folder = get_next_sequence_folder(today_folder, "batch_")
        for i, image in enumerate(images):
            seq = i + 1
            current_path = os.path.join(batch_folder, f"{seq}{ext}")
            if metadata:
                export_image(image, current_path, metadata[i])
            else:
                export_image(image, current_path)
    else:
        # For single images, store in the date folder
        seq = get_next_image_sequence(today_folder, ext)
        current_path = os.path.join(today_folder, f"{seq}{ext}")
        export_image(
            images[0], current_path, metadata[0] if metadata else None
        )
