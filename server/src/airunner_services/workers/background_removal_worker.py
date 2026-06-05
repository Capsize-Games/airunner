"""Service-owned RMBG background-removal worker."""

from __future__ import annotations

import logging
from typing import Any

from airunner_services.contract_enums import ModelStatus, ModelType, SignalCode
from airunner_services.database.models.drawingpad_settings import (
    DrawingPadSettings,
)
from airunner_services.model_management import ModelResourceManager
from airunner_services.utils.application.enum_resolver import (
    signal_code_member,
)
from airunner_services.utils.image.convert_binary_to_image import (
    convert_binary_to_image,
)
from airunner_services.workers.worker import Worker


class BackgroundRemovalWorkerSignalCode:
    """Compatibility signal names used by the RMBG worker."""

    LAYERS_SHOW_SIGNAL = "show_layers_signal"
    START_HUGGINGFACE_DOWNLOAD = "start_huggingface_download"
    MODEL_STATUS_CHANGED_SIGNAL = signal_code_member(
        "MODEL_STATUS_CHANGED_SIGNAL",
        SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
    )


class BackgroundRemovalWorker(Worker):
    """Remove backgrounds from canvas images with RMBG-2.0."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialize the background-removal worker."""
        super().__init__(*args, **kwargs)
        self._model_manager = None

    @property
    def model_manager(self):
        """Return the shared RMBG manager instance."""
        if self._model_manager is None:
            from airunner_services.art.managers.rmbg import RMBGModelManager

            self._model_manager = RMBGModelManager()
        return self._model_manager

    def handle_message(self, message: Any) -> None:
        """Handle one worker message."""
        data = message.get("data", {}) if isinstance(message, dict) else {}
        action = message.get("action") if isinstance(message, dict) else None
        if action == "unload":
            self._unload_model()
            return
        if action != "remove_background":
            return
        self._remove_background(data)

    def _daemon_client(self):
        """Return the GUI daemon client when one is active."""
        api_ref = self.refresh_api_reference() or getattr(self, "api", None)
        if api_ref is None or getattr(api_ref, "headless", False):
            return None
        return getattr(api_ref, "daemon_client", None)

    def _unload_model(self) -> None:
        """Release RMBG resources and publish unloaded status."""
        client = self._daemon_client()
        if client is not None:
            try:
                client.unload_art_component("rmbg", auto_start=False)
            except Exception:
                pass

        model_id = self.model_manager.model_id
        self.model_manager.unload()
        ModelResourceManager().cleanup_model(model_id, "rmbg")
        self.emit_signal(
            BackgroundRemovalWorkerSignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.RMBG, "status": ModelStatus.UNLOADED},
        )

    def _mark_model_busy(self) -> None:
        """Publish busy state for RMBG work."""
        model_id = self.model_manager.model_id
        ModelResourceManager().model_busy(model_id, "rmbg")
        self.emit_signal(
            BackgroundRemovalWorkerSignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.RMBG, "status": ModelStatus.LOADING},
        )

    def _mark_model_ready(self) -> None:
        """Publish ready state for RMBG work."""
        model_id = self.model_manager.model_id
        ModelResourceManager().model_ready(model_id, "rmbg")
        self.emit_signal(
            BackgroundRemovalWorkerSignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.RMBG, "status": ModelStatus.READY},
        )

    def _mark_model_failed(self) -> None:
        """Publish failed state for RMBG work."""
        model_id = self.model_manager.model_id
        resource_manager = ModelResourceManager()
        if self.model_manager.is_loaded:
            resource_manager.model_ready(model_id, "rmbg")
        else:
            resource_manager.cleanup_model(model_id, "rmbg")
        self.emit_signal(
            BackgroundRemovalWorkerSignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.RMBG, "status": ModelStatus.FAILED},
        )

    def _remove_background(self, data: dict[str, Any]) -> None:
        """Run one background-removal request."""
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
            self._mark_model_busy()
            client = self._daemon_client()
            if client is not None:
                output_binary = client.remove_background(image_binary)
            else:
                image = convert_binary_to_image(image_binary)
                if image is None:
                    logger.warning(
                        "BackgroundRemovalWorker failed to decode image"
                    )
                    self._mark_model_failed()
                    return
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

    def _request_model_download(
        self,
        layer_id: int | None,
        image_binary: bytes,
        missing: list[str],
    ) -> None:
        """Queue one Hugging Face download for missing RMBG files."""
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
            BackgroundRemovalWorkerSignalCode.START_HUGGINGFACE_DOWNLOAD,
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
        """Persist the background-removed PNG into drawing-pad settings."""
        if layer_id is None:
            self.update_drawing_pad_settings(image=image_binary)
            return
        self.update_drawing_pad_settings(
            layer_id=layer_id,
            image=image_binary,
        )

    def update_drawing_pad_settings(
        self,
        layer_id: int | None = None,
        **settings_dict: Any,
    ) -> None:
        """Persist one drawing-pad settings update without GUI mixins."""
        if layer_id is None:
            settings = DrawingPadSettings.objects.first()
            if settings is None:
                settings = DrawingPadSettings.objects.create()
        else:
            settings = DrawingPadSettings.objects.filter_by_first(
                layer_id=layer_id,
            )
            if settings is None:
                settings = DrawingPadSettings.objects.create(layer_id=layer_id)
        if settings is None:
            return
        record_id = getattr(settings, "id", None)
        if record_id is None:
            return
        DrawingPadSettings.objects.update(record_id, **settings_dict)

    def _refresh_canvas(self) -> None:
        """Notify canvas listeners about fresh RMBG output."""
        try:
            self.emit_signal(
                BackgroundRemovalWorkerSignalCode.LAYERS_SHOW_SIGNAL,
                {},
            )
        except Exception:
            pass



__all__ = ["BackgroundRemovalWorker"]