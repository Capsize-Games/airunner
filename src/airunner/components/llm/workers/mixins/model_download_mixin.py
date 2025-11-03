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
            data: Dictionary containing model_path, model_name, repo_id
        """
        if self._download_dialog_showing:
            self.logger.debug(
                "Download dialog already showing, ignoring duplicate signal"
            )
            return

        model_path = data.get("model_path", "")
        model_name = data.get("model_name", "Unknown Model")
        repo_id = data.get("repo_id", "")

        self.logger.info(
            f"Model download required: {model_name} at {model_path}"
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

        self._show_download_dialog(
            main_window, model_info, model_path, repo_id
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

        self.logger.error(f"Model info not found for repo_id: {repo_id}")
        return None

    def _show_download_dialog(
        self,
        main_window: object,
        model_info: Dict,
        model_path: str,
        repo_id: str,
    ) -> None:
        """Create and show the download dialog.

        Args:
            main_window: Parent window for dialog
            model_info: Model configuration dictionary
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
            self._download_dialog = HuggingFaceDownloadDialog(
                parent=main_window,
                model_name=model_info.get("name", repo_id),
                model_path=model_path,
            )

            self.download_manager = create_worker(DownloadHuggingFaceModel)

            self.download_manager.download(
                repo_id=repo_id,
                model_type=model_info.get("model_type", "llm"),
                output_dir=os.path.dirname(model_path),
                setup_quantization=True,
                quantization_bits=4,
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
            data: Download completion data containing model_path
        """
        self._download_dialog_showing = False
        self._download_dialog = None

        model_path = data.get("model_path", "")
        self.logger.info(f"Download complete for model at: {model_path}")

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
                )
            )
        except Exception:
            self.emit_signal(
                SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                {
                    "response": LLMResponse(
                        message=message,
                        is_end_of_message=False,
                    )
                },
            )

    def _auto_load_downloaded_model(self) -> None:
        """Automatically trigger model loading after download."""
        if self.model_manager:
            self.logger.info("Triggering automatic model load after download")
            self.model_manager.load()
        else:
            self.logger.warning(
                "Model manager not available after download - cannot auto-load"
            )
