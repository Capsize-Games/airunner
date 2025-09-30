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
    QScrollArea,
    QWidget,
    QSizePolicy,
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
        # Start at a sensible size so very long descriptions don't grow the
        # dialog off-screen. The dialog remains resizable so the user can
        # expand it if they wish.
        self.resize(700, 520)
        self.setMinimumSize(520, 340)
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

        # Widgets we may need to update on resize so text wraps instead of
        # causing horizontal scrollbars.
        self._desc_scroll: Optional[QScrollArea] = None
        self._desc_label: Optional[QLabel] = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        self.layout = QVBoxLayout(self)
        self.list_widget = QListWidget(self)
        # allow the list to expand within the dialog and to show its own
        # scrollbars when needed
        self.list_widget.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        self.download_btn = QPushButton("Download Selected Version", self)
        self.layout.addWidget(self.list_widget)
        self.layout.addWidget(self.download_btn)
        self.download_btn.clicked.connect(self._start_download)

    def resizeEvent(self, event) -> None:
        """Ensure the description label wraps to the current viewport width.

        QLabel will otherwise try to expand horizontally which can cause a
        horizontal scrollbar to appear. By updating the label's maximum width
        to match the scroll viewport we force word-wrapping.
        """
        try:
            super().resizeEvent(event)
        except Exception:
            pass
        try:
            if self._desc_scroll and self._desc_label:
                vw = self._desc_scroll.viewport().width()
                # leave a small margin
                self._desc_label.setMaximumWidth(max(40, vw - 4))
        except Exception:
            # don't let resize issues crash the UI
            pass

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
        # Insert the model name as a label (rich text allowed)
        name_label = QLabel(f"<b>{name}</b>")
        name_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.layout.insertWidget(0, name_label)

        # Description can be very long — place it into a scroll area so the
        # dialog doesn't expand to fit the entire text. The scroll area is
        # given a reasonable maximum height and the label inside it will
        # word-wrap.
        if desc:
            desc_label = QLabel(desc)
            desc_label.setWordWrap(True)
            desc_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            desc_label.setSizePolicy(
                QSizePolicy.Preferred, QSizePolicy.Preferred
            )

            desc_container = QWidget()
            desc_container_layout = QVBoxLayout(desc_container)
            desc_container_layout.setContentsMargins(0, 0, 0, 0)
            desc_container_layout.addWidget(desc_label)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(desc_container)
            # Limit initial height so the dialog stays on-screen; user can
            # expand the dialog to see more.
            scroll.setMaximumHeight(220)
            self.layout.insertWidget(1, scroll)

            # Keep references so we can adjust maximum width on resize and
            # avoid horizontal scrollbars. Update immediately to match the
            # current size.
            self._desc_scroll = scroll
            self._desc_label = desc_label
            try:
                vw = scroll.viewport().width()
                self._desc_label.setMaximumWidth(max(40, vw - 4))
            except Exception:
                pass
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
            # Close and hide the progress UI immediately so further progress
            # updates can't make it reappear.
            if self._progress_dialog is not None:
                try:
                    self._progress_dialog.close()
                except Exception:
                    pass
        except Exception:
            pass

        # Try to stop the worker thread cleanly. Avoid calling terminate()
        # because it can crash the application (abort). Instead request the
        # worker cancel and quit the thread, then wait a short time.
        if self._download_thread is not None:
            try:
                # Disconnect worker signals so they can't call back into this
                # dialog after we've closed the UI.
                try:
                    if self._download_worker is not None:
                        try:
                            self._download_worker.progress.disconnect()
                        except Exception:
                            pass
                        try:
                            self._download_worker.finished.disconnect()
                        except Exception:
                            pass
                        try:
                            self._download_worker.error.disconnect()
                        except Exception:
                            pass
                        try:
                            self._download_worker.canceled.disconnect()
                        except Exception:
                            pass
                except Exception:
                    pass

                try:
                    # Ask the thread to quit; the worker should notice the
                    # cancel flag and exit its loop. Wait briefly for it to
                    # finish.
                    self._download_thread.quit()
                    try:
                        self._download_thread.wait(2000)
                    except Exception:
                        # If wait isn't available, just continue — don't
                        # attempt to forcefully terminate the thread.
                        logger.debug(
                            "Thread wait not available", exc_info=True
                        )
                except Exception:
                    logger.debug("Thread quit failed", exc_info=True)
            except Exception:
                # Protect against any unexpected errors while disconnecting
                # or quitting the thread; we don't want this to crash the app.
                logger.debug(
                    "Error while cleaning up download thread", exc_info=True
                )

        # Drop the reference to the progress dialog so progress handlers
        # return early and cannot re-show it.
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
                # Request worker cancel; this sets the worker flag but may not
                # stop a blocking network call immediately. Call cancel first
                # then run cleanup which will escalate if the thread doesn't
                # stop in a short time.
                try:
                    self._download_worker.cancel()
                except Exception:
                    logger.debug("Worker cancel call failed", exc_info=True)
        except Exception:
            logger.debug("Cancel call failed", exc_info=True)
        # Perform cleanup (close dialog, stop thread). After cleanup, try to
        # remove any partial file the worker may have left behind.
        self._cleanup_download()
        try:
            sp = getattr(self._download_worker, "save_path", None)
            if sp and os.path.exists(sp):
                try:
                    os.remove(sp)
                except Exception:
                    logger.debug(
                        "Failed to remove partial download %s",
                        sp,
                        exc_info=True,
                    )
        except Exception:
            logger.debug("Post-cancel cleanup failed", exc_info=True)

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
        # Use a local handler so we can close the progress dialog and
        # perform cleanup immediately when the user presses Cancel. If we
        # simply call the worker.cancel() the worker may be blocked and
        # continue emitting progress, which can cause the dialog to reappear.
        self._progress_dialog.canceled.connect(
            self._on_progress_dialog_canceled
        )

        # Ensure thread cleans up non-blocking
        self._download_thread.finished.connect(self._on_thread_finished)
        self._download_worker.finished.connect(self._download_thread.quit)
        self._download_worker.error.connect(self._download_thread.quit)
        self._download_worker.canceled.connect(self._download_thread.quit)

        # Start
        self._download_thread.started.connect(self._download_worker.run)
        self._download_thread.start()
        self._progress_dialog.show()

    def _on_progress_dialog_canceled(self) -> None:
        """Handle user pressing Cancel on the QProgressDialog.

        Request worker cancellation and perform immediate cleanup so the
        progress dialog cannot be re-shown by in-flight progress updates.
        """
        try:
            if self._download_worker:
                try:
                    self._download_worker.cancel()
                except Exception:
                    logger.debug("Worker cancel failed", exc_info=True)
        except Exception:
            logger.debug("Error requesting worker cancel", exc_info=True)

        # Immediately cleanup UI state so progress updates won't re-show
        # the dialog. We also attempt to remove any partial file right
        # away to respect the user's cancellation intent.
        try:
            sp = getattr(self._download_worker, "save_path", None)
        except Exception:
            sp = None

        self._cleanup_download()

        # Try to remove partial file if present
        try:
            if sp and os.path.exists(sp):
                try:
                    os.remove(sp)
                except Exception:
                    logger.debug(
                        "Failed to remove partial download %s",
                        sp,
                        exc_info=True,
                    )
        except Exception:
            logger.debug(
                "Post-cancel partial file removal failed", exc_info=True
            )

    def closeEvent(self, event) -> None:
        """Ensure we don't destroy a running QThread when the dialog closes.

        If a download is running, request cancellation and wait briefly. If
        the thread is still running after a short timeout, reparent it so it
        isn't destroyed with the dialog and inform the user the download will
        continue in the background.
        """
        try:
            if (
                self._download_thread is not None
                and self._download_thread.isRunning()
            ):
                # Ask worker to cancel cooperatively
                try:
                    if self._download_worker is not None:
                        self._download_worker.cancel()
                except Exception:
                    logger.debug(
                        "Failed to request worker cancel", exc_info=True
                    )

                # Try to quit the thread and wait shortly
                try:
                    self._download_thread.quit()
                    try:
                        self._download_thread.wait(2000)
                    except Exception:
                        logger.debug(
                            "Thread wait not available or interrupted",
                            exc_info=True,
                        )
                except Exception:
                    logger.debug("Thread quit failed", exc_info=True)

                # If still running, detach the thread from this dialog to avoid
                # Qt complaining about destruction while running.
                if self._download_thread.isRunning():
                    try:
                        # Reparent the thread to the application so it won't be
                        # deleted when this dialog is destroyed.
                        self._download_thread.setParent(None)
                    except Exception:
                        logger.debug(
                            "Failed to reparent download thread", exc_info=True
                        )

                    # Let the user know the download will continue in background
                    try:
                        QMessageBox.information(
                            self,
                            "Download Continuing",
                            "The download will continue in the background. You can monitor downloads from the main application.",
                        )
                    except Exception:
                        pass

                # Clear local references so the dialog can be destroyed safely.
                self._download_thread = None
                self._download_worker = None
        except Exception:
            logger.debug("Error during dialog close handling", exc_info=True)

        # Proceed with normal close
        try:
            super().closeEvent(event)
        except Exception:
            event.accept()


def show_download_model_dialog(parent, path_settings, application_settings):
    url, ok = QInputDialog.getText(
        parent, "Download Model from CivitAI", "Paste CivitAI model URL:"
    )
    if not ok or not url:
        return
    dialog = DownloadModelDialog(parent, path_settings, application_settings)
    dialog.fetch_and_display(url)
    dialog.exec()
