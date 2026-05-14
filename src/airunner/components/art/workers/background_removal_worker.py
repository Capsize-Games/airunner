import logging
from typing import Any

from airunner.components.application.workers.worker import Worker
from airunner.components.model_management.model_resource_manager import (
    ModelResourceManager,
)
from airunner.enums import ModelStatus, ModelType, SignalCode
from airunner.utils.image.convert_binary_to_image import (
    convert_binary_to_image,
)


class BackgroundRemovalWorker(Worker):
    """Remove backgrounds from canvas images with RMBG-2.0."""

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

    def handle_message(self, message: Any) -> None:
        data = message.get("data", {}) if isinstance(message, dict) else {}
        action = message.get("action") if isinstance(message, dict) else None
        if action == "unload":
            self._unload_model()
            return
        if action != "remove_background":
            return
        self._remove_background(data)

    def _unload_model(self) -> None:
        model_id = self.model_manager.model_id
        self.model_manager.unload()
        ModelResourceManager().cleanup_model(model_id, "rmbg")
        self.emit_signal(
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.RMBG, "status": ModelStatus.UNLOADED},
        )

    def _mark_model_busy(self) -> None:
        model_id = self.model_manager.model_id
        ModelResourceManager().model_busy(model_id, "rmbg")
        self.emit_signal(
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.RMBG, "status": ModelStatus.LOADING},
        )

    def _mark_model_ready(self) -> None:
        model_id = self.model_manager.model_id
        ModelResourceManager().model_ready(model_id, "rmbg")
        self.emit_signal(
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.RMBG, "status": ModelStatus.READY},
        )

    def _mark_model_failed(self) -> None:
        model_id = self.model_manager.model_id
        resource_manager = ModelResourceManager()
        if self.model_manager.is_loaded:
            resource_manager.model_ready(model_id, "rmbg")
        else:
            resource_manager.cleanup_model(model_id, "rmbg")
        self.emit_signal(
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.RMBG, "status": ModelStatus.FAILED},
        )

    def _remove_background(self, data: dict[str, Any]) -> None:
        layer_id = data.get("layer_id")
        image_binary = data.get("image")
        if image_binary is None:
            return

        logger = logging.getLogger(__name__)
        logger.info(
            "BackgroundRemovalWorker request received "
            "(layer_id=%s, bytes=%s)",
            layer_id,
            len(image_binary) if hasattr(image_binary, "__len__") else None,
        )

        missing = self.model_manager.missing_files()
        if missing:
            self._request_model_download(layer_id, image_binary, missing)
            return

        try:
            image = convert_binary_to_image(image_binary)
            if image is None:
                logger.warning("BackgroundRemovalWorker failed to decode image")
                return

            self._mark_model_busy()
            output_binary = self.model_manager.remove_background_to_png_bytes(
                image
            )
            logger.info(
                "BackgroundRemovalWorker inference complete "
                "(out_bytes=%s, device=%s)",
                len(output_binary)
                if hasattr(output_binary, "__len__")
                else None,
                getattr(self.model_manager, "_device", None),
            )
            self._persist_output(layer_id, output_binary)
            self._refresh_canvas()
            self._mark_model_ready()
        except Exception as exc:
            self._mark_model_failed()
            try:
                self.api.application_error(message=str(exc))
            except Exception:
                pass

    def _request_model_download(
        self,
        layer_id: int | None,
        image_binary: bytes,
        missing: list[str],
    ) -> None:
        logger = logging.getLogger(__name__)
        logger.info(
            "BackgroundRemovalWorker RMBG files missing (%s); requesting "
            "download",
            ",".join(missing),
        )
        model_path = self.model_manager.spec.local_dir
        repo_id = self.model_manager.spec.repo_id

        def retry() -> None:
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

    def _persist_output(
        self,
        layer_id: int | None,
        image_binary: bytes,
    ) -> None:
        if layer_id is None:
            self.update_drawing_pad_settings(image=image_binary)
            return

        self.update_drawing_pad_settings(
            layer_id=layer_id,
            image=image_binary,
        )

    def _refresh_canvas(self) -> None:
        try:
            self.emit_signal(SignalCode.LAYERS_SHOW_SIGNAL, {})
        except Exception:
            pass

        try:
            self.api.art.canvas.image_updated()
            self.api.art.canvas.do_draw(True)
        except Exception:
            pass