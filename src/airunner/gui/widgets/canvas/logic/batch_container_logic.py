"""
Business logic for BatchContainer: file/folder discovery, sorting, and navigation logic.
Decoupled from PySide6 GUI code for testability.
"""

import os
import datetime
import re
from typing import List, Dict
from airunner.utils.image.export_image import get_today_folder


def natural_sort_key(s):
    return [
        int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", s)
    ]


class BatchContainerLogic:
    def __init__(self, path_settings):
        self.path_settings = path_settings

    def get_date_folders(self) -> List[str]:
        base_path = self.path_settings.image_path
        if not os.path.exists(base_path):
            return []
        folders = [
            d
            for d in os.listdir(base_path)
            if os.path.isdir(os.path.join(base_path, d)) and len(d) == 8 and d.isdigit()
        ]
        folders.sort(reverse=True)
        return folders

    def display_format(self, folder: str) -> str:
        try:
            if len(folder) == 8 and folder.isdigit():
                year, month, day = folder[0:4], folder[4:6], folder[6:8]
                return f"{year}-{month}-{day}"
            else:
                return folder
        except Exception:
            return folder

    def get_date_folder_path(self, display_date: str) -> str:
        try:
            date_parts = display_date.split("-")
            folder_name = f"{date_parts[0]}{date_parts[1]}{date_parts[2]}"
            return os.path.join(self.path_settings.image_path, folder_name)
        except Exception:
            return get_today_folder(self.path_settings.image_path)

    def find_loose_images(self, folder_path: str) -> List[str]:
        if not os.path.exists(folder_path):
            return []
        return sorted(
            [
                os.path.join(folder_path, f)
                for f in os.listdir(folder_path)
                if os.path.isfile(os.path.join(folder_path, f))
            ]
        )

    def find_batches(self, folder_path: str) -> List[Dict]:
        if not os.path.exists(folder_path):
            return []
        batch_folders = sorted(
            [
                os.path.join(folder_path, d)
                for d in os.listdir(folder_path)
                if os.path.isdir(os.path.join(folder_path, d))
                and d.startswith("batch_")
            ],
            key=lambda x: natural_sort_key(os.path.basename(x)),
        )
        batches = []
        for batch in batch_folders:
            images = sorted(
                [
                    os.path.join(batch, f)
                    for f in os.listdir(batch)
                    if os.path.isfile(os.path.join(batch, f))
                ]
            )
            batches.append({"batch_folder": batch, "images": images})
        return batches

    def find_batch_images(self, batch_folder: str) -> List[str]:
        if not os.path.exists(batch_folder):
            return []
        return sorted(
            [
                os.path.join(batch_folder, f)
                for f in os.listdir(batch_folder)
                if os.path.isfile(os.path.join(batch_folder, f))
            ]
        )
