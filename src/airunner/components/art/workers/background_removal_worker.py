import os
from typing import Any, Dict, Optional

import logging

from PIL import Image

from airunner.components.application.workers.worker import Worker
from airunner.enums import SignalCode
from airunner.utils.image.convert_binary_to_image import convert_binary_to_image


class BackgroundRemovalWorker(Worker):
    """Worker to remove background from the current canvas image using RMBG-2.0."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._model_manager = None

    @property
    def model_manager(self):
        if self._model_manager is None:
            from airunner.components.art.managers.rmbg.rmbg_model_manager import (
                RMBGModelManager,
            )

            self._model_manager = RMBGModelManager()
        return self._model_manager

    def handle_message(self, message: Any):
        data: Dict = message.get("data", {}) if isinstance(message, dict) else {}
        action = message.get("action") if isinstance(message, dict) else None

        if action != "remove_background":
            return

        layer_id = data.get("layer_id")
        image_binary = data.get("image")

        if image_binary is None:
            return

        logger = logging.getLogger(__name__)
        logger.info(
            "BackgroundRemovalWorker: request received (layer_id=%s, bytes=%s)",
            layer_id,
            len(image_binary) if hasattr(image_binary, "__len__") else None,
        )

        # Ensure model exists on disk; if not, trigger download via WorkerManager.
        missing = self.model_manager.missing_files()
        if missing:
            logger.info(
                "BackgroundRemovalWorker: RMBG files missing (%s); requesting download",
                ",".join(missing),
            )
            model_path = self.model_manager.spec.local_dir
            repo_id = self.model_manager.spec.repo_id

            # Defer the actual work until after the download completes.
            def retry():
                self.add_to_queue(
                    {
                        "action": "remove_background",
                        "data": {
                            "layer_id": layer_id,
                            "image": image_binary,
                        },
                    }
                )

            self.emit_signal(
                SignalCode.START_HUGGINGFACE_DOWNLOAD,
                {
                    "repo_id": repo_id,
                    "model_path": model_path,
                    "model_type": "rmbg",
                    "callback": retry,
                },
            )
            return

        try:
            img = convert_binary_to_image(image_binary)
            if img is None:
                logger.warning(
                    "BackgroundRemovalWorker: failed to decode input image bytes"
                )
                return

            out_bytes = self.model_manager.remove_background_to_png_bytes(img)
            logger.info(
                "BackgroundRemovalWorker: inference complete (out_bytes=%s, device=%s)",
                len(out_bytes) if hasattr(out_bytes, "__len__") else None,
                getattr(self.model_manager, "_device", None),
            )

            # Persist into the current layer's drawing pad settings.
            if layer_id is not None:
                self.update_drawing_pad_settings(layer_id=layer_id, image=out_bytes)
            else:
                # Fallback: update current selected layer via mixin resolution
                self.update_drawing_pad_settings(image=out_bytes)

            # Force the canvas layer system to reload image bytes from DB.
            # A plain redraw can still show the old cached QImage.
            try:
                self.emit_signal(SignalCode.LAYERS_SHOW_SIGNAL, {})
            except Exception:
                pass

            # Notify canvas to refresh.
            try:
                self.api.art.canvas.image_updated()
                self.api.art.canvas.do_draw(True)
            except Exception:
                pass

        except Exception as exc:
            # Surface error to user via application error pipeline.
            try:
                self.api.application_error(message=str(exc))
            except Exception:
                pass
