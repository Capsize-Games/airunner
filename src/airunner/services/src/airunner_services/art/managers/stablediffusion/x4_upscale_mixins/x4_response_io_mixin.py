"""
Response IO mixin for X4UpscaleManager.

Handles saving and queueing of generated images so these responsibilities
are kept separate from signal/emission logic.
"""

import os
from datetime import datetime
from typing import Dict, List, Optional

from PIL import Image


class X4ResponseIOMixin:
    PREVIEW_FILENAME = "preview_current.png"

    def _queue_export(self, images: List[Image.Image], data: Dict):
        """Queue images for export with metadata."""
        try:
            self.image_export_worker.add_to_queue(
                {"images": images, "data": data}
            )
        except Exception as exc:
            self.logger.warning(
                "Failed to queue upscaled image export: %s", exc
            )

    def _save_preview_image(self, image: Image.Image):
        try:
            os.makedirs(self.preview_dir, exist_ok=True)
            # Handle alpha channel
            try:
                if "A" in image.getbands():
                    bg = Image.new("RGB", image.size, (255, 255, 255))
                    bg.paste(image, mask=image.split()[-1])
                    bg.save(self.preview_path)
                else:
                    image.convert("RGB").save(self.preview_path)
            except Exception:
                image.convert("RGB").save(self.preview_path)
        except Exception:
            pass

    def _save_result_to_disk(self, image: Image.Image) -> Optional[str]:
        try:
            os.makedirs(self.preview_dir, exist_ok=True)
            filename = datetime.now().strftime("upscaled_%Y%m%d_%H%M%S.png")
            path = os.path.join(self.preview_dir, filename)

            try:
                if "A" in image.getbands():
                    bg = Image.new("RGB", image.size, (255, 255, 255))
                    bg.paste(image, mask=image.split()[-1])
                    bg.save(path)
                else:
                    image.convert("RGB").save(path)
            except Exception:
                image.convert("RGB").save(path)

            return path
        except Exception as exc:
            self.logger.warning("Unable to save upscaled image: %s", exc)
            return None
