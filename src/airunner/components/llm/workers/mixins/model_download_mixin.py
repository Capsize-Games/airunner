"""Model download management operations for LLM worker."""

import os
import sys
import threading
from typing import Dict, Optional

from PySide6.QtWidgets import QApplication

from airunner.enums import SignalCode
from airunner.components.llm.config.provider_config import LLMProviderConfig
from airunner.components.llm.managers.llm_response import LLMResponse


class HeadlessDownloadProgress:
    """Headless download progress tracker using tqdm."""
    
    def __init__(self, model_name: str, model_path: str):
        """Initialize headless download progress.
        
        Args:
            model_name: Name of the model being downloaded
            model_path: Path where model will be saved
        """
        self.model_name = model_name
        self.model_path = model_path
        self._overall_bar = None
        self._file_bars: Dict[str, object] = {}
        self._lock = threading.Lock()
        self._completed = threading.Event()
        self._failed = False
        self._error_message = ""
        
        # Import tqdm here to avoid issues if not installed
        try:
            from tqdm import tqdm
            self._tqdm = tqdm
        except ImportError:
            self._tqdm = None
            print(f"[Download] tqdm not installed, using simple progress output")
    
    def on_log_updated(self, data: Dict) -> None:
        """Handle log messages from download worker."""
        message = data.get("message", "")
        if self._tqdm:
            # Use tqdm.write to avoid breaking progress bars
            self._tqdm.write(f"[Download] {message}")
        else:
            print(f"[Download] {message}")
    
    def on_progress_updated(self, data: Dict) -> None:
        """Handle overall progress updates."""
        progress = data.get("progress", 0)
        
        if self._tqdm and self._overall_bar is None:
            self._overall_bar = self._tqdm(
                total=100,
                desc=f"Downloading {self.model_name}",
                unit="%",
                position=0,
                leave=True,
            )
        
        if self._overall_bar:
            self._overall_bar.n = progress
            self._overall_bar.refresh()
        elif not self._tqdm:
            print(f"\r[Download] Overall progress: {progress:.1f}%", end="", flush=True)
    
    def on_file_progress_updated(self, data: Dict) -> None:
        """Handle per-file progress updates."""
        filename = data.get("filename", "")
        downloaded = data.get("downloaded", 0)
        total = data.get("total", 0)
        
        if not filename:
            return
        
        with self._lock:
            if self._tqdm:
                if filename not in self._file_bars and total > 0:
                    # Create a new progress bar for this file
                    position = len(self._file_bars) + 1
                    short_name = os.path.basename(filename)[:30]
                    self._file_bars[filename] = self._tqdm(
                        total=total,
                        desc=short_name,
                        unit="B",
                        unit_scale=True,
                        unit_divisor=1024,
                        position=position,
                        leave=False,
                    )
                
                if filename in self._file_bars:
                    bar = self._file_bars[filename]
                    bar.n = downloaded
                    bar.refresh()
                    
                    # Close bar when complete
                    if downloaded >= total and total > 0:
                        bar.close()
                        del self._file_bars[filename]
    
    def on_download_complete(self, data: Dict) -> None:
        """Handle download completion."""
        # Close all progress bars
        with self._lock:
            for bar in self._file_bars.values():
                bar.close()
            self._file_bars.clear()
            
            if self._overall_bar:
                self._overall_bar.n = 100
                self._overall_bar.refresh()
                self._overall_bar.close()
                self._overall_bar = None
        
        if self._tqdm:
            self._tqdm.write(f"✅ Download complete: {self.model_name}")
        else:
            print(f"\n✅ Download complete: {self.model_name}")
        
        self._completed.set()
    
    def on_download_failed(self, data: Dict) -> None:
        """Handle download failure."""
        error = data.get("error", "Unknown error")
        self._failed = True
        self._error_message = error
        
        # Close all progress bars
        with self._lock:
            for bar in self._file_bars.values():
                bar.close()
            self._file_bars.clear()
            
            if self._overall_bar:
                self._overall_bar.close()
                self._overall_bar = None
        
        if self._tqdm:
            self._tqdm.write(f"❌ Download failed: {error}")
        else:
            print(f"\n❌ Download failed: {error}")
        
        self._completed.set()
    
    def wait_for_completion(self, timeout: float = 3600) -> bool:
        """Wait for download to complete.
        
        Args:
            timeout: Maximum time to wait in seconds (default: 1 hour)
            
        Returns:
            True if download succeeded, False if failed or timed out
        """
        completed = self._completed.wait(timeout=timeout)
        return completed and not self._failed
    
    @property
    def error_message(self) -> str:
        """Get error message if download failed."""
        return self._error_message


class ModelDownloadMixin:
    """Handles LLM model download operations.

    This mixin provides functionality for:
    - Handling download required signals
    - Showing download dialog (GUI mode)
    - Headless download with tqdm progress (headless mode)
    - Managing download worker
    - Handling download completion and auto-loading
    """

    def on_llm_model_download_required_signal(self, data: Dict) -> None:
        """Handle model download required signal - show download dialog or download headless.

        Args:
            data: Dictionary containing model_path, model_name, repo_id, model_type
                  For GGUF models, also contains gguf_filename
                  May contain convert_to_gguf flag to trigger conversion after download
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
        convert_to_gguf = data.get("convert_to_gguf", False)
        
        # Store convert_to_gguf flag for use in completion handler
        self._pending_convert_to_gguf = convert_to_gguf
        
        # Check if this is a GGUF download
        is_gguf = model_type == "gguf" or gguf_filename is not None

        self.logger.info(
            f"Model download required: {model_name} at {model_path} (GGUF: {is_gguf}, convert_after: {convert_to_gguf})"
        )

        if not repo_id:
            self.logger.error("No repo_id provided in download request")
            return

        model_info = self._get_model_info(repo_id)
        if not model_info:
            return

        # Add GGUF info to model_info if this is a GGUF download
        if is_gguf:
            model_info = dict(model_info)  # Make a copy
            model_info["is_gguf"] = True
            model_info["gguf_filename"] = gguf_filename

        # Check if we're running in GUI or headless mode
        if self._is_headless_mode():
            # Headless mode - download with tqdm progress
            self._download_headless(
                model_info,
                model_path,
                repo_id,
                data.get("missing_files"),
            )
        else:
            # GUI mode - show download dialog
            main_window = self._get_main_window()
            if main_window:
                self._show_download_dialog(
                    main_window,
                    model_info,
                    model_path,
                    repo_id,
                    data.get("missing_files"),
                )

    def _is_headless_mode(self) -> bool:
        """Check if running in headless mode (no GUI).
        
        Returns:
            True if running headless (QCoreApplication), False if GUI (QApplication)
        """
        app = QApplication.instance()
        if app is None:
            return True
        # QCoreApplication doesn't have topLevelWidgets, only QApplication does
        return not hasattr(app, 'topLevelWidgets')

    def _download_headless(
        self,
        model_info: Dict,
        model_path: str,
        repo_id: str,
        missing_files: Optional[list] = None,
    ) -> bool:
        """Download model in headless mode with tqdm progress bars.
        
        Args:
            model_info: Model configuration dictionary
            model_path: Path where model will be saved
            repo_id: HuggingFace repository ID
            missing_files: Optional list of specific files to download
            
        Returns:
            True if download succeeded, False otherwise
        """
        from airunner.components.llm.managers.download_huggingface import (
            DownloadHuggingFaceModel,
        )
        from airunner.utils.application.create_worker import create_worker

        self._download_dialog_showing = True
        
        is_gguf = model_info.get("is_gguf", False)
        gguf_filename = model_info.get("gguf_filename")
        model_name = model_info.get("name", repo_id)
        
        if is_gguf:
            model_name = f"{model_name} (GGUF)"
        
        self.logger.info(f"Starting headless download: {model_name}")
        print(f"\n📦 Downloading model: {model_name}")
        print(f"   Repository: {repo_id}")
        print(f"   Destination: {model_path}\n")
        
        # Create progress tracker
        progress = HeadlessDownloadProgress(model_name, model_path)
        
        # Create download worker
        download_manager = create_worker(DownloadHuggingFaceModel)
        
        # Connect progress tracker to download worker signals
        download_manager.register(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            progress.on_log_updated,
        )
        download_manager.register(
            SignalCode.UPDATE_DOWNLOAD_PROGRESS,
            progress.on_progress_updated,
        )
        download_manager.register(
            SignalCode.UPDATE_FILE_DOWNLOAD_PROGRESS,
            progress.on_file_progress_updated,
        )
        download_manager.register(
            SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
            progress.on_download_complete,
        )
        download_manager.register(
            SignalCode.HUGGINGFACE_DOWNLOAD_FAILED,
            progress.on_download_failed,
        )
        
        # Also register our own completion handler for auto-loading
        download_manager.register(
            SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
            self.on_huggingface_download_complete_signal,
        )
        
        try:
            if is_gguf and gguf_filename:
                # GGUF download
                download_manager.download(
                    repo_id=repo_id,
                    model_type="gguf",
                    output_dir=model_path,
                    setup_quantization=False,
                    quantization_bits=0,
                    missing_files=None,
                    gguf_filename=gguf_filename,
                )
            else:
                # Standard HuggingFace download
                download_manager.download(
                    repo_id=repo_id,
                    model_type=model_info.get("model_type", "llm"),
                    output_dir=os.path.dirname(model_path),
                    setup_quantization=model_info.get("setup_quantization", True),
                    quantization_bits=model_info.get("quantization_bits", 4),
                    missing_files=missing_files,
                )
            
            # Wait for download to complete (with 1 hour timeout)
            success = progress.wait_for_completion(timeout=3600)
            
            if not success:
                self.logger.error(f"Download failed: {progress.error_message}")
                self._download_dialog_showing = False
                return False
            
            self._download_dialog_showing = False
            return True
            
        except Exception as e:
            self.logger.error(f"Error during headless download: {e}")
            self._download_dialog_showing = False
            return False

    def _get_main_window(self) -> Optional[object]:
        """Get the main application window.

        Returns:
            Main window object or None if not found
        """
        app = QApplication.instance()
        if app is None:
            return None
        
        # QCoreApplication doesn't have topLevelWidgets
        if not hasattr(app, 'topLevelWidgets'):
            return None
        
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
        
        If convert_to_gguf flag was set in the original download request,
        triggers GGUF conversion before loading.

        Args:
            data: Download completion data containing model_path, repo_id
        """
        self._download_dialog_showing = False
        self._download_dialog = None

        model_path = data.get("model_path", "")
        repo_id = data.get("repo_id", "")
        
        # Check for stored convert_to_gguf flag from original download request
        convert_to_gguf = getattr(self, "_pending_convert_to_gguf", False)
        self._pending_convert_to_gguf = False  # Reset flag

        self.logger.info(
            f"Download complete for model at: {model_path} (repo_id: {repo_id}, convert_to_gguf: {convert_to_gguf})"
        )

        # Skip auto-load for embedding models - they're handled by RAGPropertiesMixin
        if repo_id == "intfloat/e5-large":
            self.logger.debug("Skipping auto-load for embedding model")
            return
        
        # Check if we need to convert to GGUF after download
        if convert_to_gguf:
            self.logger.info("Triggering GGUF conversion after safetensors download")
            # Get model name from model manager or path
            model_name = self.model_manager.model_name if self.model_manager else "Unknown Model"
            self.emit_signal(
                SignalCode.LLM_CONVERT_TO_GGUF_SIGNAL,
                {
                    "model_path": model_path,
                    "model_name": model_name,
                    "quantization": "Q4_K_M",
                },
            )
            return  # Don't auto-load - wait for conversion to complete

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
