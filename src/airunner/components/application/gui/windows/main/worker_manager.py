"""
Worker Manager for handling various application workers.

This class uses inline imports to avoid slow startup times. Do not move
imports to the top of the file.
"""

import threading
from typing import Dict
from airunner.components.application.workers.worker import Worker
from airunner.enums import SignalCode
from airunner.utils.application.create_worker import create_worker
from airunner.utils.application.log_hygiene import summarize_mapping_keys


_OPTIONAL_LOAD_REQUEST_TIMEOUT_SECONDS = 5.0
_OPTIONAL_UNLOAD_REQUEST_TIMEOUT_SECONDS = 2.0
_OPTIONAL_UNLOAD_WAIT_TIMEOUT_SECONDS = 5.0
_TTS_LOAD_WAIT_TIMEOUT_SECONDS = 180.0
_STREAM_TTS_WORKER_SLEEP_MS = 1


class WorkerManager(Worker):
    def __init__(self, *args, signal_api_adapter=None, **kwargs):
        self.signal_handlers = {
            SignalCode.DO_GENERATE_SIGNAL: self.on_do_generate_signal,
            SignalCode.REMOVE_BACKGROUND: self.on_remove_background_signal,
            # TTS stream-to-vocalizer signal kept for playback routing
            # TTS enable now via daemon runtime control
            # STT load now via daemon runtime control
            # STT capture start kept for microphone control
            SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE: self.on_huggingface_download_complete,
            # RMBG unload now handled by daemon (future API)
            SignalCode.INTERRUPT_PROCESS_SIGNAL: self.on_interrupt_process_signal,
            SignalCode.QUIT_APPLICATION: self.on_quit_application_signal,
            SignalCode.GENERATE_MASK: self.on_generate_mask_signal,
            SignalCode.AUDIO_CAPTURE_WORKER_RESPONSE_SIGNAL: self.on_stt_process_audio_signal,
            SignalCode.STT_STOP_CAPTURE_SIGNAL: self.on_stt_stop_capture_signal,
            SignalCode.RECORDING_DEVICE_CHANGED: self.on_recording_device_changed_signal,
            SignalCode.STT_UNLOAD_SIGNAL: self.on_stt_unload_signal,
            # TTS unblock now via daemon
            # TTS disable now via daemon
            SignalCode.LLM_THINKING_SIGNAL: self.on_llm_thinking_signal,
            SignalCode.LLM_TEXT_STREAMED_SIGNAL: self.on_llm_text_streamed_signal,
            # TTS model change now via daemon
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: self.on_application_settings_changed_signal,
            # TTS queue now via daemon
            SignalCode.PLAYBACK_DEVICE_CHANGED: self.on_playback_device_changed_signal,
            SignalCode.IMAGE_EXPORTED: self.on_image_exported_signal,
            SignalCode.START_HUGGINGFACE_DOWNLOAD: self.on_start_huggingface_download_signal,
            SignalCode.START_OPENVOICE_BATCH_DOWNLOAD: self.on_start_openvoice_batch_download_signal,
            SignalCode.APPLICATION_MAIN_WINDOW_LOADED_SIGNAL: self.on_application_main_window_loaded_signal,
        }
        super().__init__()
        self._mask_generator_worker = None
        # safety_checker_worker removed; daemon handles via future API
        self._pending_generation_request = None
        self._download_dialog = (
            None  # Store dialog reference to prevent garbage collection
        )
        self._stt_audio_capture_worker = None
        # STT transcription now via daemon; local processor worker removed
        # TTS synthesis now via daemon; local generator worker removed
        self._llm_generate_worker = None
        self._tts_vocalizer_worker = None
        self._document_worker = None
        self._huggingface_download_worker = None
        self._image_export_worker = None
        self._model_scanner_worker = None
        # background_removal_worker removed; daemon handles via future API
        if self.logger:
            self.logger.debug(
                f"WorkerManager initialized. Mediator ID: {id(self.mediator)}"
            )

        self.model_scanner_worker.add_to_queue("scan_for_models")

        # Merge API adapter handlers with precedence over local handlers.
        # When the API backend feature flag is enabled, execution triggers
        # go through the signal-to-API adapter instead of local workers.
        self._signal_api_adapter = signal_api_adapter
        if self._signal_api_adapter is not None:
            adapter_handlers = self._signal_api_adapter.signal_handlers
            self.signal_handlers.update(adapter_handlers)
            if self.logger:
                self.logger.debug(
                    "Merged %d API adapter handlers into WorkerManager",
                    len(adapter_handlers),
                )

    # background_removal_worker removed; daemon handles via future API

    def on_remove_background_signal(self, _data: Dict):
        """Queue background removal for the selected canvas layer."""
        from PySide6.QtWidgets import QMessageBox

        layer_id = self._get_current_selected_layer_id()
        if layer_id is None:
            try:
                from airunner_model.models.canvas_layer import (
                    CanvasLayer,
                )

                layers = CanvasLayer.objects.order_by("order").all() or []
                if layers:
                    layer_id = getattr(layers[0], "id", None)
            except Exception:
                layer_id = None

        image_binary = None
        try:
            from airunner_model.models.drawingpad_settings import (
                DrawingPadSettings,
            )

            if layer_id is not None:
                drawing_pad = DrawingPadSettings.objects.filter_by_first(
                    layer_id=layer_id
                )
                image_binary = getattr(drawing_pad, "image", None)
            else:
                image_binary = getattr(
                    self.drawing_pad_settings,
                    "image",
                    None,
                )
        except Exception:
            image_binary = None

        if not image_binary:
            main_window = self._get_main_window()
            if main_window is not None:
                QMessageBox.information(
                    main_window,
                    "No Image",
                    "Please import or generate an image first.",
                )
            return

        self.logger.info("Background removal signal received; daemon migration pending")

    def on_unload_rmbg_signal(self, data: Dict):
        """Background removal unload handled by daemon (future API)."""
        pass

    def handle_message(self, message: Dict):
        if self.logger:
            self.logger.debug(
                f"WorkerManager::handle_message CALLED with request_type={message.get('request_type')}"
            )
        data = message.get("data", {})
        request_type = message.get("request_type")
        try:
            if request_type == "tts_generate":
                if self.tts_vocalizer_worker is not None:
                    self.tts_vocalizer_worker.on_tts_generator_worker_add_to_stream_signal(
                        data
                    )
            # TTS enable now handled exclusively by daemon
            # STT load now handled exclusively by daemon
            elif request_type == "stt_process":
                self._process_stt_through_daemon(data)
            elif request_type == "stt_start_capture":
                if self.stt_audio_capture_worker is not None:
                    self.stt_audio_capture_worker.on_stt_start_capture_signal(
                        data
                    )

        except Exception as e:
            if self.logger:
                self.logger.error(
                    f"Error processing worker requests: {e}", exc_info=True
                )

    @property
    def model_scanner_worker(self):
        if self._model_scanner_worker is None:
            from airunner.components.application.workers.model_scanner_worker import (
                ModelScannerWorker,
            )

            self._model_scanner_worker = create_worker(ModelScannerWorker)
        return self._model_scanner_worker

    @property
    def image_export_worker(self):
        if self._image_export_worker is None:
            from airunner.components.art.workers.image_export_worker import (
                ImageExportWorker,
            )

            self._image_export_worker = create_worker(ImageExportWorker)
        return self._image_export_worker

    # safety_checker_worker removed; daemon handles via future API

    @property
    def mask_generator_worker(self):
        if self._mask_generator_worker is None:
            from airunner.components.art.workers.mask_generator_worker import (
                MaskGeneratorWorker,
            )

            self._mask_generator_worker = create_worker(MaskGeneratorWorker)
        return self._mask_generator_worker

    @property
    def stt_audio_capture_worker(self):
        if self._stt_audio_capture_worker is None:
            from airunner.components.stt.workers.audio_capture_worker import (
                AudioCaptureWorker,
            )

            self._stt_audio_capture_worker = create_worker(AudioCaptureWorker)
        return self._stt_audio_capture_worker

    # stt_audio_processor_worker removed; STT transcription via daemon client

    # tts_generator_worker removed; TTS synthesis via daemon client

    @property
    def tts_vocalizer_worker(self):
        if self._tts_vocalizer_worker is None:
            from airunner.components.tts.workers.tts_vocalizer_worker import (
                TTSVocalizerWorker,
            )

            self._tts_vocalizer_worker = create_worker(
                TTSVocalizerWorker,
                sleep_time_in_ms=_STREAM_TTS_WORKER_SLEEP_MS,
            )
        return self._tts_vocalizer_worker

    @property
    def llm_generate_worker(self):
        if self._llm_generate_worker is None:
            try:
                from airunner_services.workers.llm_generate_worker import (
                    LLMGenerateWorker,
                )
            except ImportError:
                from airunner.components.llm.workers.llm_generate_worker import (
                    LLMGenerateWorker,
                )
            self._llm_generate_worker = create_worker(LLMGenerateWorker)
        return self._llm_generate_worker

    @property
    def document_worker(self):
        if self._document_worker is None:
            from airunner.components.documents.workers.document_worker import (
                DocumentWorker,
            )

            self._document_worker = create_worker(DocumentWorker)
        return self._document_worker

    @property
    def huggingface_download_worker(self):
        if self._huggingface_download_worker is None:
            from airunner.components.application.workers.huggingface_download_worker import (
                HuggingFaceDownloadWorker,
            )

            self._huggingface_download_worker = create_worker(
                HuggingFaceDownloadWorker
            )
        return self._huggingface_download_worker

    def on_start_auto_image_generation_signal(self, data: Dict):
        self.add_to_queue(
            {
                "data": data,
                "request_type": "image_auto_generate",
            }
        )

    # on_do_generate_signal implementation below (daemon-routed)

    def on_tts_generator_worker_add_to_stream_signal(self, data: Dict):
        self.add_to_queue({"data": data, "request_type": "tts_generate"})

    def on_enable_tts_signal(self, data: Dict):
        from airunner.enums import ModelType

        if self._control_daemon_runtime_async(
            "tts",
            "load",
            ModelType.TTS,
            route_metadata=self._tts_runtime_route_metadata(),
        ):
            return
        # TTS enable now handled exclusively by daemon

    def on_stt_load_signal(self, data: Dict):
        from airunner.enums import ModelType

        if self._control_daemon_runtime_async(
            "stt",
            "load",
            ModelType.STT,
            after_success=lambda: self.emit_signal(
                SignalCode.STT_START_CAPTURE_SIGNAL,
                data,
            ),
        ):
            return
        # STT load now handled exclusively by daemon

    def on_stt_start_capture_signal(self, data: Dict):
        self.add_to_queue(
            {
                "data": data,
                "request_type": "stt_start_capture",
            }
        )

    def on_art_model_download_required(self, data: Dict):
        """Handle art model download requirement.

        Args:
            data: Download info with repo_id, model_path, missing_files, version, etc.
        """
        import os

        repo_id = data.get("repo_id")
        model_path = data.get("model_path")
        missing_files = data.get("missing_files", [])
        version = data.get("version", "")
        pipeline_action = data.get("pipeline_action", "txt2img")

        # Store the pending image generation request so we can retry after download
        image_request = data.get("image_request")
        if image_request:
            self._pending_generation_request = (
                data  # Store the full data dict, not just image_request
            )
            if self.logger:
                self.logger.info(
                    "Stored pending generation request to retry after download"
                )

        if self.logger:
            self.logger.info(
                f"WorkerManager: Starting download for {repo_id} ({len(missing_files)} missing files)"
            )

        # Determine model type for download worker.
        # All art models use "art" type for bootstrap data lookup.
        model_type = "art"

        # Determine output directory (parent of model file for single-file models, or model_path for repos)
        single_file_extensions = (
            ".gguf",
            ".safetensors",
            ".ckpt",
            ".pt",
            ".pth",
        )
        if model_path and model_path.lower().endswith(single_file_extensions):
            output_dir = os.path.dirname(model_path)
        else:
            output_dir = model_path

        # Show download dialog (modal to ensure it stays visible)
        main_window = self._get_main_window()
        if main_window:
            try:
                from airunner.components.llm.gui.windows.huggingface_download_dialog import (
                    HuggingFaceDownloadDialog,
                )

                # Close any existing download dialog
                if self._download_dialog:
                    self._download_dialog.close()
                    self._download_dialog = None

                # Create new download dialog and store reference
                self._download_dialog = HuggingFaceDownloadDialog(
                    parent=main_window,
                    model_name=f"{version} Config Files",
                    model_path=output_dir,
                )

                # Connect dialog to download worker signals
                self.huggingface_download_worker.register(
                    SignalCode.UPDATE_DOWNLOAD_LOG,
                    self._download_dialog.on_log_updated,
                )
                self.huggingface_download_worker.register(
                    SignalCode.UPDATE_DOWNLOAD_PROGRESS,
                    self._download_dialog.on_progress_updated,
                )
                self.huggingface_download_worker.register(
                    SignalCode.UPDATE_FILE_DOWNLOAD_PROGRESS,
                    self._download_dialog.on_file_progress_updated,
                )
                self.huggingface_download_worker.register(
                    SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
                    self._download_dialog.on_download_complete,
                )
                self.huggingface_download_worker.register(
                    SignalCode.HUGGINGFACE_DOWNLOAD_FAILED,
                    self._download_dialog.on_download_failed,
                )

                # Show the dialog
                self._download_dialog.show()
                self._download_dialog.raise_()
                self._download_dialog.activateWindow()

                if self.logger:
                    self.logger.info(
                        "Download dialog shown and connected to worker signals"
                    )
            except Exception as e:
                if self.logger:
                    self.logger.error(
                        f"Error showing download dialog: {e}", exc_info=True
                    )
        else:
            if self.logger:
                self.logger.error(
                    "Unable to locate the main window; download dialog could not be displayed"
                )

        # Queue download request
        download_data = {
            "repo_id": repo_id,
            "model_type": model_type,
            "version": version,  # Pass full version name for bootstrap data lookup
            "pipeline_action": pipeline_action,  # Pass pipeline action (txt2img, inpaint, etc.)
            "output_dir": output_dir,
            "missing_files": missing_files,  # Pass specific missing files to download
        }

        if self.logger:
            self.logger.info(
                "Queueing download request (%s)",
                summarize_mapping_keys(download_data, label="download"),
            )

        self.huggingface_download_worker.add_to_queue(download_data)

    def _get_main_window(self):
        """Return the main application window if available."""
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:
            return None

        app = QApplication.instance()
        if app is None:
            return None

        main_window = getattr(app, "main_window", None)
        if main_window is not None:
            return main_window

        # In headless mode we often run a QCoreApplication event loop, which
        # doesn't support QWidget APIs like activeWindow/topLevelWidgets.
        if not hasattr(app, "activeWindow") or not hasattr(app, "topLevelWidgets"):
            return None

        window = app.activeWindow()
        if window is not None:
            return window

        for widget in app.topLevelWidgets():
            if (
                widget.objectName() == "MainWindow"
                or widget.__class__.__name__ == "MainWindow"
            ):
                return widget

        # Fallback: some components expose the main window via settings API
        return getattr(self.api, "main_window", None)

    @staticmethod
    def _normalize_api_candidate(candidate):
        """Return one app-like API object from a nested candidate."""
        if candidate is None:
            return None

        root_api = getattr(candidate, "api", None)
        if root_api is not None and getattr(candidate, "daemon_client", None) is None:
            return root_api

        app_api = getattr(getattr(candidate, "app", None), "api", None)
        if app_api is not None and getattr(candidate, "daemon_client", None) is None:
            return app_api
        return candidate

    def _current_gui_api(self):
        """Return the best live GUI API reference for worker actions."""
        candidates = []
        refresher = getattr(self, "refresh_api_reference", None)
        if callable(refresher):
            candidates.append(refresher())
        candidates.append(getattr(self, "api", None))

        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is not None:
                candidates.append(getattr(app, "api", None))
                candidates.append(getattr(app, "main_window", None))
        except Exception:
            pass

        try:
            from airunner.components.server.api.server import get_api

            candidates.append(get_api(create_if_missing=False))
        except Exception:
            pass

        fallback_api = None
        for candidate in candidates:
            candidate = self._normalize_api_candidate(candidate)
            if candidate is None or getattr(candidate, "headless", False):
                continue
            if getattr(candidate, "daemon_client", None) is not None:
                self.api = candidate
                return candidate
            if fallback_api is None:
                fallback_api = candidate

        if fallback_api is not None:
            self.api = fallback_api
        return fallback_api

    def _daemon_client(self):
        """Return the GUI daemon client when daemon-backed mode is active."""
        api = self._current_gui_api()
        if api is None:
            return None
        return getattr(api, "daemon_client", None)

    def _llm_daemon_client(self):
        """Return one daemon client for LLM controls.

        The chat stop button resolves through the LLM service, so unload needs
        the same fallback when the WorkerManager API reference is stale.
        """
        client = self._daemon_client()
        if client is not None:
            return client

        api = self._current_gui_api()
        llm_service = getattr(api, "llm", None) if api is not None else None
        resolver = getattr(llm_service, "_daemon_client", None)
        if not callable(resolver):
            return None
        try:
            return resolver()
        except Exception:
            return None

    def _llm_worker_for_unload(self, *, create: bool = False):
        """Local LLM worker removed; daemon handles all LLM state."""
        return None

    def _local_llm_should_handle_unload(self) -> bool:
        """Local LLM worker removed; daemon handles all LLM state."""
        return False
        from airunner.enums import ModelStatus

        worker = self._llm_worker_for_unload(create=False)
        if worker is None:
            return False
        if not callable(
            getattr(worker, "llm_on_interrupt_process_signal", None)
        ):
            return False
        if not callable(getattr(worker, "add_to_queue", None)):
            return False

        status_getter = getattr(worker, "current_model_status", None)
        if callable(status_getter):
            try:
                status = status_getter()
            except Exception:
                status = None
            if status in (ModelStatus.LOADING, ModelStatus.LOADED):
                return True

        if getattr(worker, "_pending_llm_request", None) is not None:
            return True
        return False

    def _is_optional_runtime_unload(self, action: str, model_type) -> bool:
        """Return True for best-effort TTS/STT unload requests."""
        from airunner.enums import ModelType

        return action == "unload" and model_type in (
            ModelType.TTS,
            ModelType.STT,
        )

    @staticmethod
    def _is_optional_runtime_load(action: str, model_type) -> bool:
        """Return True for TTS/STT load requests."""
        from airunner.enums import ModelType

        return action == "load" and model_type in (
            ModelType.TTS,
            ModelType.STT,
        )

    @staticmethod
    def _optional_runtime_setting_name(model_type) -> str | None:
        """Return the preference column for one optional runtime."""
        from airunner.enums import ModelType

        if model_type is ModelType.TTS:
            return "tts_enabled"
        if model_type is ModelType.STT:
            return "stt_enabled"
        return None

    def _optional_runtime_enabled(self, model_type) -> bool:
        """Return the saved preference for one optional runtime."""
        setting_name = self._optional_runtime_setting_name(model_type)
        if setting_name is None:
            return True
        return bool(getattr(self.application_settings, setting_name, False))

    @staticmethod
    def _is_timeout_error(error: RuntimeError) -> bool:
        """Return True when one daemon request failed due to timeout."""
        return "timeout" in str(error).lower()

    def _should_wait_after_runtime_timeout(
        self,
        action: str,
        model_type,
        error: RuntimeError,
    ) -> bool:
        """Return True when a timed-out request may still converge."""
        if not self._is_timeout_error(error):
            return False
        return self._is_optional_runtime_unload(
            action,
            model_type,
        ) or self._is_optional_runtime_load(action, model_type)

    def _runtime_action_timeout_seconds(
        self,
        action: str,
        model_type,
    ) -> float | None:
        """Return the request timeout for one daemon lifecycle action."""
        if self._is_optional_runtime_unload(action, model_type):
            return _OPTIONAL_UNLOAD_REQUEST_TIMEOUT_SECONDS
        if self._is_optional_runtime_load(action, model_type):
            return _OPTIONAL_LOAD_REQUEST_TIMEOUT_SECONDS
        return None

    def _runtime_wait_timeout_seconds(
        self,
        action: str,
        model_type,
    ) -> float:
        """Return the daemon wait timeout for one lifecycle action."""
        from airunner.enums import ModelType

        if self._is_optional_runtime_unload(action, model_type):
            return _OPTIONAL_UNLOAD_WAIT_TIMEOUT_SECONDS
        if action == "load" and model_type is ModelType.STT:
            return 60.0
        if action == "load" and model_type is ModelType.TTS:
            return _TTS_LOAD_WAIT_TIMEOUT_SECONDS
        return 30.0

    def _emit_daemon_runtime_failure(
        self,
        action: str,
        runtime_name: str,
        model_type,
        message: str,
    ) -> bool:
        """Emit the right terminal status after one daemon action fails."""
        from airunner.enums import ModelStatus, SignalCode

        local_status = self._preferred_local_llm_status_for_failure(
            action,
            runtime_name,
            model_type,
        )
        if local_status is not None:
            if self.logger:
                self.logger.debug(
                    "%s; keeping local LLM status=%s",
                    message,
                    local_status.value,
                )
            self.emit_signal(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
                {"model": model_type, "status": local_status},
            )
            return True

        if self.logger:
            if self._is_optional_runtime_unload(action, model_type):
                self.logger.debug(message)
            else:
                self.logger.warning(message)
        status = ModelStatus.FAILED
        if self._is_optional_runtime_unload(action, model_type):
            status = ModelStatus.UNLOADED
        self.emit_signal(
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": model_type, "status": status},
        )
        return True

    def _preferred_local_llm_status_for_failure(
        self,
        action: str,
        runtime_name: str,
        model_type,
    ):
        """Return one local LLM status that should override daemon failure."""
        from airunner.enums import ModelStatus, ModelType

        if runtime_name != "llm" or model_type is not ModelType.LLM:
            return None

        # Local LLM worker removed; daemon handles all LLM state
        if True:
            if action == "load":
                return ModelStatus.UNLOADED
            return None

        current_model_status = getattr(worker, "current_model_status", None)
        if not callable(current_model_status):
            return None

        try:
            status = current_model_status()
        except Exception:
            return None

        if action == "load" and status in (
            ModelStatus.LOADING,
            ModelStatus.LOADED,
            ModelStatus.UNLOADED,
            ModelStatus.FAILED,
        ):
            return status

        if action == "unload" and status in (
            ModelStatus.LOADED,
            ModelStatus.UNLOADED,
        ):
            return status

        return None

    def _revert_optional_runtime_load(
        self,
        client,
        runtime_name: str,
        model_type,
    ) -> bool:
        """Unload one optional runtime when its saved preference was cleared."""
        from airunner.enums import ModelStatus, SignalCode

        try:
            ready = self._run_daemon_runtime_action(
                client,
                runtime_name,
                "unload",
                model_type,
            )
        except RuntimeError as exc:
            return self._emit_daemon_runtime_failure(
                "unload",
                runtime_name,
                model_type,
                "Daemon unload for %s failed after preference change: %s"
                % (runtime_name, exc),
            )
        if not ready:
            return self._emit_daemon_runtime_failure(
                "unload",
                runtime_name,
                model_type,
                "Daemon unload for %s timed out waiting for runtime "
                "state after preference change" % runtime_name,
            )
        self.emit_signal(
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": model_type, "status": ModelStatus.UNLOADED},
        )
        return True

    def _run_daemon_runtime_action(
        self,
        client,
        runtime_name: str,
        action: str,
        model_type,
        route_metadata: Dict | None = None,
    ) -> bool:
        """Run one daemon load or unload request and wait for its state."""
        loaded = action == "load"
        action_timeout = self._runtime_action_timeout_seconds(
            action,
            model_type,
        )
        wait_timeout = self._runtime_wait_timeout_seconds(
            action,
            model_type,
        )
        deployment_mode = self._daemon_runtime_deployment_mode(
            runtime_name,
            model_type,
        )
        runtime_method = client.load_runtime if loaded else client.unload_runtime
        try:
            runtime_method(
                runtime_name,
                deployment_mode=deployment_mode,
                metadata=route_metadata,
                timeout_seconds=action_timeout,
            )
        except RuntimeError as exc:
            if not self._should_wait_after_runtime_timeout(
                action,
                model_type,
                exc,
            ):
                raise
            if self.logger:
                self.logger.debug(
                    "Daemon %s request for %s timed out; waiting for state",
                    action,
                    runtime_name,
                )
        return client.wait_runtime_ready(
            runtime_name,
            loaded=loaded,
            deployment_mode=deployment_mode,
            timeout_seconds=wait_timeout,
        )

    def _control_daemon_runtime(
        self,
        runtime_name: str,
        action: str,
        model_type,
        route_metadata: Dict | None = None,
        before_request=None,
        after_success=None,
    ) -> bool:
        """Translate a GUI lifecycle request into one daemon runtime action."""
        from airunner.enums import ModelStatus, SignalCode

        client = self._daemon_client()
        if client is None:
            return False
        if before_request is not None:
            before_request()
        if action == "load":
            self.emit_signal(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
                {"model": model_type, "status": ModelStatus.LOADING},
            )
        try:
            ready = self._run_daemon_runtime_action(
                client,
                runtime_name,
                action,
                model_type,
                route_metadata=route_metadata,
            )
            status = ModelStatus.LOADED
            if action == "unload":
                status = ModelStatus.UNLOADED
        except RuntimeError as exc:
            if (
                self._is_optional_runtime_load(action, model_type)
                and not self._optional_runtime_enabled(model_type)
            ):
                return self._revert_optional_runtime_load(
                    client,
                    runtime_name,
                    model_type,
                )
            return self._emit_daemon_runtime_failure(
                action,
                runtime_name,
                model_type,
                "Daemon %s for %s failed: %s" % (
                    action,
                    runtime_name,
                    exc,
                ),
            )
        if (
            action == "load"
            and self._is_optional_runtime_load(action, model_type)
            and not self._optional_runtime_enabled(model_type)
        ):
            return self._revert_optional_runtime_load(
                client,
                runtime_name,
                model_type,
            )
        if not ready:
            return self._emit_daemon_runtime_failure(
                action,
                runtime_name,
                model_type,
                "Daemon %s for %s timed out waiting for runtime state"
                % (action, runtime_name),
            )
        self.emit_signal(
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": model_type, "status": status},
        )
        if after_success is not None:
            after_success()
        return True

    def _control_daemon_runtime_async(
        self,
        runtime_name: str,
        action: str,
        model_type,
        route_metadata: Dict | None = None,
        before_request=None,
        after_success=None,
    ) -> bool:
        """Run one daemon runtime action without blocking the caller."""
        if self._daemon_client() is None:
            return False

        thread = threading.Thread(
            target=self._control_daemon_runtime,
            args=(runtime_name, action, model_type),
            kwargs={
                "route_metadata": route_metadata,
                "before_request": before_request,
                "after_success": after_success,
            },
            daemon=True,
        )
        thread.start()
        return True

    def _run_daemon_llm_unload(self) -> bool:
        """Unload the daemon-managed local LLM without blocking the UI."""
        from airunner.enums import ModelStatus, ModelType, SignalCode

        client = self._llm_daemon_client()
        if client is None:
            return False
        try:
            client.interrupt_llm()
        except RuntimeError:
            pass
        try:
            client.unload_local_llm()
        except RuntimeError as exc:
            return self._emit_daemon_runtime_failure(
                "unload",
                "llm",
                ModelType.LLM,
                "Daemon unload for llm failed: %s" % exc,
            )
        ready = client.wait_runtime_ready(
            "llm",
            loaded=False,
            timeout_seconds=self._runtime_wait_timeout_seconds(
                "unload",
                ModelType.LLM,
            ),
        )
        if not ready:
            return self._emit_daemon_runtime_failure(
                "unload",
                "llm",
                ModelType.LLM,
                "Daemon unload for llm timed out waiting for runtime state",
            )
        self.emit_signal(
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": ModelType.LLM, "status": ModelStatus.UNLOADED},
        )
        return True

    def _unload_daemon_llm_async(self) -> bool:
        """Start the daemon-backed local LLM unload in a background thread."""
        if self._llm_daemon_client() is None:
            return False
        thread = threading.Thread(
            target=self._run_daemon_llm_unload,
            name="airunner-llm-unload",
            daemon=True,
        )
        thread.start()
        return True

    def _tts_runtime_route_metadata(self) -> Dict[str, str]:
        """Return the active TTS model settings for daemon control."""
        metadata: Dict[str, str] = {}
        voice_settings = getattr(self, "chatbot_voice_settings", None)
        if voice_settings is not None:
            model_type = getattr(voice_settings, "model_type", None)
            if model_type:
                metadata["model_type"] = str(model_type)
        path_settings = getattr(self, "path_settings", None)
        if path_settings is not None:
            model_path = getattr(path_settings, "tts_model_path", None)
            if model_path:
                metadata["model_path"] = str(model_path)
        return metadata

    @staticmethod
    def _daemon_runtime_deployment_mode(
        runtime_name: str,
        model_type,
    ) -> str:
        """Return the daemon deployment mode used for one runtime action."""
        from airunner.enums import ModelType

        if runtime_name in {"art", "tts", "stt"} or model_type in {
            ModelType.SD,
            ModelType.TTS,
            ModelType.STT,
        }:
            return "sidecar"
        return "default"

    def on_huggingface_download_complete(self, data: Dict):
        """Handle download completion and retry pending generation.

        Args:
            data: Download completion info with model_path
        """
        # Skip if we're in a batch download (OpenVoice handles its own completion)
        if hasattr(self, "_openvoice_remaining_downloads") and self._openvoice_remaining_downloads is not None:
            if self.logger:
                self.logger.debug(
                    f"Skipping generic download complete handler during batch download"
                )
            return
        
        # Handle safety checker downloads - notify via queue to ensure thread safety
        pipeline_action = data.get("pipeline_action", "")
        if pipeline_action == "safety_checker":
            if self.logger:
                self.logger.info(
                    "Safety checker download complete, notifying worker to retry load"
                )
            # Use queue to ensure thread-safe notification
            # Safety checker load now via daemon (future API)
            return
        
        if self.logger:
            self.logger.info(
                f"WorkerManager: Download complete for {data.get('model_path')}"
            )
            self.logger.info(
                f"Pending generation request: {self._pending_generation_request is not None}"
            )

        # Delegate to LLM worker only for LLM model downloads
        # Skip TTS, STT, and other non-LLM model types
        # Use add_to_queue to ensure processing happens in worker thread,
        # not main thread, to prevent UI lockups during model loading
        model_type = data.get("model_type", "")
        non_llm_types = {"tts_openvoice", "stt", "openvoice_zip", "art"}
        # Download completion routing removed; handled by daemon

        # If we have a pending generation request (for image generation), retry it now
        if self._pending_generation_request:
            if self.logger:
                self.logger.info(
                    "Retrying pending generation request after download completion"
                )
                self.logger.debug(
                    f"Image request details: {self._pending_generation_request}"
                )

            # Re-emit the generation signal to trigger model loading and generation
            # The pending request already has the correct structure
            self.emit_signal(
                SignalCode.DO_GENERATE_SIGNAL,
                self._pending_generation_request,
            )
            self._pending_generation_request = None
        else:
            if self.logger:
                self.logger.warning(
                    "No pending generation request found after download completion"
                )

    def _interrupt_active_daemon_art_job(self, data: Dict) -> bool:
        """Local SD worker removed; daemon handles all art state."""
        return False
        if callable(request_unload):
            if not request_unload():
                return False
        elif not getattr(worker, "_active_daemon_job_id", None):
            return False
        else:
            worker._pending_daemon_unload_after_cancel = True

        worker.on_interrupt_image_generation_signal(data)
        return True

    def on_unload_art_signal(self, data: Dict):
        from airunner.enums import ModelType

        data = data or {}
        if self._interrupt_active_daemon_art_job(data):
            return

        if self._control_daemon_runtime_async(
            "art",
            "unload",
            ModelType.SD,
        ):
            return
        # Art unloading is now handled exclusively by the daemon

    def on_model_status_changed_signal(self, data):
        from airunner.enums import ModelStatus, ModelType

        model_type = data.get("model") or data.get("model_type")
        status = data.get("status")

        if model_type == ModelType.TTS:
            if status in (ModelStatus.LOADED, ModelStatus.READY):
                pass
        
        if (
            model_type == ModelType.SAFETY_CHECKER
            and status == ModelStatus.LOADED
            and self._pending_generation_request is not None
        ):
            self.logger.info(
                "Safety checker loaded, proceeding with pending image generation"
            )
            # Note: Don't clear _pending_generation_request here - it will be cleared
            # by on_huggingface_download_complete after the SD model download completes,
            # or it will be set to None if no download is needed (generation proceeds immediately)
            self._proceed_with_generation(self._pending_generation_request)

        elif (
            model_type == ModelType.SAFETY_CHECKER
            and status == ModelStatus.FAILED
            and self._pending_generation_request is not None
        ):
            # Check if this was a download-triggered failure (we should wait for download)
            # or a real failure (show error)
            # The safety checker worker emits FAILED only after download fails or load fails
            # If NSFW filter is enabled, we should NOT proceed - show error instead
            from airunner_model.models.application_settings import (
                ApplicationSettings,
            )
            app_settings = self._get_or_create_application_settings()
            
            if app_settings.nsfw_filter:
                self.logger.error(
                    "Safety checker failed to load and NSFW filter is enabled. Cannot proceed with generation."
                )
                # Clear pending request since we're not proceeding
                self._pending_generation_request = None
                # Show error popup to user
                self.api.application_error(
                    message="Safety checker failed to load. Please disable the NSFW filter in settings or wait for the safety checker to download."
                )
            else:
                self.logger.warning(
                    "Safety checker failed to load; continuing image generation (NSFW filter disabled)"
                )
                self._proceed_with_generation(self._pending_generation_request)

        if self._stt_audio_capture_worker is not None:
            self.stt_audio_capture_worker.on_model_status_changed_signal(data)

    def on_load_art_signal(self, data):
        if self._daemon_client() is not None:
            return
        # Art loading is now handled exclusively by the daemon

    def on_do_generate_signal(self, data: dict) -> None:
        """Route art generation through the daemon and emit result."""
        import threading

        def _generate():
            try:
                image_request = data.get("image_request")
                if image_request is None:
                    self.logger.error(
                        "Art generation: no image_request in data"
                    )
                    return

                client = self._daemon_client()
                if client is None:
                    self.logger.error(
                        "Art generation: daemon unavailable"
                    )
                    return

                # Submit job to daemon
                result = client.start_art_generation(
                    prompt=getattr(image_request, "prompt", ""),
                    negative_prompt=getattr(
                        image_request, "negative_prompt", ""
                    ),
                    width=getattr(image_request, "width", 1024),
                    height=getattr(image_request, "height", 1024),
                    steps=getattr(image_request, "steps", 20),
                    cfg_scale=getattr(image_request, "scale", 7.5),
                    seed=getattr(image_request, "seed", None),
                    num_images=getattr(image_request, "n_samples", 1),
                    model=getattr(image_request, "model_path", None),
                    version=getattr(image_request, "version", None),
                    scheduler=getattr(image_request, "scheduler", None),
                    pipeline=getattr(
                        image_request, "pipeline_action", None
                    ),
                    strength=getattr(image_request, "strength", None),
                )
                job_id = result.get("job_id")
                self.logger.info(
                    f"Art generation submitted, job_id={job_id}"
                )

                if not job_id:
                    self.logger.error("Art generation: no job_id returned")
                    return

                # Poll until complete and retrieve image
                self.logger.info(
                    f"Waiting for art job {job_id} to complete..."
                )

                def _progress_callback(status: dict) -> None:
                    progress = float(status.get("progress", 0))
                    self.emit_signal(
                        SignalCode.SD_PROGRESS_SIGNAL,
                        {
                            "step": int(progress),
                            "total": 100,
                        },
                    )

                png_bytes = client.wait_art_job(
                    job_id,
                    timeout_seconds=600.0,
                    progress_callback=_progress_callback,
                )
                self.logger.info(
                    f"Art job {job_id} complete, "
                    f"received {len(png_bytes)} bytes"
                )

                # Convert PNG bytes to image and emit for GUI display
                from PIL import Image
                import io
                from airunner.utils.image import convert_image_to_binary
                from airunner.enums import EngineResponseCode
                from airunner.components.art.managers.stablediffusion.image_response import (
                    ImageResponse,
                )

                image = Image.open(io.BytesIO(png_bytes))
                image_data = convert_image_to_binary(image)

                # Build ImageResponse and send to canvas
                response = ImageResponse(
                    images=[image],
                    data={
                        "generator_section": getattr(
                            image_request, "generator_section", None
                        ),
                    },
                    active_rect=None,
                    is_outpaint=False,
                )
                self.emit_signal(
                    SignalCode.SEND_IMAGE_TO_CANVAS_SIGNAL,
                    {"image_response": response},
                )
                self.logger.info(
                    f"Image sent to canvas: "
                    f"{len(image_data)} bytes"
                )
            except Exception as exc:
                self.logger.error(
                    f"Art generation failed: {exc}"
                )

        threading.Thread(target=_generate, daemon=True).start()

    def on_application_main_window_loaded_signal(self, _data=None):
        """Main window loaded — runtimes loaded on demand only."""
        # Art runtime pre-warm disabled; models load on first generation
        if not getattr(self.application_settings, "tts_enabled", False):
            return

        self.on_enable_tts_signal({"source": "startup"})

    def on_art_model_changed(self, data):
        # Art runtime pre-warm disabled; models load on first generation
        pass

    def on_safety_checker_load_signal(self, data):
        # Safety checker now handled by daemon (future API)
        pass
        # Using add_to_queue ensures thread-safe message passing
        # Safety checker worker removed; daemon migration pending

    def on_safety_checker_unload_signal(self, data):
        # Safety checker unload handled by daemon (future API)
        pass
        if self._safety_checker_worker is not None:
            self.safety_checker_worker.add_to_queue(
                {"action": "unload", "data": data}
            )

    def _handle_image_generation_request(self, data):
        """
        Handle image generation request, ensuring safety checker is ready if needed.

        Args:
            data: Image generation request data
        """
        from airunner_model.models.application_settings import (
            ApplicationSettings,
        )

        app_settings = self._get_or_create_application_settings()

        # Check if safety checker is enabled
        if not app_settings.nsfw_filter:
            # Safety checker disabled, proceed immediately
            self._proceed_with_generation(data)
            return

        # Safety checker is enabled, check if it's already loaded
        safety_worker = self.safety_checker_worker
        if (
            safety_worker
            and safety_worker.safety_checker is not None
            and safety_worker.feature_extractor is not None
        ):
            # Already loaded, proceed immediately
            self._proceed_with_generation(data)
            return

        # Safety checker needs to be loaded, store the request and trigger load
        self.logger.info(
            "Safety checker not ready, triggering load before generation"
        )
        self._pending_generation_request = data
        self.emit_signal(SignalCode.SAFETY_CHECKER_LOAD_SIGNAL, {})

    def _get_or_create_application_settings(self):
        """Return ApplicationSettings for the current tenant.

        In headless multi-tenant mode, tenant schemas may be created on-demand and
        not have bootstrap rows yet. Image generation expects ApplicationSettings
        to exist; without it, requests crash and art jobs stay RUNNING forever.
        """
        from airunner_model.models.application_settings import (
            ApplicationSettings,
        )

        app_settings = ApplicationSettings.objects.first()
        if app_settings is not None:
            return app_settings

        # Create a sane default row for this tenant.
        # - Enable SD if the service is enabled in this headless server.
        # - Default NSFW filter off in headless mode to avoid blocking generation
        #   on a safety-checker bootstrap step.
        try:
            import os

            ApplicationSettings(
                sd_enabled=os.environ.get("AIRUNNER_SD_ON") == "1",
                llm_enabled=True,
                nsfw_filter=False,
            ).save()
        except Exception:
            # Best-effort; if creation fails, subsequent code will raise a clearer error.
            pass

        app_settings = ApplicationSettings.objects.first()
        if app_settings is None:
            raise RuntimeError(
                "ApplicationSettings row is missing and could not be created"
            )
        return app_settings

    def _proceed_with_generation(self, data):
        """
        Proceed with image generation after safety checker is ready (or not needed).

        Args:
            data: Image generation request data
        """
        self.logger.debug(
            "_proceed_with_generation called with data keys: %s",
            data.keys() if data else "None",
        )
        # SD generation now handled exclusively by the daemon

    def on_llm_on_unload_signal(self, data):
        data = data or {}

        if self._local_llm_should_handle_unload():
            worker = self._llm_worker_for_unload(create=False)
            if worker is None:
                return
            worker.llm_on_interrupt_process_signal(data)
            worker.add_to_queue(
                {
                    "_message_type": "llm_unload",
                    "data": data,
                }
            )
            return

        if self._unload_daemon_llm_async():
            return
        worker = self._llm_worker_for_unload(create=True)
        if worker is None:
            return

        worker.llm_on_interrupt_process_signal(data)
        worker.add_to_queue(
            {
                "_message_type": "llm_unload",
                "data": data,
            }
        )

    def on_llm_load_model_signal(self, data):
        from airunner.enums import ModelType

        if self._control_daemon_runtime("llm", "load", ModelType.LLM):
            return
        # LLM loading is now handled exclusively by the daemon

    def _llm_model_change_requires_runtime_reload(self, data) -> bool:
        """Return True when a model-change notification should unload."""
        if not isinstance(data, dict):
            return False
        return bool(data.get("reload_runtime"))

    def _handle_llm_download_directly(self, data):
        """Handle LLM model download when LLM worker is not available.
        
        This allows downloading models from settings before the LLM is loaded.
        """
        from PySide6.QtWidgets import QApplication
        from airunner.components.llm.config.provider_config import LLMProviderConfig
        from airunner.components.llm.gui.windows.huggingface_download_dialog import (
            HuggingFaceDownloadDialog,
        )
        from airunner.components.llm.managers.download_huggingface import (
            DownloadHuggingFaceModel,
        )
        
        model_path = data.get("model_path", "")
        model_name = data.get("model_name", "Unknown Model")
        repo_id = data.get("repo_id", "")
        model_type = data.get("model_type", "llm")
        gguf_filename = data.get("gguf_filename")

        resolved_download = LLMProviderConfig.resolve_download_target(
            "local",
            repo_id=repo_id,
            prefer_pre_quantized=True,
        )
        if resolved_download and resolved_download.get("model_type") == "gguf":
            repo_id = resolved_download["repo_id"]
            model_type = "gguf"
            gguf_filename = resolved_download["gguf_filename"]
            model_name = resolved_download.get("model_name", model_name)
        
        if not repo_id:
            self.logger.error("No repo_id provided in download request")
            return
        
        # Get main window
        main_window = None
        app = QApplication.instance()
        for widget in app.topLevelWidgets():
            if widget.__class__.__name__ == "MainWindow":
                main_window = widget
                break
        
        if not main_window:
            self.logger.error("Cannot show download dialog - main window not found")
            return
        
        is_gguf = model_type == "gguf" or gguf_filename is not None
        dialog_model_name = f"{model_name} (GGUF)" if is_gguf else model_name
        
        # Create and show download dialog
        self._download_dialog = HuggingFaceDownloadDialog(
            parent=main_window,
            model_name=dialog_model_name,
            model_path=model_path,
        )
        
        # Create download worker - use local variable to avoid polluting the 
        # huggingface_download_worker property which is used for STT/TTS downloads
        llm_download_worker = create_worker(DownloadHuggingFaceModel)
        
        # Connect dialog to download worker signals
        llm_download_worker.register(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            self._download_dialog.on_log_updated,
        )
        llm_download_worker.register(
            SignalCode.UPDATE_DOWNLOAD_PROGRESS,
            self._download_dialog.on_progress_updated,
        )
        llm_download_worker.register(
            SignalCode.UPDATE_FILE_DOWNLOAD_PROGRESS,
            self._download_dialog.on_file_progress_updated,
        )
        llm_download_worker.register(
            SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
            self._download_dialog.on_download_complete,
        )
        llm_download_worker.register(
            SignalCode.HUGGINGFACE_DOWNLOAD_FAILED,
            self._download_dialog.on_download_failed,
        )
        
        if is_gguf and gguf_filename:
            self.logger.info("Starting GGUF download")
            llm_download_worker.download(
                repo_id=repo_id,
                model_type="gguf",
                output_dir=model_path,
                setup_quantization=False,
                quantization_bits=0,
                missing_files=None,
                gguf_filename=gguf_filename,
            )
        else:
            self.logger.info(f"Starting standard download: {repo_id}")
            llm_download_worker.download(
                repo_id=repo_id,
                model_type=model_type,
                output_dir=os.path.dirname(model_path),
                setup_quantization=True,
                quantization_bits=data.get("quantization_bits", 4),
                missing_files=data.get("missing_files"),
            )
        
        self._download_dialog.show()

    def on_huggingface_download_complete_signal(self, data):
        # Download completion routing removed; handled by daemon
        pass

    def on_quit_application_signal(self, data):
        pass

    def on_generate_mask_signal(self, data):
        if self._mask_generator_worker is not None:
            self.mask_generator_worker.on_generate_mask_signal(data)

    def on_audio_capture_worker_response_signal(self, data):
        if self._stt_audio_capture_worker is not None:
            self.stt_audio_capture_worker.on_audio_capture_worker_response_signal(
                data
            )

    def on_stt_stop_capture_signal(self, data):
        if self._stt_audio_capture_worker is not None:
            self.stt_audio_capture_worker.on_stt_stop_capture_signal(data)

    def on_recording_device_changed_signal(self, data):
        if self._stt_audio_capture_worker is not None:
            self.stt_audio_capture_worker.on_recording_device_changed_signal(
                data
            )

    def update_properties(self, data):
        # STT processor removed; daemon handles transcription
        pass

    def on_stt_unload_signal(self, data):
        from airunner.enums import ModelType

        self.emit_signal(
            SignalCode.STT_STOP_CAPTURE_SIGNAL,
            data,
        )

        if self._control_daemon_runtime_async(
            "stt",
            "unload",
            ModelType.STT,
        ):
            return
        # STT unload now handled exclusively by daemon

    def on_stt_process_audio_signal(self, data):
        """Forward captured audio to daemon for transcription."""
        self.add_to_queue({"data": data, "request_type": "stt_process"})

    def _process_stt_through_daemon(self, data: dict) -> None:
        """Send captured audio to the daemon for STT transcription."""
        import threading

        def _transcribe():
            try:
                audio_bytes = data.get("audio_bytes")
                if not audio_bytes:
                    self.logger.warning(
                        "STT process: no audio_bytes in data"
                    )
                    return
                client = self._daemon_client()
                if client is None:
                    self.logger.error(
                        "STT process: daemon unavailable"
                    )
                    return
                result = client.transcribe_audio(audio_bytes)
                text = result.get("text", "")
                if text and self.logger:
                    self.logger.info(
                        f"STT transcription result: {text[:100]}..."
                    )
            except Exception as exc:
                self.logger.error(
                    f"STT transcription failed: {exc}"
                )

        threading.Thread(target=_transcribe, daemon=True).start()

    def on_interrupt_process_signal(self, data):
        # LLM interrupt now handled exclusively by the daemon

        # Interrupt TTS generation
        # TTS synthesis now handled exclusively by daemon

        if self._tts_vocalizer_worker is not None:
            self.tts_vocalizer_worker.on_interrupt_process_signal(data)

    def on_unblock_tts_generator_signal(self, data):
        callback_handled = False
        
        # TTS synthesis now handled exclusively by daemon

        if self._tts_vocalizer_worker is not None:
            self.tts_vocalizer_worker.on_unblock_tts_generator_signal(data)
            callback_handled = True

        # If no TTS workers handled this, still invoke the callback
        # This ensures STT audio capture works even when TTS is disabled
        if not callback_handled and data is not None:
            callback = data.get("callback", None)
            if callback is not None:
                callback()

    def on_disable_tts_signal(self, data):
        from airunner.enums import ModelType

        self._stop_tts_activity_immediately()

        if self._control_daemon_runtime_async(
            "tts",
            "unload",
            ModelType.TTS,
        ):
            return
        # TTS disable now handled exclusively by daemon

    @staticmethod
    def _queue_tts_worker_message(worker, message: dict) -> None:
        """Send one TTS control message through the worker queue."""
        add_to_queue = getattr(worker, "add_to_queue", None)
        if callable(add_to_queue):
            add_to_queue(message)

    def _stop_tts_activity_immediately(self) -> None:
        """Stop queued TTS playback before daemon unload completes."""
        # TTS generator removed; daemon handles TTS synthesis
        generator = None
        if generator is not None:
            self._queue_tts_worker_message(
                generator,
                {
                    "_message_type": "interrupt",
                    "data": {},
                    "options": {"empty_queue": True},
                },
            )

        vocalizer = getattr(self, "_tts_vocalizer_worker", None)
        if vocalizer is not None:
            self._queue_tts_worker_message(
                vocalizer,
                {
                    "_message_type": "interrupt",
                    "data": {},
                    "options": {"empty_queue": True},
                },
            )

    def on_llm_text_streamed_signal(self, data):
        if data and data.get("_skip_worker_manager_tts"):
            return
        worker = self._stream_tts_worker()
        if worker is not None:
            worker.on_llm_text_streamed_signal(data)

    def on_llm_thinking_signal(self, data):
        if data and data.get("_skip_worker_manager_tts"):
            return
        worker = self._stream_tts_worker()
        if worker is not None:
            worker.on_llm_thinking_signal(data)

    def _stream_tts_worker(self):
        """Return the TTS worker only for GUI-owned streamed chat speech."""
        if self._current_gui_api() is None:
            return None
        return None  # TTS generator removed; daemon handles TTS

    def _reload_tts_model_manager(self, data):
        from airunner.enums import ModelType

        if getattr(self.application_settings, "tts_enabled", False):
            if self._control_daemon_runtime_async(
                "tts",
                "load",
                ModelType.TTS,
                route_metadata=self._tts_runtime_route_metadata(),
            ):
                return
        # TTS model reload now handled exclusively by daemon

    def on_application_settings_changed_signal(self, data):
        self._refresh_daemon_tts_for_reference_speaker_change(data)

        # TTS settings change now handled exclusively by daemon

        if self._tts_vocalizer_worker is not None:
            self.tts_vocalizer_worker.on_application_settings_changed_signal(
                data
            )

    def _refresh_daemon_tts_for_reference_speaker_change(self, data) -> None:
        """Restart sidecar-backed TTS after one reference-speaker change."""
        from airunner.enums import ModelType, TTSModel

        if self._daemon_client() is None:
            return
        if not getattr(self.application_settings, "tts_enabled", False):
            return
        if not isinstance(data, dict):
            return
        if data.get("setting_name") != "openvoice_settings":
            return
        if data.get("column_name") != "reference_speaker_path":
            return
        if self.chatbot_voice_model_type != TTSModel.OPENVOICE:
            return

        self._control_daemon_runtime_async(
            "tts",
            "unload",
            ModelType.TTS,
            before_request=self._stop_tts_activity_immediately,
            after_success=lambda: self._control_daemon_runtime_async(
                "tts",
                "load",
                ModelType.TTS,
                route_metadata=self._tts_runtime_route_metadata(),
            ),
        )

    def on_add_to_queue_signal(self, data):
        # TTS queue now handled exclusively by daemon
        pass

    def on_playback_device_changed_signal(self, data):
        if self._tts_vocalizer_worker is not None:
            self.tts_vocalizer_worker.on_playback_device_changed_signal(data)

    def on_image_exported_signal(self, data):
        # self.api.art.unload()
        pass

    def on_start_huggingface_download_signal(self, data: dict):
        """Handle START_HUGGINGFACE_DOWNLOAD signal for generic queued downloads.

        This signal is emitted when model managers detect missing model files
        and need to trigger a download. Uses the same download infrastructure
        as LLM and Art models.

        Args:
            data: Signal data dictionary containing:
                - repo_id: HuggingFace repository ID
                - model_path: Local path to save the model
                - model_type: Type of model (stt, tts_openvoice)
                - callback: Optional callback to invoke after download completes
        """
        from PySide6.QtWidgets import QApplication, QMessageBox
        from airunner.components.llm.gui.windows.huggingface_download_dialog import (
            HuggingFaceDownloadDialog,
        )
        
        # Check if HuggingFace downloads are allowed
        from airunner.components.application.gui.dialogs.privacy_consent_dialog import (
            is_huggingface_allowed,
        )
        if not is_huggingface_allowed():
            if self.logger:
                self.logger.info("HuggingFace downloads disabled by privacy settings")
            main_window = self._get_main_window()
            if main_window:
                QMessageBox.warning(
                    main_window,
                    "Downloads Disabled",
                    "HuggingFace downloads are disabled in privacy settings.\n\n"
                    "You can enable them in Preferences → Privacy & Security → External Services."
                )
            return

        repo_id = data.get("repo_id", "")
        model_path = data.get("model_path", "")
        model_type = data.get("model_type", "")
        version = data.get("version")
        pipeline_action = data.get("pipeline_action")
        callback = data.get("callback")

        if not repo_id:
            if self.logger:
                self.logger.error("No repo_id provided in download request")
            return

        if self.logger:
            self.logger.info(
                f"Starting HuggingFace download for {model_type}: {repo_id}"
            )

        # Get main window for dialog parent
        main_window = self._get_main_window()

        if main_window:
            try:
                # Close any existing download dialog
                if hasattr(self, "_download_dialog") and self._download_dialog:
                    self._download_dialog.close()
                    self._download_dialog = None

                # Create download dialog
                model_name = repo_id.split("/")[-1] if "/" in repo_id else repo_id
                self._download_dialog = HuggingFaceDownloadDialog(
                    parent=main_window,
                    model_name=f"{model_name} ({model_type.upper()})",
                    model_path=model_path,
                )

                # Store the callback for after download completes
                self._pending_download_callback = callback

                # Connect dialog to download worker signals
                self.huggingface_download_worker.register(
                    SignalCode.UPDATE_DOWNLOAD_LOG,
                    self._download_dialog.on_log_updated,
                )
                self.huggingface_download_worker.register(
                    SignalCode.UPDATE_DOWNLOAD_PROGRESS,
                    self._download_dialog.on_progress_updated,
                )
                self.huggingface_download_worker.register(
                    SignalCode.UPDATE_FILE_DOWNLOAD_PROGRESS,
                    self._download_dialog.on_file_progress_updated,
                )
                self.huggingface_download_worker.register(
                    SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
                    self._on_stt_tts_download_complete,
                )
                self.huggingface_download_worker.register(
                    SignalCode.HUGGINGFACE_DOWNLOAD_FAILED,
                    self._download_dialog.on_download_failed,
                )

                # Show the dialog
                self._download_dialog.show()
                self._download_dialog.raise_()
                self._download_dialog.activateWindow()

                if self.logger:
                    self.logger.info(
                        "Download dialog shown for STT/TTS model"
                    )

            except Exception as e:
                if self.logger:
                    self.logger.error(
                        f"Error showing download dialog: {e}", exc_info=True
                    )
        else:
            if self.logger:
                self.logger.error(
                    "Unable to locate the main window; download dialog could not be displayed"
                )

        # Queue download request
        download_data = {
            "repo_id": repo_id,
            "model_type": model_type,
            "output_dir": model_path,
            "version": version,
            "pipeline_action": pipeline_action,
        }

        if self.logger:
            self.logger.info(
                "Queueing download request (%s)",
                summarize_mapping_keys(download_data, label="download"),
            )

        self.huggingface_download_worker.add_to_queue(download_data)

    def _on_stt_tts_download_complete(self, data: dict):
        """Handle completion of STT/TTS model download.

        Invokes the stored callback if one was provided.
        """
        if hasattr(self, "_download_dialog") and self._download_dialog:
            self._download_dialog.on_download_complete(data)

        # Invoke callback if provided
        if hasattr(self, "_pending_download_callback") and self._pending_download_callback:
            callback = self._pending_download_callback
            self._pending_download_callback = None
            try:
                callback()
            except Exception as e:
                if self.logger:
                    self.logger.error(
                        f"Error invoking download callback: {e}", exc_info=True
                    )

    def on_start_openvoice_zip_download_signal(self, data: dict):
        """Handle START_OPENVOICE_ZIP_DOWNLOAD signal for OpenVoice converter checkpoints.

        Uses the same download dialog as HuggingFace downloads.

        Args:
            data: Signal data dictionary containing:
                - callback: Optional callback to invoke after download completes
        """
        import os
        from PySide6.QtWidgets import QApplication
        from airunner.components.llm.gui.windows.huggingface_download_dialog import (
            HuggingFaceDownloadDialog,
        )

        callback = data.get("callback")
        
        # Target directory for extraction
        openvoice_dir = os.path.join(
            self.path_settings.tts_model_path,
            "openvoice",
        )
        
        if self.logger:
            self.logger.info("Starting OpenVoice ZIP download")

        # Get main window for dialog parent
        main_window = self._get_main_window()

        if main_window:
            try:
                # Close any existing download dialog
                if hasattr(self, "_download_dialog") and self._download_dialog:
                    self._download_dialog.close()
                    self._download_dialog = None

                # Create download dialog
                self._download_dialog = HuggingFaceDownloadDialog(
                    parent=main_window,
                    model_name="OpenVoice Converter Checkpoints",
                    model_path=openvoice_dir,
                )

                # Store the callback for after download completes
                self._pending_download_callback = callback

                # Connect dialog to download worker signals
                self.huggingface_download_worker.register(
                    SignalCode.UPDATE_DOWNLOAD_LOG,
                    self._download_dialog.on_log_updated,
                )
                self.huggingface_download_worker.register(
                    SignalCode.UPDATE_DOWNLOAD_PROGRESS,
                    self._download_dialog.on_progress_updated,
                )
                self.huggingface_download_worker.register(
                    SignalCode.UPDATE_FILE_DOWNLOAD_PROGRESS,
                    self._download_dialog.on_file_progress_updated,
                )
                self.huggingface_download_worker.register(
                    SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
                    self._on_stt_tts_download_complete,
                )
                self.huggingface_download_worker.register(
                    SignalCode.HUGGINGFACE_DOWNLOAD_FAILED,
                    self._download_dialog.on_download_failed,
                )

                # Show the dialog
                self._download_dialog.show()
                self._download_dialog.raise_()
                self._download_dialog.activateWindow()

                if self.logger:
                    self.logger.info(
                        "Download dialog shown for OpenVoice checkpoints"
                    )

            except Exception as e:
                if self.logger:
                    self.logger.error(
                        f"Error showing download dialog: {e}", exc_info=True
                    )
        else:
            if self.logger:
                self.logger.error(
                    "Unable to locate the main window; download dialog could not be displayed"
                )

        # Queue download request - use the openvoice_zip model type
        download_data = {
            "model_type": "openvoice_zip",
            "output_dir": openvoice_dir,
            "zip_url": "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/checkpoints_v2_0417.zip",
        }

        if self.logger:
            self.logger.info(
                "Queueing OpenVoice ZIP download request (%s)",
                summarize_mapping_keys(download_data, label="download"),
            )

        self.huggingface_download_worker.add_to_queue(download_data)

    def on_start_openvoice_batch_download_signal(self, data: dict):
        """Handle START_OPENVOICE_BATCH_DOWNLOAD signal.

        Shows a language selection dialog FIRST, then downloads all selected models
        (including converter ZIP and HuggingFace models) in a single batch.

        Args:
            data: Signal data containing:
                - needs_converter: Whether the converter ZIP needs download
                - missing_core_models: List of core model IDs that need download
                - missing_languages: List of language keys that need download
                - callback: Callback to invoke after all downloads complete
        """
        import os
        from PySide6.QtCore import QThread
        from PySide6.QtWidgets import QMessageBox, QDialog
        from airunner.components.tts.gui.dialogs.openvoice_language_dialog import (
            OpenVoiceLanguageDialog,
        )
        from airunner_services.bootstrap.openvoice_languages import (
            OPENVOICE_CORE_MODELS,
            OPENVOICE_LANGUAGE_MODELS,
        )
        from airunner.components.llm.gui.windows.huggingface_download_dialog import (
            HuggingFaceDownloadDialog,
        )

        needs_converter = data.get("needs_converter", False)
        missing_core_models = data.get("missing_core_models", [])
        missing_languages = data.get("missing_languages", [])
        callback = data.get("callback")

        if self.logger:
            self.logger.info(
                f"OpenVoice batch download requested: converter={needs_converter}, "
                f"{len(missing_core_models)} core models, {len(missing_languages)} languages"
            )

        # Clean up any previous batch download state and ALL other download handlers
        # that might interfere with the batch download
        try:
            self.huggingface_download_worker.unregister(
                SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
                self._on_openvoice_batch_download_complete,
            )
        except Exception:
            pass
        # Unregister the STT/TTS download complete handler if it exists
        try:
            self.huggingface_download_worker.unregister(
                SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
                self._on_stt_tts_download_complete,
            )
        except Exception:
            pass
        # Unregister any direct dialog handlers from other download flows
        if hasattr(self, "_download_dialog") and self._download_dialog:
            try:
                self.huggingface_download_worker.unregister(
                    SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
                    self._download_dialog.on_download_complete,
                )
            except Exception:
                pass
        self._openvoice_remaining_downloads = None
        self._openvoice_download_callback = None
        self._pending_download_callback = None  # Clear any pending STT/TTS callback

        main_window = self._get_main_window()
        ui_thread = None
        if main_window is not None and hasattr(main_window, "thread"):
            ui_thread = main_window.thread()
        ui_available = (
            main_window is not None and ui_thread == QThread.currentThread()
        )

        if ui_available:
            dialog = OpenVoiceLanguageDialog(
                parent=main_window,
                missing_languages=missing_languages,
            )
            result = dialog.exec()

            if result != QDialog.Accepted:
                if self.logger:
                    self.logger.info(
                        "User cancelled OpenVoice language selection"
                    )
                return

            selected_languages = dialog.get_selected_languages()
        else:
            selected_languages = self._default_openvoice_languages(
                missing_languages,
            )
            if self.logger:
                self.logger.info(
                    "OpenVoice download running without language dialog; "
                    "selected=%s",
                    selected_languages,
                )

        # Build list of all models to download
        models_to_download = list(missing_core_models)  # Always download core models
        
        # Add language-specific models for selected languages
        for lang_key in selected_languages:
            if lang_key in OPENVOICE_LANGUAGE_MODELS:
                lang_info = OPENVOICE_LANGUAGE_MODELS[lang_key]
                for model_id in lang_info["models"]:
                    if model_id not in models_to_download:
                        models_to_download.append(model_id)

        # Count total downloads (including converter if needed)
        total_downloads = len(models_to_download)
        if needs_converter:
            total_downloads += 1

        if total_downloads == 0:
            if self.logger:
                self.logger.info("No OpenVoice models to download")
            # Still invoke callback since download check passed
            if callback:
                callback()
            return

        if self.logger:
            self.logger.info(
                f"Downloading {total_downloads} OpenVoice items: "
                f"converter={needs_converter}, models={models_to_download}"
            )

        # Create the progress dialog only when we are on the UI thread.
        try:
            # Track remaining downloads and callback
            self._openvoice_remaining_downloads = total_downloads
            self._openvoice_download_callback = callback
            self.huggingface_download_worker.register(
                SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
                self._on_openvoice_batch_download_complete,
            )

            if ui_available:
                if hasattr(self, "_download_dialog") and self._download_dialog:
                    try:
                        self.huggingface_download_worker.unregister(
                            SignalCode.UPDATE_DOWNLOAD_LOG,
                            self._download_dialog.on_log_updated,
                        )
                    except Exception:
                        pass
                    try:
                        self.huggingface_download_worker.unregister(
                            SignalCode.UPDATE_DOWNLOAD_PROGRESS,
                            self._download_dialog.on_progress_updated,
                        )
                    except Exception:
                        pass
                    try:
                        self.huggingface_download_worker.unregister(
                            SignalCode.UPDATE_FILE_DOWNLOAD_PROGRESS,
                            self._download_dialog.on_file_progress_updated,
                        )
                    except Exception:
                        pass
                    try:
                        self.huggingface_download_worker.unregister(
                            SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
                            self._download_dialog.on_download_complete,
                        )
                    except Exception:
                        pass
                    try:
                        self.huggingface_download_worker.unregister(
                            SignalCode.HUGGINGFACE_DOWNLOAD_FAILED,
                            self._download_dialog.on_download_failed,
                        )
                    except Exception:
                        pass
                    self._download_dialog.close()
                    self._download_dialog = None

                self._download_dialog = HuggingFaceDownloadDialog(
                    parent=main_window,
                    model_name=f"OpenVoice TTS ({total_downloads} items)",
                    model_path=os.path.join(
                        self.path_settings.base_path, "text/models/tts"
                    ),
                    batch_mode=True,
                )
                self.huggingface_download_worker.register(
                    SignalCode.UPDATE_DOWNLOAD_LOG,
                    self._download_dialog.on_log_updated,
                )
                self.huggingface_download_worker.register(
                    SignalCode.UPDATE_DOWNLOAD_PROGRESS,
                    self._download_dialog.on_progress_updated,
                )
                self.huggingface_download_worker.register(
                    SignalCode.UPDATE_FILE_DOWNLOAD_PROGRESS,
                    self._download_dialog.on_file_progress_updated,
                )
                self.huggingface_download_worker.register(
                    SignalCode.HUGGINGFACE_DOWNLOAD_FAILED,
                    self._download_dialog.on_download_failed,
                )
                self._download_dialog.show()
                self._download_dialog.raise_()
                self._download_dialog.activateWindow()
            else:
                self._download_dialog = None

            # Queue converter ZIP download first if needed
            if needs_converter:
                openvoice_dir = os.path.join(
                    self.path_settings.base_path, "text/models/tts/openvoice"
                )
                os.makedirs(openvoice_dir, exist_ok=True)
                
                download_data = {
                    "model_type": "openvoice_zip",
                    "output_dir": openvoice_dir,
                    "zip_url": "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/checkpoints_v2_0417.zip",
                }
                if self.logger:
                    self.logger.info(f"Queueing OpenVoice converter ZIP download")
                self.huggingface_download_worker.add_to_queue(download_data)

            # Queue all HuggingFace model downloads
            for model_id in models_to_download:
                model_path = os.path.join(
                    self.path_settings.base_path,
                    "text/models/tts",
                    model_id,
                )
                download_data = {
                    "repo_id": model_id,
                    "model_type": "tts_openvoice",
                    "output_dir": model_path,
                }
                self.huggingface_download_worker.add_to_queue(download_data)

        except Exception as e:
            if self.logger:
                self.logger.error(
                    f"Error setting up OpenVoice batch download: {e}", exc_info=True
                )

    def _default_openvoice_languages(
        self,
        missing_languages: list[str],
    ) -> list[str]:
        """Return one best-effort language list for non-blocking bootstrap."""
        language_name_map = {
            "FR": "French",
            "ES": "Spanish",
            "SP": "Spanish",
            "JP": "Japanese",
            "ZH": "Chinese",
            "ZH_MIX_EN": "Chinese",
            "KR": "Korean",
        }

        configured_language = getattr(
            self.language_settings,
            "bot_language",
            None,
        ) or getattr(self.openvoice_settings, "language", None)

        if (
            configured_language is None
            and getattr(self.application_settings, "use_detected_language", False)
        ):
            configured_language = getattr(
                self.application_settings,
                "detected_language",
                None,
            )

        language_key = language_name_map.get(
            str(configured_language or "").upper()
        )
        if language_key and language_key in missing_languages:
            return [language_key]
        return []

    def _on_openvoice_batch_download_complete(self, data: dict):
        """Handle completion of a single model in the OpenVoice batch download."""
        if not hasattr(self, "_openvoice_remaining_downloads") or self._openvoice_remaining_downloads is None:
            # Not in a batch download, ignore
            return
            
        self._openvoice_remaining_downloads -= 1
        
        if self.logger:
            self.logger.info(
                f"OpenVoice model download complete, {self._openvoice_remaining_downloads} remaining"
            )
        
        if self._openvoice_remaining_downloads <= 0:
            # All downloads complete - unregister all handlers
            try:
                self.huggingface_download_worker.unregister(
                    SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
                    self._on_openvoice_batch_download_complete,
                )
            except Exception:
                pass
            
            # Unregister dialog signal handlers
            if hasattr(self, "_download_dialog") and self._download_dialog:
                try:
                    self.huggingface_download_worker.unregister(
                        SignalCode.UPDATE_DOWNLOAD_LOG,
                        self._download_dialog.on_log_updated,
                    )
                except Exception:
                    pass
                try:
                    self.huggingface_download_worker.unregister(
                        SignalCode.UPDATE_DOWNLOAD_PROGRESS,
                        self._download_dialog.on_progress_updated,
                    )
                except Exception:
                    pass
                try:
                    self.huggingface_download_worker.unregister(
                        SignalCode.UPDATE_FILE_DOWNLOAD_PROGRESS,
                        self._download_dialog.on_file_progress_updated,
                    )
                except Exception:
                    pass
                try:
                    self.huggingface_download_worker.unregister(
                        SignalCode.HUGGINGFACE_DOWNLOAD_FAILED,
                        self._download_dialog.on_download_failed,
                    )
                except Exception:
                    pass
                
                # Notify dialog that all downloads are complete, then close it
                self._download_dialog.on_download_complete(data)
                # Use QTimer to close after a brief delay so user sees the completion message
                from PySide6.QtCore import QTimer
                dialog = self._download_dialog
                QTimer.singleShot(1500, dialog.accept)
                self._download_dialog = None
            
            # Clear tracking state
            self._openvoice_remaining_downloads = None
            
            # Invoke callback
            if hasattr(self, "_openvoice_download_callback") and self._openvoice_download_callback:
                callback = self._openvoice_download_callback
                self._openvoice_download_callback = None
                try:
                    callback()
                except Exception as e:
                    if self.logger:
                        self.logger.error(
                            f"Error invoking OpenVoice download callback: {e}",
                            exc_info=True
                        )
