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


_OPTIONAL_LOAD_REQUEST_TIMEOUT_SECONDS = 5.0
_OPTIONAL_UNLOAD_REQUEST_TIMEOUT_SECONDS = 2.0
_OPTIONAL_UNLOAD_WAIT_TIMEOUT_SECONDS = 5.0
_TTS_LOAD_WAIT_TIMEOUT_SECONDS = 180.0
_STREAM_TTS_WORKER_SLEEP_MS = 1


class WorkerManager(Worker):
    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.REMOVE_BACKGROUND: self.on_remove_background_signal,
            SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL: self.on_llm_request_signal,
            SignalCode.START_AUTO_IMAGE_GENERATION_SIGNAL: self.on_start_auto_image_generation_signal,
            SignalCode.DO_GENERATE_SIGNAL: self.on_do_generate_signal,
            SignalCode.TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL: self.on_tts_generator_worker_add_to_stream_signal,
            SignalCode.TTS_ENABLE_SIGNAL: self.on_enable_tts_signal,
            SignalCode.STT_LOAD_SIGNAL: self.on_stt_load_signal,
            SignalCode.STT_START_CAPTURE_SIGNAL: self.on_stt_start_capture_signal,
            SignalCode.ART_MODEL_DOWNLOAD_REQUIRED: self.on_art_model_download_required,
            SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE: self.on_huggingface_download_complete,
            SignalCode.SD_UNLOAD_SIGNAL: self.on_unload_art_signal,
            SignalCode.RMBG_UNLOAD_SIGNAL: self.on_unload_rmbg_signal,
            SignalCode.SD_CANCEL_SIGNAL: self.on_sd_cancel_signal,
            SignalCode.STOP_AUTO_IMAGE_GENERATION_SIGNAL: self.on_stop_auto_image_generation_signal,
            SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL: self.on_interrupt_image_generation_signal,
            SignalCode.CHANGE_SCHEDULER_SIGNAL: self.on_change_scheduler_signal,
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL: self.on_model_status_changed_signal,
            SignalCode.SD_LOAD_SIGNAL: self.on_load_art_signal,
            SignalCode.SD_ART_MODEL_CHANGED: self.on_art_model_changed,
            SignalCode.CONTROLNET_LOAD_SIGNAL: self.on_load_controlnet_signal,
            SignalCode.CONTROLNET_UNLOAD_SIGNAL: self.on_unload_controlnet_signal,
            SignalCode.SAFETY_CHECKER_LOAD_SIGNAL: self.on_safety_checker_load_signal,
            SignalCode.SAFETY_CHECKER_UNLOAD_SIGNAL: self.on_safety_checker_unload_signal,
            SignalCode.INPUT_IMAGE_SETTINGS_CHANGED: self.on_input_image_settings_changed_signal,
            SignalCode.LORA_UPDATE_SIGNAL: self.on_update_lora_signal,
            SignalCode.EMBEDDING_UPDATE_SIGNAL: self.on_update_embeddings_signal,
            SignalCode.EMBEDDING_DELETE_MISSING_SIGNAL: self.delete_missing_embeddings,
            SignalCode.LLM_UNLOAD_SIGNAL: self.on_llm_on_unload_signal,
            SignalCode.LLM_LOAD_SIGNAL: self.on_llm_load_model_signal,
            SignalCode.LLM_MODEL_CHANGED: self.on_llm_model_changed_signal,
            SignalCode.LLM_MODEL_DOWNLOAD_REQUIRED: self.on_llm_model_download_required_signal,
            SignalCode.LLM_CONVERT_TO_GGUF_SIGNAL: self.on_llm_convert_to_gguf_signal,
            SignalCode.RAG_RELOAD_INDEX_SIGNAL: self.on_llm_reload_rag_index_signal,
            SignalCode.RAG_INDEX_ALL_DOCUMENTS: self.on_rag_index_all_documents_signal,
            SignalCode.RAG_INDEX_SELECTED_DOCUMENTS: self.on_rag_index_selected_documents_signal,
            SignalCode.RAG_INDEX_CANCEL: self.on_rag_index_cancel_signal,
            SignalCode.RAG_LOAD_DOCUMENTS: self.on_rag_load_documents_signal,
            SignalCode.INDEX_DOCUMENT: self.on_index_document_signal,
            SignalCode.LLM_START_QUANTIZATION: self.on_llm_start_quantization_signal,
            SignalCode.LLM_CLEAR_HISTORY_SIGNAL: self.on_llm_clear_history_signal,
            SignalCode.ADD_CHATBOT_MESSAGE_SIGNAL: self.on_llm_add_chatbot_response_to_history,
            SignalCode.LOAD_CONVERSATION: self.on_llm_load_conversation,
            SignalCode.INTERRUPT_PROCESS_SIGNAL: self.on_interrupt_process_signal,
            SignalCode.QUIT_APPLICATION: self.on_quit_application_signal,
            SignalCode.CONVERSATION_DELETED: self.on_conversation_deleted_signal,
            SignalCode.SECTION_CHANGED: self.on_section_changed_signal,
            SignalCode.GENERATE_MASK: self.on_generate_mask_signal,
            SignalCode.AUDIO_CAPTURE_WORKER_RESPONSE_SIGNAL: self.on_stt_process_audio_signal,
            SignalCode.STT_STOP_CAPTURE_SIGNAL: self.on_stt_stop_capture_signal,
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL: self.on_model_status_changed_signal,
            SignalCode.RECORDING_DEVICE_CHANGED: self.on_recording_device_changed_signal,
            SignalCode.STT_UNLOAD_SIGNAL: self.on_stt_unload_signal,
            SignalCode.UNBLOCK_TTS_GENERATOR_SIGNAL: self.on_unblock_tts_generator_signal,
            SignalCode.TTS_DISABLE_SIGNAL: self.on_disable_tts_signal,
            SignalCode.LLM_THINKING_SIGNAL: self.on_llm_thinking_signal,
            SignalCode.LLM_TEXT_STREAMED_SIGNAL: self.on_llm_text_streamed_signal,
            SignalCode.TTS_MODEL_CHANGED: self._reload_tts_model_manager,
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: self.on_application_settings_changed_signal,
            SignalCode.TTS_QUEUE_SIGNAL: self.on_add_to_queue_signal,
            SignalCode.PLAYBACK_DEVICE_CHANGED: self.on_playback_device_changed_signal,
            SignalCode.IMAGE_EXPORTED: self.on_image_exported_signal,
            SignalCode.START_HUGGINGFACE_DOWNLOAD: self.on_start_huggingface_download_signal,
            SignalCode.START_OPENVOICE_BATCH_DOWNLOAD: self.on_start_openvoice_batch_download_signal,
            SignalCode.APPLICATION_MAIN_WINDOW_LOADED_SIGNAL: self.on_application_main_window_loaded_signal,
        }
        super().__init__()
        self._mask_generator_worker = None
        self._sd_worker = None
        self._safety_checker_worker = None
        self._pending_generation_request = None
        self._download_dialog = (
            None  # Store dialog reference to prevent garbage collection
        )
        self._stt_audio_capture_worker = None
        self._stt_audio_processor_worker = None
        self._tts_generator_worker = None
        self._tts_generator_worker_import_error = None
        self._tts_vocalizer_worker = None
        self._llm_generate_worker = None
        self._document_worker = None
        self._huggingface_download_worker = None
        self._image_export_worker = None
        self._model_scanner_worker = None
        self._background_removal_worker = None
        self._art_runtime_prewarm_started = False
        self._tts_runtime_prewarm_started = False
        if self.logger:
            self.logger.debug(
                f"WorkerManager initialized. Mediator ID: {id(self.mediator)}"
            )

        self.model_scanner_worker.add_to_queue("scan_for_models")

    @property
    def background_removal_worker(self):
        if self._background_removal_worker is None:
            from airunner.components.art.workers.background_removal_worker import (
                BackgroundRemovalWorker,
            )

            self._background_removal_worker = create_worker(
                BackgroundRemovalWorker
            )
        return self._background_removal_worker

    def on_remove_background_signal(self, _data: Dict):
        """Queue background removal for the selected canvas layer."""
        from PySide6.QtWidgets import QMessageBox

        layer_id = self._get_current_selected_layer_id()
        if layer_id is None:
            try:
                from airunner.components.art.data.canvas_layer import (
                    CanvasLayer,
                )

                layers = CanvasLayer.objects.order_by("order").all() or []
                if layers:
                    layer_id = getattr(layers[0], "id", None)
            except Exception:
                layer_id = None

        image_binary = None
        try:
            from airunner.components.art.data.drawingpad_settings import (
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

        self.background_removal_worker.add_to_queue(
            {
                "action": "remove_background",
                "data": {
                    "layer_id": layer_id,
                    "image": image_binary,
                },
            }
        )

    def on_unload_rmbg_signal(self, data: Dict):
        """Queue RMBG unloading for the background-removal worker."""
        self.background_removal_worker.add_to_queue(
            {
                "action": "unload",
                "data": data,
            }
        )

    def handle_message(self, message: Dict):
        if self.logger:
            self.logger.debug(
                f"WorkerManager::handle_message CALLED with request_type={message.get('request_type')}"
            )
        data = message.get("data", {})
        request_type = message.get("request_type")
        try:
            if request_type == "llm_generate":
                if self.llm_generate_worker is not None:
                    self.llm_generate_worker.on_llm_request_signal(data)
            elif request_type == "image_auto_generate":
                if self.sd_worker is not None:
                    self.sd_worker.on_start_auto_image_generation_signal(data)
            elif request_type == "image_generate":
                # Intercept image generation to ensure safety checker is ready
                self._handle_image_generation_request(data)
            elif request_type == "tts_generate":
                if self.tts_vocalizer_worker is not None:
                    self.tts_vocalizer_worker.on_tts_generator_worker_add_to_stream_signal(
                        data
                    )
            elif request_type == "tts_enable":
                if self.tts_generator_worker is not None:
                    self.tts_generator_worker.on_enable_tts_signal(data)
            elif request_type == "stt_load":
                if self.stt_audio_processor_worker is not None:
                    self.stt_audio_processor_worker.on_stt_load_signal(data)
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

    @property
    def safety_checker_worker(self):
        if self._safety_checker_worker is None:
            from airunner.components.art.workers.safety_checker_worker import (
                SafetyCheckerWorker,
            )

            self._safety_checker_worker = create_worker(SafetyCheckerWorker)
        return self._safety_checker_worker

    @property
    def mask_generator_worker(self):
        if self._mask_generator_worker is None:
            from airunner.components.art.workers.mask_generator_worker import (
                MaskGeneratorWorker,
            )

            self._mask_generator_worker = create_worker(MaskGeneratorWorker)
        return self._mask_generator_worker

    @property
    def sd_worker(self):
        if self._sd_worker is None:
            from airunner.components.art.workers.sd_worker import SDWorker

            self._sd_worker = create_worker(
                SDWorker, image_export_worker=self.image_export_worker
            )
            # reference self.mask_generator_worker to ensure it is created
            _ = self.mask_generator_worker
        return self._sd_worker

    @property
    def stt_audio_capture_worker(self):
        if self._stt_audio_capture_worker is None:
            from airunner.components.stt.workers.audio_capture_worker import (
                AudioCaptureWorker,
            )

            self._stt_audio_capture_worker = create_worker(AudioCaptureWorker)
        return self._stt_audio_capture_worker

    @property
    def stt_audio_processor_worker(self):
        if self._stt_audio_processor_worker is None:
            from airunner.components.stt.workers.audio_processor_worker import (
                AudioProcessorWorker,
            )

            self._stt_audio_processor_worker = create_worker(
                AudioProcessorWorker
            )
        return self._stt_audio_processor_worker

    @property
    def tts_generator_worker(self):
        if self._tts_generator_worker is None:
            try:
                from airunner.components.tts.workers.tts_generator_worker import (
                    TTSGeneratorWorker,
                )
            except ModuleNotFoundError as exc:
                missing_module = getattr(exc, "name", str(exc))
                if self._tts_generator_worker_import_error != missing_module:
                    self._tts_generator_worker_import_error = missing_module
                    if self.logger:
                        self.logger.warning(
                            "TTS generator worker unavailable because optional dependency %s is missing",
                            missing_module,
                            exc_info=True,
                        )
                return None

            self._tts_generator_worker = create_worker(
                TTSGeneratorWorker,
                sleep_time_in_ms=_STREAM_TTS_WORKER_SLEEP_MS,
            )
        return self._tts_generator_worker

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

    def on_llm_request_signal(self, data: Dict):
        if self.logger:
            self.logger.info(
                f"WorkerManager::on_llm_request_signal CALLED with data keys: {list(data.keys())}"
            )

        worker = self.llm_generate_worker
        if worker is not None:
            if self.logger:
                self.logger.info(
                    "WorkerManager::on_llm_request_signal forwarding directly to llm_generate_worker"
                )
            worker.on_llm_request_signal(data)
            return

        self.add_to_queue(
            {
                "data": data,
                "request_type": "llm_generate",
            }
        )

    def on_start_auto_image_generation_signal(self, data: Dict):
        self.add_to_queue(
            {
                "data": data,
                "request_type": "image_auto_generate",
            }
        )

    def on_do_generate_signal(self, data: Dict):
        self.add_to_queue(
            {
                "data": data,
                "request_type": "image_generate",
            }
        )

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
        worker = self.tts_generator_worker
        if worker is not None:
            worker.add_to_queue(
                {
                    "_message_type": "tts_enable",
                    "data": data,
                }
            )

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
        self.stt_audio_processor_worker.add_to_queue(
            {
                "_message_type": "stt_load",
                "data": data,
            }
        )

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
            self.logger.info(f"Queueing download request: {download_data}")

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
        """Return one local LLM worker instance when available."""
        worker = getattr(self, "_llm_generate_worker", None)
        if worker is not None:
            return worker
        if not create:
            return None
        try:
            return self.llm_generate_worker
        except Exception:
            return None

    def _local_llm_should_handle_unload(self) -> bool:
        """Return True when the live LLM appears to be owned locally."""
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

    def _start_art_runtime_prewarm(self) -> None:
        """Start the art sidecar in the background after the GUI loads."""
        if self._art_runtime_prewarm_started:
            return
        if self._daemon_client() is None:
            return
        self._art_runtime_prewarm_started = True
        thread = threading.Thread(
            target=self._prewarm_art_runtime,
            name="airunner-art-prewarm",
            daemon=True,
        )
        thread.start()

    def _prewarm_art_runtime(self) -> None:
        """Ensure the art runtime is already running before first generate."""
        client = self._daemon_client()
        if client is None:
            self._art_runtime_prewarm_started = False
            return
        try:
            client.load_runtime(
                "art",
                deployment_mode="sidecar",
                auto_start=False,
            )
            return
        except RuntimeError as exc:
            if self.logger:
                self.logger.debug("Art runtime prewarm skipped: %s", exc)
        self._art_runtime_prewarm_started = False

    def _start_tts_runtime_prewarm(self) -> None:
        """Start the TTS sidecar before the first spoken reply."""
        if self._tts_runtime_prewarm_started:
            return
        if self._daemon_client() is None:
            return
        if callable(getattr(self.logger, "info", None)):
            self.logger.info("Starting TTS runtime prewarm")
        self._tts_runtime_prewarm_started = True
        thread = threading.Thread(
            target=self._prewarm_tts_runtime,
            name="airunner-tts-prewarm",
            daemon=True,
        )
        thread.start()

    def _prewarm_tts_runtime(self) -> None:
        """Ensure sidecar-backed TTS is loaded before synthesis begins."""
        from airunner.enums import ModelType

        client = self._daemon_client()
        if client is None:
            self._tts_runtime_prewarm_started = False
            return
        try:
            client.load_runtime(
                "tts",
                deployment_mode="sidecar",
                metadata=self._tts_runtime_route_metadata(),
                auto_start=False,
                timeout_seconds=_OPTIONAL_LOAD_REQUEST_TIMEOUT_SECONDS,
            )
            ready = client.wait_runtime_ready(
                "tts",
                loaded=True,
                deployment_mode="sidecar",
                auto_start=False,
                timeout_seconds=self._runtime_wait_timeout_seconds(
                    "load",
                    ModelType.TTS,
                ),
            )
            if ready:
                if callable(getattr(self.logger, "info", None)):
                    self.logger.info("TTS runtime prewarm completed")
                return
        except RuntimeError as exc:
            if self.logger:
                self.logger.debug("TTS runtime prewarm skipped: %s", exc)
        self._tts_runtime_prewarm_started = False

    @staticmethod
    def _is_optional_runtime_unload(action: str, model_type) -> bool:
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

        worker = getattr(self, "_llm_generate_worker", None)
        if worker is None:
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
        auto_start = loaded
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
                auto_start=auto_start,
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
            auto_start=auto_start,
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
            client.unload_local_llm(auto_start=False)
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
            auto_start=False,
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
            if self._safety_checker_worker is not None:
                self._safety_checker_worker.add_to_queue({"action": "load", "data": {}})
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
        if self._llm_generate_worker is not None and model_type not in non_llm_types:
            self.llm_generate_worker.add_to_queue({
                "_message_type": "download_complete",
                "data": data
            })

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
        """Cancel one active daemon art job before unloading its runtime."""
        worker = getattr(self, "_sd_worker", None)
        if worker is None:
            return False

        request_unload = getattr(
            worker,
            "request_daemon_unload_after_cancel",
            None,
        )
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
        if self._sd_worker is not None:

            def callback(res: Dict):
                del self._sd_worker
                self._sd_worker = None

            data["callback"] = callback
            self.sd_worker.unload(data)

    def on_sd_cancel_signal(self, data):
        if self._sd_worker is not None:
            self.sd_worker.on_sd_cancel_signal(data)

    def on_stop_auto_image_generation_signal(self, data):
        if self._sd_worker is not None:
            self.sd_worker.on_stop_auto_image_generation_signal(data)

    def on_interrupt_image_generation_signal(self, data):
        if self._sd_worker is not None:
            self.sd_worker.on_interrupt_image_generation_signal(data)

    def on_change_scheduler_signal(self, data):
        if self._sd_worker is not None:
            self.sd_worker.on_change_scheduler_signal(data)

    def on_model_status_changed_signal(self, data):
        from airunner.enums import ModelStatus, ModelType

        model_type = data.get("model") or data.get("model_type")
        status = data.get("status")

        if model_type == ModelType.TTS:
            if status in (ModelStatus.LOADED, ModelStatus.READY):
                self._tts_runtime_prewarm_started = True
            elif status in (ModelStatus.UNLOADED, ModelStatus.FAILED):
                self._tts_runtime_prewarm_started = False

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
            from airunner.components.settings.data.application_settings import (
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

        if self._sd_worker is not None:
            self.sd_worker.on_model_status_changed_signal(data)
        if self._stt_audio_capture_worker is not None:
            self.stt_audio_capture_worker.on_model_status_changed_signal(data)

    def on_load_art_signal(self, data):
        if self._daemon_client() is not None:
            self._start_art_runtime_prewarm()
            return
        if self.sd_worker is not None:
            self.sd_worker.on_load_art_signal(data)

    def on_application_main_window_loaded_signal(self, _data=None):
        """Warm optional runtimes once the main window is ready."""
        self._start_art_runtime_prewarm()
        if not getattr(self.application_settings, "tts_enabled", False):
            return

        self.on_enable_tts_signal({"source": "startup"})

    def on_art_model_changed(self, data):
        self._start_art_runtime_prewarm()
        if self._sd_worker is not None:
            self.sd_worker.on_art_model_changed(data)

    def on_load_controlnet_signal(self, data):
        if self._sd_worker is not None:
            self.sd_worker.on_load_controlnet_signal(data)

    def on_unload_controlnet_signal(self, data):
        if self._sd_worker is not None:
            self.sd_worker.on_unload_controlnet_signal(data)

    def on_safety_checker_load_signal(self, data):
        # Ensure the worker is created and send load request through its queue
        # Using add_to_queue ensures thread-safe message passing
        self.safety_checker_worker.add_to_queue({"action": "load", "data": data})

    def on_safety_checker_unload_signal(self, data):
        # Trigger unloading if worker exists
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
        from airunner.components.settings.data.application_settings import (
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
        from airunner.components.settings.data.application_settings import (
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
        if self.sd_worker is not None:
            self.logger.debug("Calling sd_worker.on_do_generate_signal")
            self.sd_worker.on_do_generate_signal(data)
        else:
            self.logger.error("sd_worker is None, cannot proceed with generation")

    def on_input_image_settings_changed_signal(self, data):
        if self._sd_worker is not None:
            self.sd_worker.on_input_image_settings_changed_signal(data)

    def on_update_lora_signal(self, data):
        if self._sd_worker is not None:
            self.sd_worker.on_update_lora_signal(data)

    def on_update_embeddings_signal(self, data):
        if self._sd_worker is not None:
            self.sd_worker.on_update_embeddings_signal(data)

    def delete_missing_embeddings(self, data):
        if self._sd_worker is not None:
            self.sd_worker.delete_missing_embeddings(data)

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
        self.llm_generate_worker.add_to_queue(
            {
                "_message_type": "llm_load",
                "data": data,
            }
        )

    def _llm_model_change_requires_runtime_reload(self, data) -> bool:
        """Return True when a model-change notification should unload."""
        if not isinstance(data, dict):
            return False
        return bool(data.get("reload_runtime"))

    def on_llm_model_changed_signal(self, data):
        if not self._llm_model_change_requires_runtime_reload(data):
            return

        from airunner.enums import ModelType

        if self._control_daemon_runtime("llm", "unload", ModelType.LLM):
            return
        if self._llm_generate_worker is not None:
            self.llm_generate_worker.on_llm_model_changed_signal(data)

    def on_llm_model_download_required_signal(self, data):
        self.logger.info(f"WorkerManager received LLM_MODEL_DOWNLOAD_REQUIRED: {data}")
        if self._llm_generate_worker is not None:
            self.logger.info("Forwarding to llm_generate_worker")
            self.llm_generate_worker.on_llm_model_download_required_signal(
                data
            )
        else:
            # Handle download directly without LLM worker
            self.logger.info("LLM worker not available, handling download directly")
            self._handle_llm_download_directly(data)

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
            self.logger.info(f"Starting GGUF download: {repo_id}/{gguf_filename}")
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

    def on_llm_convert_to_gguf_signal(self, data):
        """Handle GGUF conversion request.
        
        Converts safetensors to GGUF format when no pre-quantized GGUF is available.
        
        Args:
            data: Dict with model_path, model_name, quantization
        """
        self.logger.info(f"WorkerManager received LLM_CONVERT_TO_GGUF_SIGNAL: {data}")
        
        from PySide6.QtWidgets import QApplication, QProgressDialog, QMessageBox
        from PySide6.QtCore import Qt
        from airunner.utils.model_optimizer import get_model_optimizer
        
        model_path = data.get("model_path", "")
        model_name = data.get("model_name", "Unknown Model")
        quantization = data.get("quantization", "Q4_K_M")
        
        # Get main window
        main_window = None
        app = QApplication.instance()
        for widget in app.topLevelWidgets():
            if widget.__class__.__name__ == "MainWindow":
                main_window = widget
                break
        
        if not main_window:
            self.logger.error("Cannot show conversion dialog - main window not found")
            return
        
        # Show progress dialog
        progress = QProgressDialog(
            f"Converting {model_name} to GGUF format...\n\n"
            "This may take several minutes depending on model size.",
            "Cancel",
            0, 0,
            main_window
        )
        progress.setWindowTitle("GGUF Conversion")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()
        QApplication.processEvents()
        
        try:
            optimizer = get_model_optimizer()
            
            # Check for conversion tools
            if not optimizer.has_llama_cpp_convert():
                progress.close()
                QMessageBox.critical(
                    main_window,
                    "Conversion Not Available",
                    "GGUF conversion requires llama.cpp tools.\n\n"
                    "Install with:\n"
                    "  pip install llama-cpp-python\n\n"
                    "Or clone llama.cpp and build convert tools."
                )
                return
            
            # Perform conversion
            success, gguf_path, error = optimizer.convert_to_gguf(
                model_path=model_path,
                quantization=quantization,
            )
            
            progress.close()
            
            if success:
                self.logger.info(f"GGUF conversion successful: {gguf_path}")
                QMessageBox.information(
                    main_window,
                    "Conversion Complete",
                    f"Successfully converted to GGUF:\n{gguf_path}\n\n"
                    "The model will now be loaded."
                )
                
                # Emit signal to reload the model
                self.emit_signal(
                    SignalCode.LLM_GGUF_CONVERSION_COMPLETE,
                    {"model_path": model_path, "gguf_path": gguf_path}
                )
                
                # Trigger model reload
                self.emit_signal(SignalCode.LLM_LOAD_SIGNAL)
            else:
                self.logger.error(f"GGUF conversion failed: {error}")
                QMessageBox.critical(
                    main_window,
                    "Conversion Failed",
                    f"Failed to convert model to GGUF:\n\n{error}"
                )
                self.emit_signal(
                    SignalCode.LLM_GGUF_CONVERSION_FAILED,
                    {"model_path": model_path, "error": error}
                )
                
        except Exception as e:
            progress.close()
            self.logger.exception(f"GGUF conversion error: {e}")
            QMessageBox.critical(
                main_window,
                "Conversion Error",
                f"An error occurred during conversion:\n\n{str(e)}"
            )

    def on_huggingface_download_complete_signal(self, data):
        # Use add_to_queue to ensure processing happens in worker thread,
        # not main thread, to prevent UI lockups during model loading
        if self._llm_generate_worker is not None:
            self.llm_generate_worker.add_to_queue({
                "_message_type": "download_complete",
                "data": data
            })

    def on_llm_reload_rag_index_signal(self, data):
        if self._llm_generate_worker is not None:
            self.llm_generate_worker.on_llm_reload_rag_index_signal(data)

    def on_rag_index_all_documents_signal(self, data):
        if self.llm_generate_worker is not None:
            self.llm_generate_worker.on_rag_index_all_documents_signal(data)

    def on_rag_index_selected_documents_signal(self, data):
        if self.llm_generate_worker is not None:
            self.llm_generate_worker.on_rag_index_selected_documents_signal(
                data
            )

    def on_rag_index_cancel_signal(self, data):
        if self._llm_generate_worker is not None:
            self.llm_generate_worker.on_rag_index_cancel_signal(data)

    def on_rag_load_documents_signal(self, data):
        if self._llm_generate_worker is not None:
            self.llm_generate_worker.on_rag_load_documents_signal(data)

    def on_index_document_signal(self, data):
        if self._llm_generate_worker is not None:
            self.llm_generate_worker.on_index_document_signal(data)

    def on_llm_start_quantization_signal(self, data):
        if self._llm_generate_worker is not None:
            self.llm_generate_worker.on_llm_start_quantization_signal(data)

    def on_llm_clear_history_signal(self, data):
        if self._llm_generate_worker is not None:
            self.llm_generate_worker.on_llm_clear_history_signal(data)

    def on_llm_add_chatbot_response_to_history(self, data):
        if self._llm_generate_worker is not None:
            self.llm_generate_worker.on_llm_add_chatbot_response_to_history(
                data
            )

    def on_llm_load_conversation(self, data):
        if self._llm_generate_worker is not None:
            self.llm_generate_worker.on_llm_load_conversation(data)

    def on_quit_application_signal(self, data):
        if self._llm_generate_worker is not None:
            self.llm_generate_worker.on_quit_application_signal(data)

    def on_conversation_deleted_signal(self, data):
        if self._llm_generate_worker is not None:
            self.llm_generate_worker.on_conversation_deleted_signal(data)

    def on_section_changed_signal(self, data):
        if self._llm_generate_worker is not None:
            self.llm_generate_worker.on_section_changed_signal(data)

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
        if self._stt_audio_processor_worker is not None:
            self.stt_audio_processor_worker.update_properties(data)

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
        if self._stt_audio_processor_worker is not None:
            self.stt_audio_processor_worker.add_to_queue(
                {
                    "_message_type": "stt_unload",
                    "data": data,
                }
            )

    def on_stt_process_audio_signal(self, data):
        # Use the property to ensure the worker is created
        if self.logger:
            self.logger.debug("on_stt_process_audio_signal called")
        worker = self.stt_audio_processor_worker
        if worker is not None:
            if self.logger:
                self.logger.debug("Forwarding audio to stt_audio_processor_worker")
            worker.on_stt_process_audio_signal(data)
        else:
            if self.logger:
                self.logger.warning("stt_audio_processor_worker is None")

    def on_interrupt_process_signal(self, data):
        # Interrupt LLM generation
        if self._llm_generate_worker is not None:
            self.llm_generate_worker.llm_on_interrupt_process_signal(data)

        # Interrupt TTS generation
        if self.tts_generator_worker is not None:
            self.tts_generator_worker.on_interrupt_process_signal(data)

        if self._tts_vocalizer_worker is not None:
            self.tts_vocalizer_worker.on_interrupt_process_signal(data)

    def on_unblock_tts_generator_signal(self, data):
        callback_handled = False
        
        if self.tts_generator_worker is not None:
            self.tts_generator_worker.on_unblock_tts_generator_signal(data)
            callback_handled = True

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

        self._tts_runtime_prewarm_started = False
        self._stop_tts_activity_immediately()

        if self._control_daemon_runtime_async(
            "tts",
            "unload",
            ModelType.TTS,
        ):
            return
        if self.tts_generator_worker is not None:
            self.tts_generator_worker.add_to_queue(
                {
                    "_message_type": "tts_disable",
                    "data": data,
                }
            )

    @staticmethod
    def _queue_tts_worker_message(worker, message: dict) -> None:
        """Send one TTS control message through the worker queue."""
        add_to_queue = getattr(worker, "add_to_queue", None)
        if callable(add_to_queue):
            add_to_queue(message)

    def _stop_tts_activity_immediately(self) -> None:
        """Stop queued TTS playback before daemon unload completes."""
        generator = getattr(self, "_tts_generator_worker", None)
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
        return self.tts_generator_worker

    def _reload_tts_model_manager(self, data):
        from airunner.enums import ModelType

        self._tts_runtime_prewarm_started = False
        if getattr(self.application_settings, "tts_enabled", False):
            if self._control_daemon_runtime_async(
                "tts",
                "load",
                ModelType.TTS,
                route_metadata=self._tts_runtime_route_metadata(),
            ):
                return
        if self.tts_generator_worker is not None:
            self.tts_generator_worker._reload_tts_model_manager(data)

    def on_application_settings_changed_signal(self, data):
        self._refresh_daemon_tts_for_reference_speaker_change(data)

        if self.tts_generator_worker is not None:
            self.tts_generator_worker.on_application_settings_changed_signal(
                data
            )

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
        if self.tts_generator_worker is not None:
            self.tts_generator_worker.on_add_to_queue_signal(data)

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
            self.logger.info(f"Queueing download request: {download_data}")

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
            self.logger.info(
                f"Starting OpenVoice ZIP download to {openvoice_dir}"
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
            self.logger.info(f"Queueing OpenVoice ZIP download request: {download_data}")

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
        from airunner.components.tts.data.bootstrap.openvoice_languages import (
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
