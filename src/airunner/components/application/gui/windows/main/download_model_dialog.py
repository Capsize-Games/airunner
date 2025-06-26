"""
Dialog and logic for downloading models from CivitAI by URL.
"""

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
from airunner.components.art.managers.stablediffusion.civit_ai_api import (
    CivitAIAPI,
)
from airunner.components.application.workers.civit_ai_download_worker import (
    CivitAIDownloadWorker,
)


class DownloadModelDialog(QDialog):
    """Dialog for downloading a model from CivitAI by URL."""

    def __init__(self, parent, path_settings, application_settings):
        super().__init__(parent)
        self.setWindowTitle("CivitAI Model Details")
        self.path_settings = path_settings
        self.application_settings = application_settings
        self.model_info = None
        self._setup_ui()

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.list_widget = QListWidget(self)
        self.download_btn = QPushButton("Download Selected Version", self)
        self.layout.addWidget(self.list_widget)
        self.layout.addWidget(self.download_btn)
        self.download_btn.clicked.connect(self._start_download)

    def fetch_and_display(self, url):
        try:
            api_key = getattr(
                self.application_settings, "civit_ai_api_key", None
            )
            civitai = CivitAIAPI(api_key=api_key)
            self.model_info = civitai.get_model_info(url)
        except Exception as e:
            QMessageBox.critical(
                self, "CivitAI Error", f"Failed to fetch model info: {e}"
            )
            self.reject()
            return
        name = self.model_info.get("name", "Unknown")
        desc = self.model_info.get("description", "")
        self.layout.insertWidget(0, QLabel(f"<b>{name}</b>"))
        if desc:
            self.layout.insertWidget(1, QLabel(desc))
        versions = self.model_info.get("modelVersions", [])
        for v in versions:
            item = QListWidgetItem(
                f"Version {v.get('id')}: {v.get('name', '')}"
            )
            item.setData(1000, v)
            self.list_widget.addItem(item)
        self.layout.insertWidget(2, QLabel("Select a version to download:"))

    def _start_download(self):
        selected = self.list_widget.currentItem()
        if not selected:
            QMessageBox.warning(
                self, "No Selection", "Please select a version."
            )
            return
        version = selected.data(1000)
        files = version.get("files", [])
        file_url = None
        file_name = None
        file_size = 0
        for f in files:
            if f.get("downloadUrl") and any(
                f.get("name", "").endswith(ext)
                for ext in [".safetensors", ".ckpt", ".pt"]
            ):
                file_url = f["downloadUrl"]
                file_name = f.get("name")
                file_size = f.get("sizeKB", 0)
                break
        if not file_url:
            QMessageBox.warning(
                self,
                "No Downloadable File",
                "No suitable file found for this version.",
            )
            return
        model_type = (version.get("type") or "checkpoint").lower()
        base_path = os.path.expanduser(self.path_settings.base_path)
        model_dir = os.path.join(base_path, "art/models", model_type)
        os.makedirs(model_dir, exist_ok=True)
        save_path = os.path.join(model_dir, file_name)
        worker = CivitAIDownloadWorker()
        thread = QThread(self)
        worker.moveToThread(thread)
        worker.add_to_queue((file_url, save_path, file_size))
        progress_dialog = QProgressDialog(
            f"Downloading {file_name}...\nDestination: {save_path}",
            "Cancel",
            0,
            100,
            self,
        )
        progress_dialog.setWindowTitle("Downloading Model")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setMinimumDuration(0)

        def on_progress(current, total):
            percent = int((current / total) * 100) if total else 0
            progress_dialog.setValue(percent)
            progress_dialog.setLabelText(
                f"Downloading {file_name}...\nDestination: {save_path}"
            )

        def on_finished():
            progress_dialog.close()
            thread.quit()
            thread.wait()
            QMessageBox.information(
                self, "Download Complete", f"Model downloaded to: {save_path}"
            )

        def on_failed(error):
            progress_dialog.close()
            thread.quit()
            thread.wait()
            QMessageBox.critical(
                self,
                "Download Failed",
                f"Error: {str(error) or 'Unknown error'}",
            )

        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        worker.failed.connect(on_failed)
        progress_dialog.canceled.connect(worker.cancel)
        thread.started.connect(worker.download)
        thread.start()
        progress_dialog.exec()


# Helper function to launch the dialog from MainWindow


def show_download_model_dialog(parent, path_settings, application_settings):
    url, ok = QInputDialog.getText(
        parent, "Download Model from CivitAI", "Paste CivitAI model URL:"
    )
    if not ok or not url:
        return
    dialog = DownloadModelDialog(parent, path_settings, application_settings)
    dialog.fetch_and_display(url)
    dialog.exec()
