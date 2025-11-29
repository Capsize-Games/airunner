"""
Worker Manager for handling various application workers.

This class uses inline imports to avoid slow startup times. Do not move
imports to the top of the file.
"""

from typing import Dict
from airunner.components.application.workers.worker import Worker
from airunner.enums import SignalCode
from airunner.utils.application.create_worker import create_worker


class WorkerManager(Worker):
    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
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
            SignalCode.RAG_RELOAD_INDEX_SIGNAL: self.on_llm_reload_rag_index_signal,
            SignalCode.RAG_INDEX_ALL_DOCUMENTS: self.on_rag_index_all_documents_signal,
            SignalCode.RAG_INDEX_SELECTED_DOCUMENTS: self.on_rag_index_selected_documents_signal,
            SignalCode.RAG_INDEX_CANCEL: self.on_rag_index_cancel_signal,
            SignalCode.RAG_LOAD_DOCUMENTS: self.on_rag_load_documents_signal,
            SignalCode.INDEX_DOCUMENT: self.on_index_document_signal,
            SignalCode.LLM_START_FINE_TUNE: self.on_llm_start_fine_tune_signal,
            SignalCode.LLM_FINE_TUNE_CANCEL: self.on_llm_fine_tune_cancel_signal,
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
            SignalCode.LLM_TEXT_STREAMED_SIGNAL: self.on_llm_text_streamed_signal,
            SignalCode.TTS_MODEL_CHANGED: self._reload_tts_model_manager,
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: self.on_application_settings_changed_signal,
            SignalCode.TTS_QUEUE_SIGNAL: self.on_add_to_queue_signal,
            SignalCode.PLAYBACK_DEVICE_CHANGED: self.on_playback_device_changed_signal,
            SignalCode.IMAGE_EXPORTED: self.on_image_exported_signal,
            SignalCode.FARA_LOAD_SIGNAL: self.on_fara_load_signal,
            SignalCode.FARA_UNLOAD_SIGNAL: self.on_fara_unload_signal,
            SignalCode.FARA_MODEL_DOWNLOAD_REQUIRED: self.on_fara_model_download_required_signal,
        }
        super().__init__()
        self._mask_generator_worker = None
        self._sd_worker = None
        self._safety_checker_worker = None
        self._fara_worker = None
        self._pending_generation_request = None
        self._download_dialog = (
            None  # Store dialog reference to prevent garbage collection
        )
        self._stt_audio_capture_worker = None
        self._stt_audio_processor_worker = None
        self._tts_generator_worker = None
        self._tts_vocalizer_worker = None
        self._llm_generate_worker = None
        self._document_worker = None
        self._huggingface_download_worker = None
        self._image_export_worker = None
        self._model_scanner_worker = None
        if self.logger:
            self.logger.debug(
                f"WorkerManager initialized. Mediator ID: {id(self.mediator)}"
            )

        self.model_scanner_worker.add_to_queue("scan_for_models")

    def handle_message(self, message: Dict):
        if self.logger:
            self.logger.info(
                f"WorkerManager::handle_message CALLED with request_type={message.get('request_type')}"
            )
        data = message.get("data", {})
        request_type = message.get("request_type")
        try:
            if request_type == "llm_generate":
                if self.llm_generate_worker is not None:
                    self.llm_generate_worker.on_llm_request_signal(data)
            elif request_type == "fara_generate":
                # Route USE_COMPUTER requests to Fara worker
                if self.fara_worker is not None:
                    self.fara_worker.on_fara_request_signal(data)
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
                self.logger.error(f"Error processing worker requests: {e}")

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
            from airunner.components.tts.workers.tts_generator_worker import (
                TTSGeneratorWorker,
            )

            self._tts_generator_worker = create_worker(TTSGeneratorWorker)
        return self._tts_generator_worker

    @property
    def tts_vocalizer_worker(self):
        if self._tts_vocalizer_worker is None:
            from airunner.components.tts.workers.tts_vocalizer_worker import (
                TTSVocalizerWorker,
            )

            self._tts_vocalizer_worker = create_worker(TTSVocalizerWorker)
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
    def fara_worker(self):
        if self._fara_worker is None:
            from airunner.components.llm.workers.fara_worker import (
                FaraWorker,
            )

            self._fara_worker = create_worker(FaraWorker)
        return self._fara_worker

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

        # Check if this is a USE_COMPUTER action - route to Fara worker
        from airunner.enums import LLMActionType

        request_data = data.get("request_data", {})
        action = request_data.get("action")

        # Handle both enum and string action values
        is_use_computer = False
        if action is LLMActionType.USE_COMPUTER:
            is_use_computer = True
        elif isinstance(action, str) and action.lower() == "use_computer":
            is_use_computer = True

        if is_use_computer:
            if self.logger:
                self.logger.info("USE_COMPUTER action detected - routing to Fara worker")
            # First unload all other models, then route to Fara
            self.emit_signal(SignalCode.FARA_LOAD_SIGNAL, {})
            self.add_to_queue(
                {
                    "data": data,
                    "request_type": "fara_generate",
                }
            )
        else:
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
        self.add_to_queue(
            {
                "data": data,
                "request_type": "tts_enable",
            }
        )

    def on_stt_load_signal(self, data: Dict):
        self.add_to_queue(
            {
                "data": data,
                "request_type": "stt_load",
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
        from airunner.components.llm.gui.windows.huggingface_download_dialog import (
            HuggingFaceDownloadDialog,
        )

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

        # Determine model type for download worker
        # All art models (SDXL, FLUX, SD) use "art" type for bootstrap data lookup
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

    def on_huggingface_download_complete(self, data: Dict):
        """Handle download completion and retry pending generation.

        Args:
            data: Download completion info with model_path
        """
        if self.logger:
            self.logger.info(
                f"WorkerManager: Download complete for {data.get('model_path')}"
            )
            self.logger.info(
                f"Pending generation request: {self._pending_generation_request is not None}"
            )

        # Delegate to LLM worker for LLM model downloads
        if self._llm_generate_worker is not None:
            self.llm_generate_worker.on_huggingface_download_complete_signal(
                data
            )

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

    def on_unload_art_signal(self, data: Dict):
        if self._sd_worker is not None:

            def callback(res: Dict):
                del self._sd_worker
                self._sd_worker = None

            data["callback"] = callback
            self.sd_worker.unload(data)
            self.sd_worker.image_export_worker.stop()
            del self.sd_worker.image_export_worker
            self.sd_worker.image_export_worker = None
            self._image_export_worker = None

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

        if (
            model_type == ModelType.SAFETY_CHECKER
            and status == ModelStatus.LOADED
            and self._pending_generation_request is not None
        ):
            self.logger.info(
                "Safety checker loaded, proceeding with pending image generation"
            )
            pending_data = self._pending_generation_request
            self._pending_generation_request = None
            self._proceed_with_generation(pending_data)

        elif (
            model_type == ModelType.SAFETY_CHECKER
            and status == ModelStatus.FAILED
            and self._pending_generation_request is not None
        ):
            self.logger.warning(
                "Safety checker failed to load; continuing image generation without it"
            )
            pending_data = self._pending_generation_request
            self._pending_generation_request = None
            self._proceed_with_generation(pending_data)

        if self._sd_worker is not None:
            self.sd_worker.on_model_status_changed_signal(data)
        if self._stt_audio_capture_worker is not None:
            self.stt_audio_capture_worker.on_model_status_changed_signal(data)

    def on_load_art_signal(self, data):
        if self.sd_worker is not None:
            self.sd_worker.on_load_art_signal(data)

    def on_art_model_changed(self, data):
        if self._sd_worker is not None:
            self.sd_worker.on_art_model_changed(data)

    def on_load_controlnet_signal(self, data):
        if self._sd_worker is not None:
            self.sd_worker.on_load_controlnet_signal(data)

    def on_unload_controlnet_signal(self, data):
        if self._sd_worker is not None:
            self.sd_worker.on_unload_controlnet_signal(data)

    def on_safety_checker_load_signal(self, data):
        # Initialize the safety checker worker and trigger loading
        if self.safety_checker_worker is not None:
            self.safety_checker_worker.handle_load(data)

    def on_safety_checker_unload_signal(self, data):
        # Trigger unloading if worker exists
        if self._safety_checker_worker is not None:
            self._safety_checker_worker.handle_unload(data)

    def _handle_image_generation_request(self, data):
        """
        Handle image generation request, ensuring safety checker is ready if needed.

        Args:
            data: Image generation request data
        """
        from airunner.components.settings.data.application_settings import (
            ApplicationSettings,
        )

        app_settings = ApplicationSettings.objects.first()

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

    def _proceed_with_generation(self, data):
        """
        Proceed with image generation after safety checker is ready (or not needed).

        Args:
            data: Image generation request data
        """
        if self.sd_worker is not None:
            self.sd_worker.on_do_generate_signal(data)

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
        if self._llm_generate_worker is not None:
            self.llm_generate_worker.on_llm_on_unload_signal(data)

    def on_llm_load_model_signal(self, data):
        if self._llm_generate_worker is not None:
            self.llm_generate_worker.on_llm_load_model_signal(data)

    def on_fara_load_signal(self, data: Dict):
        """Handle FARA load signal.

        Unloads all other models (LLM, SD, TTS, STT) before loading Fara
        to ensure sufficient VRAM is available.

        Args:
            data: Signal data dictionary
        """
        if self.logger:
            self.logger.info("FARA_LOAD_SIGNAL received - unloading all models first")

        # Unload regular LLM if loaded
        if self._llm_generate_worker is not None:
            try:
                self.llm_generate_worker.unload_llm()
                if self.logger:
                    self.logger.info("Unloaded regular LLM model")
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Error unloading LLM: {e}")

        # Unload SD/art model if loaded
        if self._sd_worker is not None:
            try:
                self.sd_worker.on_unload_art_signal()
                if self.logger:
                    self.logger.info("Unloaded art/SD model")
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Error unloading SD: {e}")

        # Unload TTS if loaded
        if self._tts_generator_worker is not None:
            try:
                self.tts_generator_worker.unload()
                if self.logger:
                    self.logger.info("Unloaded TTS model")
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Error unloading TTS: {e}")

        # Unload STT if loaded
        if self._stt_audio_processor_worker is not None:
            try:
                self.stt_audio_processor_worker.unload()
                if self.logger:
                    self.logger.info("Unloaded STT model")
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Error unloading STT: {e}")

        # Now load Fara
        if self.fara_worker is not None:
            self.fara_worker.load(data)

    def on_fara_unload_signal(self, data: Dict):
        """Handle FARA unload signal.

        Args:
            data: Signal data dictionary
        """
        if self.logger:
            self.logger.info("FARA_UNLOAD_SIGNAL received")

        if self._fara_worker is not None:
            self.fara_worker.unload(data)

    def on_fara_model_download_required_signal(self, data: Dict):
        """Handle FARA model download required signal.

        Args:
            data: Signal data dictionary with model_path, model_name, repo_id
        """
        if self.logger:
            self.logger.info(f"FARA_MODEL_DOWNLOAD_REQUIRED received: {data}")

        if self._fara_worker is not None:
            self.fara_worker.on_fara_model_download_required_signal(data)

    def on_llm_model_changed_signal(self, data):
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
        
        # Create download worker
        self._huggingface_download_worker = create_worker(DownloadHuggingFaceModel)
        
        if is_gguf and gguf_filename:
            self.logger.info(f"Starting GGUF download: {repo_id}/{gguf_filename}")
            self._huggingface_download_worker.download(
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
            self._huggingface_download_worker.download(
                repo_id=repo_id,
                model_type=model_type,
                output_dir=model_path,
                setup_quantization=True,
                quantization_bits=data.get("quantization_bits", 4),
                missing_files=data.get("missing_files"),
            )
        
        self._download_dialog.show()

    def on_huggingface_download_complete_signal(self, data):
        if self._llm_generate_worker is not None:
            self.llm_generate_worker.on_huggingface_download_complete_signal(
                data
            )

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

    def on_llm_start_fine_tune_signal(self, data):
        if self._llm_generate_worker is not None:
            self.llm_generate_worker.on_llm_start_fine_tune_signal(data)

    def on_llm_fine_tune_cancel_signal(self, data):
        if self._llm_generate_worker is not None:
            self.llm_generate_worker.on_llm_fine_tune_cancel_signal(data)

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
        if self._audio_processor_worker is not None:
            self.stt_audio_processor_worker.update_properties(data)

    def on_stt_unload_signal(self, data):
        if self._audio_processor_worker is not None:
            self.stt_audio_processor_worker.on_stt_unload_signal(data)

    def on_stt_process_audio_signal(self, data):
        if self._audio_processor_worker is not None:
            self.stt_audio_processor_worker.on_stt_process_audio_signal(data)

    def on_interrupt_process_signal(self, data):
        # Interrupt LLM generation
        if self._llm_generate_worker is not None:
            self.llm_generate_worker.llm_on_interrupt_process_signal(data)

        # Interrupt TTS generation
        if self._tts_generator_worker is not None:
            self.tts_generator_worker.on_interrupt_process_signal(data)

        if self._tts_vocalizer_worker is not None:
            self.tts_vocalizer_worker.on_interrupt_process_signal(data)

    def on_unblock_tts_generator_signal(self, data):
        if self._tts_generator_worker is not None:
            self.tts_generator_worker.on_unblock_tts_generator_signal(data)

        if self._tts_vocalizer_worker is not None:
            self.tts_vocalizer_worker.on_unblock_tts_generator_signal(data)

    def on_disable_tts_signal(self, data):
        if self._tts_generator_worker is not None:
            self.tts_generator_worker.on_disable_tts_signal(data)

    def on_llm_text_streamed_signal(self, data):
        if self._tts_generator_worker is not None:
            self.tts_generator_worker.on_llm_text_streamed_signal(data)

    def _reload_tts_model_manager(self, data):
        if self._tts_generator_worker is not None:
            self.tts_generator_worker._reload_tts_model_manager(data)

    def on_application_settings_changed_signal(self, data):
        if self._tts_generator_worker is not None:
            self.tts_generator_worker.on_application_settings_changed_signal(
                data
            )

        if self._tts_vocalizer_worker is not None:
            self.tts_vocalizer_worker.on_application_settings_changed_signal(
                data
            )

    def on_add_to_queue_signal(self, data):
        if self._tts_generator_worker is not None:
            self.tts_generator_worker.on_add_to_queue_signal(data)

    def on_playback_device_changed_signal(self, data):
        if self._tts_vocalizer_worker is not None:
            self.tts_vocalizer_worker.on_playback_device_changed_signal(data)

    def on_image_exported_signal(self, data):
        # self.api.art.unload()
        pass
