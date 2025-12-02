"""Model download management operations for LLM worker."""

import os
from typing import Dict, Optional

from PySide6.QtWidgets import QApplication

from airunner.enums import SignalCode
from airunner.components.llm.config.provider_config import LLMProviderConfig
from airunner.components.llm.managers.llm_response import LLMResponse


class ModelDownloadMixin:
    """Handles LLM model download operations.

    This mixin provides functionality for:
    - Handling download required signals
    - Showing download dialog
    - Managing download worker
    - Handling download completion and auto-loading
    """

    def on_llm_model_download_required_signal(self, data: Dict) -> None:
        """Handle model download required signal - show download dialog.

        Args:
            data: Dictionary containing model_path, model_name, repo_id, model_type
                  For GGUF models, also contains gguf_filename
        """
        # Skip embedding model downloads - those are handled by RAGPropertiesMixin
        model_type = data.get("model_type", "llm")
        if model_type == "embedding":
            self.logger.debug(
                "Ignoring embedding model download request - handled by RAG system"
            )
            return

        if self._download_dialog_showing:
            self.logger.debug(
                "Download dialog already showing, ignoring duplicate signal"
            )
            return

        model_path = data.get("model_path", "")
        model_name = data.get("model_name", "Unknown Model")
        repo_id = data.get("repo_id", "")
        gguf_filename = data.get("gguf_filename")
        
        # Check if this is a GGUF download
        is_gguf = model_type == "gguf" or gguf_filename is not None

        self.logger.info(
            f"Model download required: {model_name} at {model_path} (GGUF: {is_gguf})"
        )

        if not repo_id:
            self.logger.error("No repo_id provided in download request")
            return

        main_window = self._get_main_window()
        if not main_window:
            return

        model_info = self._get_model_info(repo_id)
        if not model_info:
            return

        # Add GGUF info to model_info if this is a GGUF download
        if is_gguf:
            model_info = dict(model_info)  # Make a copy
            model_info["is_gguf"] = True
            model_info["gguf_filename"] = gguf_filename

        self._show_download_dialog(
            main_window,
            model_info,
            model_path,
            repo_id,
            data.get("missing_files"),
        )

    def _get_main_window(self) -> Optional[object]:
        """Get the main application window.

        Returns:
            Main window object or None if not found
        """
        app = QApplication.instance()
        for widget in app.topLevelWidgets():
            if widget.__class__.__name__ == "MainWindow":
                return widget

        self.logger.error(
            "Cannot show download dialog - main window not found"
        )
        return None

    def _get_model_info(self, repo_id: str) -> Optional[Dict]:
        """Get model information from config using repo_id.

        Args:
            repo_id: HuggingFace repository ID

        Returns:
            Model info dictionary or None if not found
        """
        for provider_models in [LLMProviderConfig.LOCAL_MODELS]:
            for model_id, info in provider_models.items():
                if info.get("repo_id") == repo_id:
                    return info

        # Fallback for auxiliary models (embeddings, etc.) not listed in config
        self.logger.debug(
            "Model info not found for repo_id %s - using fallback config",
            repo_id,
        )
        return {
            "name": repo_id,
            "repo_id": repo_id,
            "model_type": "llm",
            "setup_quantization": False,
            "quantization_bits": 4,
        }

    def _show_download_dialog(
        self,
        main_window: object,
        model_info: Dict,
        model_path: str,
        repo_id: str,
        missing_files: Optional[list] = None,
    ) -> None:
        """Create and show the download dialog.

        Args:
            main_window: Parent window for dialog
            model_info: Model configuration dictionary (may include is_gguf and gguf_filename)
            model_path: Path where model will be saved
            repo_id: HuggingFace repository ID
        """
        # Import here to avoid circular dependency
        from airunner.components.llm.gui.windows.huggingface_download_dialog import (
            HuggingFaceDownloadDialog,
        )
        from airunner.components.llm.managers.download_huggingface import (
            DownloadHuggingFaceModel,
        )
        from airunner.utils.application.create_worker import create_worker

        self._download_dialog_showing = True

        try:
            is_gguf = model_info.get("is_gguf", False)
            gguf_filename = model_info.get("gguf_filename")
            
            dialog_model_name = model_info.get("name", repo_id)
            if is_gguf:
                dialog_model_name = f"{dialog_model_name} (GGUF)"
            
            self._download_dialog = HuggingFaceDownloadDialog(
                parent=main_window,
                model_name=dialog_model_name,
                model_path=model_path,
            )

            self.download_manager = create_worker(DownloadHuggingFaceModel)

            # Connect dialog to download worker signals
            self.download_manager.register(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                self._download_dialog.on_log_updated,
            )
            self.download_manager.register(
                SignalCode.UPDATE_DOWNLOAD_PROGRESS,
                self._download_dialog.on_progress_updated,
            )
            self.download_manager.register(
                SignalCode.UPDATE_FILE_DOWNLOAD_PROGRESS,
                self._download_dialog.on_file_progress_updated,
            )
            self.download_manager.register(
                SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
                self._download_dialog.on_download_complete,
            )
            self.download_manager.register(
                SignalCode.HUGGINGFACE_DOWNLOAD_FAILED,
                self._download_dialog.on_download_failed,
            )

            if is_gguf and gguf_filename:
                # GGUF download - just download the single .gguf file
                self.download_manager.download(
                    repo_id=repo_id,
                    model_type="gguf",
                    output_dir=model_path,  # GGUF goes directly to model dir
                    setup_quantization=False,  # GGUF is already quantized
                    quantization_bits=0,
                    missing_files=None,
                    gguf_filename=gguf_filename,  # Specific file to download
                )
            else:
                # Standard HuggingFace download
                self.download_manager.download(
                    repo_id=repo_id,
                    model_type=model_info.get("model_type", "llm"),
                    output_dir=os.path.dirname(model_path),
                    setup_quantization=model_info.get("setup_quantization", True),
                    quantization_bits=model_info.get("quantization_bits", 4),
                    missing_files=missing_files,
                )

            self._download_dialog.show()
        except Exception as e:
            self._download_dialog_showing = False
            self._download_dialog = None
            self.logger.error(f"Error showing download dialog: {e}")

    def on_huggingface_download_complete_signal(self, data: Dict) -> None:
        """Handle HuggingFace download completion.

        After download completes, automatically retry loading the model.
        This enables the seamless workflow: download → auto-quantize → load.

        Args:
            data: Download completion data containing model_path and repo_id
        """
        self._download_dialog_showing = False
        self._download_dialog = None

        model_path = data.get("model_path", "")
        repo_id = data.get("repo_id", "")

        self.logger.info(
            f"Download complete for model at: {model_path} (repo_id: {repo_id})"
        )

        # Skip auto-load for embedding models - they're handled by RAGPropertiesMixin
        if repo_id == "intfloat/e5-large":
            self.logger.debug("Skipping auto-load for embedding model")
            return

        self._emit_download_complete_message()
        self._auto_load_downloaded_model()

    def _emit_download_complete_message(self) -> None:
        """Emit download completion message to user."""
        message = (
            "📦 Download complete! "
            "Loading model with automatic quantization...\n"
        )

        try:
            self.api.llm.send_llm_text_streamed_signal(
                LLMResponse(
                    message=message,
                    is_end_of_message=False,
                    is_system_message=True,
                )
            )
        except Exception:
            self.emit_signal(
                SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                {
                    "response": LLMResponse(
                        message=message,
                        is_end_of_message=False,
                        is_system_message=True,
                    )
                },
            )

    def _auto_load_downloaded_model(self) -> None:
        """Automatically trigger model loading after download and retry pending request."""
        if self.model_manager:
            self.logger.info("Triggering automatic model load after download")

            # Try to load the model
            load_success = self.model_manager.load()
            self.logger.info(f"Model load returned: {load_success}")

            # Check if model actually loaded
            from airunner.enums import ModelStatus, ModelType

            if (
                self.model_manager.model_status[ModelType.LLM]
                != ModelStatus.LOADED
            ):
                self.logger.error(
                    f"Model failed to load after download - status: {self.model_manager.model_status[ModelType.LLM]}"
                )
                # Clear pending request since we can't fulfill it
                if hasattr(self, "_pending_llm_request"):
                    self._pending_llm_request = None
                return

            self.logger.info("Model loaded successfully!")

            # If there's a pending request, retry it now that the model is loaded
            if (
                hasattr(self, "_pending_llm_request")
                and self._pending_llm_request
            ):
                self.logger.info(
                    "Retrying pending LLM request after model download"
                )
                # Add the request back to the queue
                self.handle_message(self._pending_llm_request)
                self._pending_llm_request = None
            else:
                self.logger.info("No pending request to retry")
        else:
            self.logger.warning(
                "Model manager not available after download - cannot auto-load"
            )
