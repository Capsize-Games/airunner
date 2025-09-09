"""Dialog and logic for downloading models from CivitAI by URL."""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QInputDialog,
    QMessageBox,
    QProgressDialog,
)
from PySide6.QtCore import Qt, QThread
import os
import logging
from typing import Any, Dict, Optional

from airunner.components.application.workers.qt_civitai_workers import (
    ModelInfoWorker,
    FileDownloadWorker,
)
from airunner.components.application.utils.model_persistence import (
    persist_trigger_words,
)

logger = logging.getLogger(__name__)


class DownloadModelDialog(QDialog):
    @staticmethod
    def _get_model_subfolder(model_type: str, file_info: dict) -> str:
        """Map model type and file info to correct subfolder."""
        # Normalize type
        t = (model_type or "checkpoint").strip().upper()
        # Try to use file type if available
        file_type = (file_info.get("type") or "").strip().upper()
        fname = file_info.get("name", "").lower()
        # LORA
        if t == "LORA":
            return "lora"
        # Checkpoint (txt2img)
        if t in ("CHECKPOINT", "MODEL"):
            return "txt2img"
        # Inpaint
        if t == "INPAINT" or "inpaint" in fname:
            return "inpaint"
        # Embedding
        if (
            t in ("TEXTUAL EMBEDDING", "EMBEDDING", "TEXTUALINVERSION")
            or file_type == "EMBEDDING"
            or fname.endswith(".pt")
        ):
            return "embeddings"
        # Fallback
        return t.lower()

    """Dialog for downloading a model from CivitAI by URL.

    Attributes:
        path_settings: Application path settings, used to resolve base paths.
        application_settings: Global application settings (contains CivitAI API key).
    """

    def __init__(self, parent, path_settings, application_settings):
        super().__init__(parent)
        self.setWindowTitle("CivitAI Model Details")
        self.path_settings = path_settings
        self.application_settings = application_settings
        self.model_info: Optional[Dict[str, Any]] = None

        # Keep strong references to avoid GC while running
        self._download_thread: Optional[QThread] = None
        self._download_worker: Optional[FileDownloadWorker] = None
        self._progress_dialog: Optional[QProgressDialog] = None
        self._info_thread: Optional[QThread] = None
        self._info_worker: Optional[ModelInfoWorker] = None

        # Store download context for persistence
        self._current_version_data: Optional[Dict[str, Any]] = None
        self._current_model_type: Optional[str] = None
        self._current_file_info: Optional[Dict[str, Any]] = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        self.layout = QVBoxLayout(self)
        self.list_widget = QListWidget(self)
        self.download_btn = QPushButton("Download Selected Version", self)
        self.layout.addWidget(self.list_widget)
        self.layout.addWidget(self.download_btn)
        self.download_btn.clicked.connect(self._start_download)

    def fetch_and_display(self, url: str) -> None:
        """Fetch model info from CivitAI and populate the UI (async)."""
        api_key = getattr(self.application_settings, "civit_ai_api_key", "")
        self._info_worker = ModelInfoWorker(url=url, api_key=api_key)
        self._info_thread = QThread(self)
        self._info_worker.moveToThread(self._info_thread)
        self._info_worker.fetched.connect(self._on_info_fetched)
        self._info_worker.error.connect(self._on_info_error)
        self._info_thread.started.connect(self._info_worker.run)
        # Cleanup thread when done
        self._info_worker.fetched.connect(self._info_thread.quit)
        self._info_worker.error.connect(self._info_thread.quit)
        self._info_thread.finished.connect(self._on_info_thread_finished)
        self._info_thread.start()

    def _on_info_thread_finished(self) -> None:
        try:
            if self._info_worker is not None:
                self._info_worker.deleteLater()
        except Exception:
            pass
        try:
            if self._info_thread is not None:
                self._info_thread.deleteLater()
        except Exception:
            pass
        self._info_worker = None
        self._info_thread = None

    def _on_info_error(self, msg: str) -> None:
        QMessageBox.critical(self, "CivitAI Error", msg)
        self.reject()

    def _on_info_fetched(self, data: Dict[str, Any]) -> None:
        self.model_info = data
        name = data.get("name", "Unknown")
        desc = data.get("description", "")
        self.layout.insertWidget(0, QLabel(f"<b>{name}</b>"))
        if desc:
            self.layout.insertWidget(1, QLabel(desc))
        self.layout.insertWidget(2, QLabel("Select a version to download:"))
        self.list_widget.clear()
        for v in data.get("modelVersions", []):
            item = QListWidgetItem(
                f"Version {v.get('id')}: {v.get('name', '')}"
            )
            item.setData(Qt.ItemDataRole.UserRole, v)
            self.list_widget.addItem(item)

    def _on_thread_finished(self) -> None:
        try:
            if self._download_worker is not None:
                self._download_worker.deleteLater()
        except Exception:
            pass
        try:
            if self._download_thread is not None:
                self._download_thread.deleteLater()
        except Exception:
            pass
        self._download_worker = None
        self._download_thread = None

    def _cleanup_download(self) -> None:
        """Stop thread, clear references, and close progress dialog if needed."""
        try:
            if self._progress_dialog is not None:
                self._progress_dialog.close()
        except Exception:
            pass
        if self._download_thread is not None:
            try:
                self._download_thread.quit()
            except Exception:
                logger.debug("Thread quit failed", exc_info=True)
        self._progress_dialog = None

    def _on_download_progress(self, current: int, total: int) -> None:
        if not self._progress_dialog:
            return
        if total <= 0:
            self._progress_dialog.setRange(0, 0)
            return
        if (
            self._progress_dialog.minimum() == 0
            and self._progress_dialog.maximum() == 0
        ):
            self._progress_dialog.setRange(0, 100)
        percent = max(0, min(100, int((current / total) * 100)))
        self._progress_dialog.setValue(percent)

    def _on_download_finished(self, save_path: str) -> None:
        # Persist trigger words immediately (no popup, no delay)
        if (
            self._current_version_data
            and self._current_model_type is not None
            and self._current_file_info
        ):
            try:
                persist_trigger_words(
                    self._current_version_data,
                    self._current_model_type,
                    self._current_file_info,
                    save_path,
                )
                logger.info(
                    f"Successfully persisted trigger words for {save_path}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to persist trigger words for {save_path}: {e}",
                    exc_info=True,
                )

        # Clear download context and cleanup (no extra popups)
        self._current_version_data = None
        self._current_model_type = None
        self._current_file_info = None
        self._cleanup_download()

    def _on_download_failed(self, error: Exception) -> None:
        # Clear download context on failure
        self._current_version_data = None
        self._current_model_type = None
        self._current_file_info = None

        self._cleanup_download()
        QMessageBox.critical(
            self,
            "Download Failed",
            f"Error: {str(error) or 'Unknown error'}",
        )

    def _on_download_failed_str(self, msg: str) -> None:
        # Clear download context on failure
        self._current_version_data = None
        self._current_model_type = None
        self._current_file_info = None

        self._cleanup_download()
        QMessageBox.critical(self, "Download Failed", msg or "Unknown error")

    def _on_download_canceled(self) -> None:
        # Clear download context on cancellation
        self._current_version_data = None
        self._current_model_type = None
        self._current_file_info = None

        try:
            if self._download_worker:
                self._download_worker.cancel()
        except Exception:
            logger.debug("Cancel call failed", exc_info=True)
        self._cleanup_download()

    def _start_download(self) -> None:
        selected = self.list_widget.currentItem()
        if not selected:
            QMessageBox.warning(
                self, "No Selection", "Please select a version."
            )
            return
        if self._download_thread is not None:
            QMessageBox.information(
                self,
                "Download In Progress",
                "A download is already in progress.",
            )
            return

        version = selected.data(Qt.ItemDataRole.UserRole)
        files = version.get("files", []) if version else []
        file_url: Optional[str] = None
        file_name: Optional[str] = None
        file_size_kb = 0
        file_info = None
        for f in files:
            if f.get("downloadUrl") and any(
                f.get("name", "").endswith(ext)
                for ext in [".safetensors", ".ckpt", ".pt"]
            ):
                file_url = f["downloadUrl"]
                file_name = f.get("name")
                file_size_kb = f.get("sizeKB", 0) or 0
                file_info = f
                break
        if not file_url or not file_name or not file_info:
            QMessageBox.warning(
                self,
                "No Downloadable File",
                "No suitable file found for this version.",
            )
            return

        # Get baseModel (e.g., "SDXL 1.0") and type (e.g., "LORA")
        base_model = version.get("baseModel", "checkpoint")
        model_type = version.get(
            "type", self.model_info.get("type", "checkpoint")
        )
        subfolder = self._get_model_subfolder(model_type, file_info)
        base_path = os.path.expanduser(self.path_settings.base_path)
        model_dir = os.path.join(
            base_path, "art/models", base_model, subfolder
        )
        os.makedirs(model_dir, exist_ok=True)
        save_path = os.path.join(model_dir, file_name)

        # Store context for persistence after successful download
        self._current_version_data = version
        self._current_model_type = model_type
        self._current_file_info = file_info

        api_key = getattr(self.application_settings, "civit_ai_api_key", "")
        self._download_worker = FileDownloadWorker(
            url=file_url,
            save_path=save_path,
            api_key=api_key,
            total_size_bytes=int(file_size_kb * 1024),
        )
        self._download_thread = QThread(self)
        self._download_worker.moveToThread(self._download_thread)

        self._progress_dialog = QProgressDialog(
            f"Downloading {file_name}...\nDestination: {save_path}",
            "Cancel",
            0,
            100,
            self,
        )
        self._progress_dialog.setWindowTitle("Downloading Model")
        self._progress_dialog.setWindowModality(Qt.WindowModality.NonModal)
        self._progress_dialog.setMinimumDuration(0)
        self._progress_dialog.setAutoClose(True)
        self._progress_dialog.setAutoReset(True)
        self._progress_dialog.setRange(0, 0)

        # Wire signals
        self._download_worker.progress.connect(self._on_download_progress)
        self._download_worker.finished.connect(self._on_download_finished)
        self._download_worker.error.connect(self._on_download_failed_str)
        self._download_worker.canceled.connect(self._on_download_canceled)
        self._progress_dialog.canceled.connect(self._download_worker.cancel)

        # Ensure thread cleans up non-blocking
        self._download_thread.finished.connect(self._on_thread_finished)
        self._download_worker.finished.connect(self._download_thread.quit)
        self._download_worker.error.connect(self._download_thread.quit)
        self._download_worker.canceled.connect(self._download_thread.quit)

        # Start
        self._download_thread.started.connect(self._download_worker.run)
        self._download_thread.start()
        self._progress_dialog.show()


def show_download_model_dialog(parent, path_settings, application_settings):
    url, ok = QInputDialog.getText(
        parent, "Download Model from CivitAI", "Paste CivitAI model URL:"
    )
    if not ok or not url:
        return
    dialog = DownloadModelDialog(parent, path_settings, application_settings)
    dialog.fetch_and_display(url)
    dialog.exec()
