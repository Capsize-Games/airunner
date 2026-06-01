"""Template-backed CivitAI browser dialog."""

from __future__ import annotations

import hashlib
import os
from typing import Any, Optional
from urllib.parse import urlparse

from PySide6.QtCore import QSize, Qt, QThread, QUrl
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from airunner.components.application.utils.model_persistence import (
    persist_trigger_words,
)
from airunner.components.application.workers.qt_civitai_workers import (
    FileDownloadWorker,
    ImageLoaderWorker,
    ModelInfoWorker,
    ModelSearchWorker,
)
from airunner.enums import StableDiffusionVersion
from airunner.utils.application.ui_loader import load_ui_file

BASE_MODEL_VALUES = {
    "SDXL 1.0": "SDXL 1.0",
    "Z-Image Turbo": "ZImageTurbo",
}
MODEL_TYPE_VALUES = {
    "Checkpoint": "Checkpoint",
    "LoRA": "LORA",
    "Embedding": "TextualInversion",
}
MODEL_TYPES_BY_BASE = {
    "SDXL 1.0": ["Checkpoint", "LoRA", "Embedding"],
    "Z-Image Turbo": ["Checkpoint"],
}
CIVITAI_BASE_MODEL_MAP = {
    "ZImageTurbo": "Z-Image Turbo",
    "SDXL 1.0": "SDXL 1.0",
}
SUPPORTED_ZIMAGE_BASE_MODELS = {StableDiffusionVersion.Z_IMAGE_TURBO.value}


class DownloadModelDialog(QDialog):
    """Browse and download filtered CivitAI models."""

    def __init__(self, parent, path_settings, application_settings) -> None:
        super().__init__(parent)
        self.path_settings = path_settings
        self.application_settings = application_settings

        self._ui_root = self._load_ui()
        self.browser_splitter = self._bind_widget(QSplitter, "browser_splitter")
        self.search_line_edit = self._bind_widget(
            QLineEdit,
            "search_line_edit",
        )
        self.base_model_combo = self._bind_widget(
            QComboBox,
            "base_model_combo",
        )
        self.type_combo = self._bind_widget(QComboBox, "type_combo")
        self.search_button = self._bind_widget(QPushButton, "search_button")
        self.load_more_button = self._bind_widget(
            QPushButton,
            "load_more_button",
        )
        self.status_label = self._bind_widget(QLabel, "status_label")
        self.results_list = self._bind_widget(QListWidget, "results_list")
        self.selected_model_label = self._bind_widget(
            QLabel,
            "selected_model_label",
        )
        self.selected_model_meta_label = self._bind_widget(
            QLabel,
            "selected_model_meta_label",
        )
        self.preview_label = self._bind_widget(QLabel, "preview_label")
        self.sample_images_list = self._bind_widget(
            QListWidget,
            "sample_images_list",
        )
        self.description_browser = self._bind_widget(
            QTextBrowser,
            "description_browser",
        )
        self.version_combo = self._bind_widget(QComboBox, "version_combo")
        self.file_combo = self._bind_widget(QComboBox, "file_combo")
        self.open_model_button = self._bind_widget(
            QPushButton,
            "open_model_button",
        )
        self.download_button = self._bind_widget(
            QPushButton,
            "download_button",
        )
        self.button_box = self._bind_widget(
            QDialogButtonBox,
            "button_box",
        )

        self._search_thread: Optional[QThread] = None
        self._search_worker: Optional[ModelSearchWorker] = None
        self._info_thread: Optional[QThread] = None
        self._info_worker: Optional[ModelInfoWorker] = None
        self._download_thread: Optional[QThread] = None
        self._download_worker: Optional[FileDownloadWorker] = None
        self._progress_dialog: Optional[QProgressDialog] = None
        self._image_threads: dict[str, QThread] = {}
        self._image_workers: dict[str, ImageLoaderWorker] = {}
        self._pending_image_jobs: dict[str, str] = {}
        self._max_image_threads = 4
        self._result_items: dict[str, QListWidgetItem] = {}
        self._sample_items: dict[str, QListWidgetItem] = {}
        self._model_cache: dict[str, dict[str, Any]] = {}
        self._current_model: Optional[dict[str, Any]] = None
        self._current_version: Optional[dict[str, Any]] = None
        self._current_file: Optional[dict[str, Any]] = None
        self._next_cursor: Optional[str] = None
        self._append_results = False
        self._requested_model_id: Optional[str] = None
        self._initialized = False
        self._closing = False

        self._configure_ui()

    def showEvent(self, event) -> None:
        """Kick off the initial search once the dialog is visible."""
        super().showEvent(event)
        if self._initialized:
            return
        self._initialized = True
        self._start_search()

    def closeEvent(self, event) -> None:
        """Cancel one active download before the dialog closes."""
        self._closing = True
        self._pending_image_jobs.clear()
        if self._download_worker is not None:
            self._download_worker.cancel()
        self._stop_thread(self._search_thread)
        self._stop_thread(self._info_thread)
        self._stop_thread(self._download_thread)
        super().closeEvent(event)

    def _configure_ui(self) -> None:
        """Configure one browser dialog after loading the template."""
        self.setWindowTitle("CivitAI Browser")
        self.resize(1080, 720)
        self.browser_splitter.setSizes([360, 720])
        self.results_list.setIconSize(QSize(64, 64))
        self.sample_images_list.setIconSize(QSize(120, 120))
        self.sample_images_list.setViewMode(
            self.sample_images_list.ViewMode.IconMode
        )
        self.sample_images_list.setResizeMode(
            self.sample_images_list.ResizeMode.Adjust
        )
        self.sample_images_list.setSpacing(8)
        self.description_browser.setOpenExternalLinks(True)
        self.button_box.rejected.connect(self.reject)
        self.search_button.clicked.connect(self._start_search)
        self.load_more_button.clicked.connect(self._load_more)
        self.base_model_combo.currentTextChanged.connect(
            self._update_type_options
        )
        self.results_list.currentItemChanged.connect(
            self._on_result_selected
        )
        self.version_combo.currentIndexChanged.connect(
            self._on_version_changed
        )
        self.file_combo.currentIndexChanged.connect(
            self._on_file_changed
        )
        self.sample_images_list.currentItemChanged.connect(
            self._on_sample_selected
        )
        self.search_line_edit.returnPressed.connect(self._start_search)
        self.open_model_button.clicked.connect(self._open_current_model)
        self.download_button.clicked.connect(self._start_download)
        self.load_more_button.setEnabled(False)
        self.open_model_button.setEnabled(False)
        self.download_button.setEnabled(False)
        self._populate_base_models()
        self._update_type_options()

    def _populate_base_models(self) -> None:
        """Populate one constrained base-model selector."""
        self.base_model_combo.clear()
        for label in BASE_MODEL_VALUES:
            self.base_model_combo.addItem(label)

    def _update_type_options(self) -> None:
        """Refresh model-type options for one selected base model."""
        base_model = self.base_model_combo.currentText()
        current = self.type_combo.currentText()
        self.type_combo.blockSignals(True)
        self.type_combo.clear()
        for label in MODEL_TYPES_BY_BASE.get(base_model, ["Checkpoint"]):
            self.type_combo.addItem(label)
        match = self.type_combo.findText(current)
        self.type_combo.setCurrentIndex(max(match, 0))
        self.type_combo.blockSignals(False)

    def _start_search(self) -> None:
        """Start one new filtered browser search."""
        self._append_results = False
        self._next_cursor = None
        self._run_search_worker(cursor=None)

    def _load_more(self) -> None:
        """Append the next page of results when the API exposes one."""
        if not self._next_cursor:
            return
        self._append_results = True
        self._run_search_worker(cursor=self._next_cursor)

    def _run_search_worker(self, cursor: Optional[str]) -> None:
        """Run one search worker with the current filter set."""
        if self._search_thread is not None:
            return
        self.status_label.setText("Loading models...")
        self.load_more_button.setEnabled(False)
        self._search_worker = ModelSearchWorker(
            query=self.search_line_edit.text().strip(),
            base_models=[BASE_MODEL_VALUES[self.base_model_combo.currentText()]],
            model_types=[MODEL_TYPE_VALUES[self.type_combo.currentText()]],
            limit=20,
            cursor=cursor,
            api_key=self._api_key,
        )
        self._search_thread = self._start_worker_thread(
            worker=self._search_worker,
            success_signal=self._search_worker.fetched,
            success_slot=self._on_search_results,
            error_signal=self._search_worker.error,
            error_slot=self._on_search_error,
            clear_callback=self._clear_search_worker,
        )

    def _on_search_results(self, payload: dict[str, Any]) -> None:
        """Render one browser search response in the results list."""
        if not self._append_results:
            self.results_list.clear()
            self._result_items.clear()
        items = payload.get("items", []) or []
        self._next_cursor = (
            payload.get("metadata", {}) or {}
        ).get("nextCursor")
        self.load_more_button.setEnabled(bool(self._next_cursor))
        for model in items:
            self._add_result_item(model)
        count = self.results_list.count()
        if count == 0:
            self.status_label.setText("No matching models found.")
            self._clear_details()
            return
        self.status_label.setText(f"Showing {count} filtered models")
        if self.results_list.currentItem() is None:
            self.results_list.setCurrentRow(0)

    def _add_result_item(self, model: dict[str, Any]) -> None:
        """Append one model row and queue its thumbnail load."""
        model_id = str(model.get("id") or "")
        creator = (model.get("creator") or {}).get("username") or "Unknown"
        model_type = model.get("type") or self.ui.type_combo.currentText()
        base_model = ""
        if model.get("modelVersions"):
            base_model = str(model["modelVersions"][0].get("baseModel", ""))
        text = f"{model.get('name', 'Unknown')}\n{creator} • {model_type}"
        if base_model:
            text = f"{text} • {base_model}"
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, model_id)
        self.results_list.addItem(item)
        self._result_items[model_id] = item
        image_url = self._model_image_url(model)
        if image_url:
            self._start_image_worker(f"result:{model_id}", image_url)

    def _on_search_error(self, message: str) -> None:
        """Show one browser search failure without closing the dialog."""
        self.status_label.setText("Failed to load models.")
        QMessageBox.critical(self, "CivitAI", message)

    def _on_result_selected(self, current, _previous) -> None:
        """Fetch one selected model into the detail pane."""
        if current is None:
            self._clear_details()
            return
        model_id = str(current.data(Qt.ItemDataRole.UserRole) or "")
        if not model_id:
            return
        cache_key = self._model_cache_key(model_id)
        if cache_key in self._model_cache:
            self._show_model(self._model_cache[cache_key])
            return
        self._requested_model_id = model_id
        self.selected_model_label.setText("Loading model details...")
        self._info_worker = ModelInfoWorker(
            model_id=model_id,
            base_models=[BASE_MODEL_VALUES[self.base_model_combo.currentText()]],
            model_types=[MODEL_TYPE_VALUES[self.type_combo.currentText()]],
            api_key=self._api_key,
        )
        self._info_thread = self._start_worker_thread(
            worker=self._info_worker,
            success_signal=self._info_worker.fetched,
            success_slot=self._on_model_info,
            error_signal=self._info_worker.error,
            error_slot=self._on_model_error,
            clear_callback=self._clear_info_worker,
        )

    def _on_model_info(self, model: dict[str, Any]) -> None:
        """Store and display one fetched model payload."""
        model_id = str(model.get("id") or "")
        self._model_cache[self._model_cache_key(model_id)] = model
        if model_id != self._requested_model_id:
            return
        self._show_model(model)

    def _show_model(self, model: dict[str, Any]) -> None:
        """Render one selected model in the detail pane."""
        self._current_model = model
        self.selected_model_label.setText(model.get("name", "Unknown"))
        self.selected_model_meta_label.setText(self._model_meta(model))
        description = model.get("description") or "<p>No description.</p>"
        self.description_browser.setHtml(description)
        self.open_model_button.setEnabled(True)
        self.version_combo.blockSignals(True)
        self.version_combo.clear()
        selected_id = ((model.get("selectedVersion") or {}).get("id"))
        selected_index = 0
        for index, version in enumerate(model.get("modelVersions", [])):
            label = str(version.get("name") or f"Version {index + 1}")
            self.version_combo.addItem(label, version)
            if selected_id is not None and version.get("id") == selected_id:
                selected_index = index
        self.version_combo.setCurrentIndex(selected_index)
        self.version_combo.blockSignals(False)
        self._on_version_changed(selected_index)

    def _on_model_error(self, message: str) -> None:
        """Show one model-detail failure and keep browsing enabled."""
        self.selected_model_label.setText("Failed to load model details")
        QMessageBox.critical(self, "CivitAI", message)

    def _on_version_changed(self, _index: int) -> None:
        """Refresh files and preview images for one selected version."""
        version = self.version_combo.currentData()
        self._current_version = version if isinstance(version, dict) else None
        self.file_combo.blockSignals(True)
        self.file_combo.clear()
        if self._current_version is None:
            self.file_combo.blockSignals(False)
            self._clear_samples()
            return
        for file_info in self._current_version.get("files", []):
            self.file_combo.addItem(self._file_label(file_info), file_info)
        self.file_combo.blockSignals(False)
        self._on_file_changed(self.file_combo.currentIndex())
        self._populate_samples(self._current_version)

    def _on_file_changed(self, _index: int) -> None:
        """Store one selected file and enable download when possible."""
        file_info = self.file_combo.currentData()
        self._current_file = file_info if isinstance(file_info, dict) else None
        self.download_button.setEnabled(self._current_file is not None)

    def _populate_samples(self, version: dict[str, Any]) -> None:
        """Render sample-image entries for one selected version."""
        self._clear_samples()
        images = [img for img in version.get("images", []) if img.get("url")]
        for index, image in enumerate(images[:6]):
            url = str(image.get("url"))
            item = QListWidgetItem(f"Sample {index + 1}")
            item.setData(Qt.ItemDataRole.UserRole, url)
            self.sample_images_list.addItem(item)
            self._sample_items[url] = item
            self._start_image_worker(f"sample:{url}", url)
        if self.sample_images_list.count() > 0:
            self.sample_images_list.setCurrentRow(0)
        else:
            self.preview_label.setText("No preview available")

    def _clear_samples(self) -> None:
        """Clear one sample-image strip and its preview state."""
        self.sample_images_list.clear()
        self._sample_items.clear()
        self.preview_label.setPixmap(QPixmap())
        self.preview_label.setText("No preview selected")

    def _on_sample_selected(self, current, _previous) -> None:
        """Show one selected sample image in the preview area."""
        if current is None:
            self.preview_label.setText("No preview selected")
            return
        url = str(current.data(Qt.ItemDataRole.UserRole) or "")
        if not url:
            return
        cache_path = self._image_cache_path(url)
        if os.path.exists(cache_path):
            self._set_preview(cache_path)
            return
        self.preview_label.setText("Loading preview...")

    def _start_download(self) -> None:
        """Start one daemon-backed download for the selected file."""
        if self._download_thread is not None or self._current_file is None:
            return
        if self._current_version is None or self._current_model is None:
            return
        file_name = str(self._current_file.get("name") or "")
        file_url = str(self._current_file.get("downloadUrl") or "")
        file_size_kb = int(self._current_file.get("sizeKB") or 0)
        if not file_name or not file_url:
            QMessageBox.warning(self, "CivitAI", "No downloadable file found.")
            return
        base_model = self._normalize_base_model(
            str(self._current_version.get("baseModel") or "")
        )
        if (
            base_model.startswith("Z-Image")
            and base_model not in SUPPORTED_ZIMAGE_BASE_MODELS
        ):
            QMessageBox.warning(self, "CivitAI", "Unsupported base model.")
            return
        model_type = str(self._current_model.get("type") or "Checkpoint")
        subfolder = self._model_subfolder(model_type, self._current_file)
        model_dir = os.path.join(
            os.path.expanduser(self.path_settings.base_path),
            "art/models",
            base_model,
            subfolder,
        )
        os.makedirs(model_dir, exist_ok=True)
        save_path = os.path.join(model_dir, file_name)
        self._download_worker = FileDownloadWorker(
            url=file_url,
            save_path=save_path,
            api_key=self._api_key,
            total_size_bytes=file_size_kb * 1024,
        )
        self._download_thread = self._start_worker_thread(
            worker=self._download_worker,
            success_signal=self._download_worker.finished,
            success_slot=self._on_download_finished,
            error_signal=self._download_worker.error,
            error_slot=self._on_download_failed,
            clear_callback=self._clear_download_worker,
            canceled_signal=self._download_worker.canceled,
            canceled_slot=self._on_download_canceled,
        )
        self._progress_dialog = QProgressDialog(
            f"Downloading {file_name}...\nDestination: {save_path}",
            "Cancel",
            0,
            100,
            self,
        )
        self._progress_dialog.setWindowTitle("Downloading Model")
        self._progress_dialog.setMinimumDuration(0)
        self._progress_dialog.setRange(0, 0)
        self._progress_dialog.canceled.connect(self._download_worker.cancel)
        self._download_worker.progress.connect(self._on_download_progress)
        self._progress_dialog.show()

    def _on_download_progress(self, current: int, total: int) -> None:
        """Mirror one daemon progress update into the progress dialog."""
        if self._progress_dialog is None:
            return
        if total <= 0:
            self._progress_dialog.setRange(0, 0)
            return
        if self._progress_dialog.maximum() == 0:
            self._progress_dialog.setRange(0, 100)
        percent = max(0, min(100, int((current / total) * 100)))
        self._progress_dialog.setValue(percent)

    def _on_download_finished(self, save_path: str) -> None:
        """Persist trigger words after one successful download."""
        self._close_progress_dialog()
        if self._current_version and self._current_file and self._current_model:
            persist_trigger_words(
                self._current_version,
                str(self._current_model.get("type") or "Checkpoint"),
                self._current_file,
                save_path,
            )

    def _on_download_failed(self, message: str) -> None:
        """Close progress UI and surface one download failure."""
        self._close_progress_dialog()
        QMessageBox.critical(self, "Download Failed", message)

    def _on_download_canceled(self) -> None:
        """Close progress UI after one canceled download."""
        self._close_progress_dialog()

    def _open_current_model(self) -> None:
        """Open one selected model page in the default browser."""
        if self._current_model is None:
            return
        model_id = self._current_model.get("id")
        if model_id is None:
            return
        QDesktopServices.openUrl(QUrl(f"https://civitai.com/models/{model_id}"))

    def _start_image_worker(self, key: str, url: str) -> None:
        """Queue one safe thumbnail or sample-image fetch."""
        if self._closing:
            return
        if key in self._image_threads or key in self._pending_image_jobs:
            return
        if len(self._image_threads) >= self._max_image_threads:
            self._pending_image_jobs[key] = url
            return
        worker = ImageLoaderWorker(
            key=key,
            url=url,
            cache_path=self._image_cache_path(url),
        )
        app = QApplication.instance()
        thread = QThread(app)
        worker.moveToThread(thread)
        worker.loaded.connect(self._on_image_loaded)
        worker.error.connect(self._on_image_error)
        worker.loaded.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda key=key: self._clear_image_worker(key))
        thread.started.connect(worker.run)
        self._image_threads[key] = thread
        self._image_workers[key] = worker
        thread.start()

    def _on_image_loaded(self, key: str, cache_path: str) -> None:
        """Update one result or preview image from the local cache."""
        if key.startswith("result:"):
            self._set_result_icon(key[7:], cache_path)
            return
        if key.startswith("sample:"):
            url = key[7:]
            self._set_sample_icon(url, cache_path)
            current = self.sample_images_list.currentItem()
            if current is not None and current.data(Qt.ItemDataRole.UserRole) == url:
                self._set_preview(cache_path)

    def _on_image_error(self, key: str, _message: str) -> None:
        """Ignore one image failure and keep browsing responsive."""
        return

    def _start_next_image_worker(self) -> None:
        """Start the next queued image fetch when capacity is available."""
        if self._closing:
            return
        while self._pending_image_jobs:
            if len(self._image_threads) >= self._max_image_threads:
                return
            key, url = next(iter(self._pending_image_jobs.items()))
            self._pending_image_jobs.pop(key, None)
            self._start_image_worker(key, url)

    def _set_result_icon(self, model_id: str, cache_path: str) -> None:
        """Apply one loaded thumbnail to the search-results row."""
        item = self._result_items.get(model_id)
        if item is None:
            return
        pixmap = QPixmap(cache_path)
        if pixmap.isNull():
            return
        item.setIcon(QIcon(pixmap.scaled(64, 64, Qt.KeepAspectRatio)))

    def _set_sample_icon(self, url: str, cache_path: str) -> None:
        """Apply one loaded sample image to the sample strip."""
        item = self._sample_items.get(url)
        if item is None:
            return
        pixmap = QPixmap(cache_path)
        if pixmap.isNull():
            return
        item.setIcon(QIcon(pixmap.scaled(120, 120, Qt.KeepAspectRatio)))

    def _set_preview(self, cache_path: str) -> None:
        """Scale one cached image into the preview label."""
        pixmap = QPixmap(cache_path)
        if pixmap.isNull():
            self.preview_label.setText("No preview available")
            return
        self.preview_label.setText("")
        self.preview_label.setPixmap(
            pixmap.scaled(
                self.preview_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

    def _clear_details(self) -> None:
        """Reset the detail pane when no model is selected."""
        self._current_model = None
        self._current_version = None
        self._current_file = None
        self.selected_model_label.setText("Select a model")
        self.selected_model_meta_label.setText("")
        self.description_browser.clear()
        self.open_model_button.setEnabled(False)
        self.version_combo.clear()
        self.file_combo.clear()
        self.download_button.setEnabled(False)
        self._clear_samples()

    def _model_cache_key(self, model_id: str) -> str:
        """Return one cache key for the active filter set and model id."""
        return (
            f"{model_id}:{self.base_model_combo.currentText()}:"
            f"{self.type_combo.currentText()}"
        )

    def _model_meta(self, model: dict[str, Any]) -> str:
        """Build one compact metadata line for the detail pane."""
        stats = model.get("stats") or {}
        creator = (model.get("creator") or {}).get("username") or "Unknown"
        downloads = int(stats.get("downloadCount") or 0)
        rating = int(stats.get("favoriteCount") or 0)
        return (
            f"{creator} • {model.get('type', 'Unknown')} • "
            f"{downloads} downloads • {rating} favorites"
        )

    def _model_image_url(self, model: dict[str, Any]) -> str:
        """Return one primary preview image URL for a model row."""
        for version in model.get("modelVersions", []):
            for image in version.get("images", []):
                url = image.get("url") or image.get("thumbnailUrl")
                if url:
                    return str(url)
        return ""

    def _file_label(self, file_info: dict[str, Any]) -> str:
        """Build one file selector label with size information."""
        size_kb = float(file_info.get("sizeKB") or 0)
        size_label = ""
        if size_kb > 0:
            if size_kb < 1024:
                size_label = f"{size_kb:.0f} KB"
            elif size_kb < 1024 * 1024:
                size_label = f"{size_kb / 1024:.1f} MB"
            else:
                size_label = f"{size_kb / (1024 * 1024):.2f} GB"
        suffix = f" ({size_label})" if size_label else ""
        return f"{file_info.get('name', 'Unknown file')}{suffix}"

    def _image_cache_path(self, url: str) -> str:
        """Return one app-scoped cache path for a remote preview image."""
        suffix = os.path.splitext(urlparse(url).path)[1] or ".img"
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return os.path.join(
            os.path.expanduser(self.path_settings.base_path),
            "cache",
            "civitai",
            f"{digest}{suffix}",
        )

    def _load_ui(self) -> QWidget:
        """Load and embed the browser template widget into the dialog."""
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "templates",
            "civitai_browser_dialog.ui",
        )
        ui_root = load_ui_file(ui_path, self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(ui_root)
        return ui_root

    def _bind_widget(self, widget_type, object_name: str):
        """Return one required child widget from the loaded UI tree."""
        widget = self._ui_root.findChild(widget_type, object_name)
        if widget is None:
            raise RuntimeError(f"Missing UI widget: {object_name}")
        return widget

    def _normalize_base_model(self, base_model: str) -> str:
        """Normalize one CivitAI base model into the local folder name."""
        return CIVITAI_BASE_MODEL_MAP.get(base_model, base_model)

    def _model_subfolder(self, model_type: str, file_info: dict[str, Any]) -> str:
        """Map one browser selection onto the AIRunner art-model folder."""
        normalized_type = model_type.strip().upper()
        if normalized_type == "LORA":
            return "lora"
        if normalized_type == "TEXTUALINVERSION":
            return "embeddings"
        if normalized_type == "CHECKPOINT":
            return "txt2img"
        name = str(file_info.get("name") or "").lower()
        if "inpaint" in name:
            return "inpaint"
        return normalized_type.lower() or "txt2img"

    def _start_worker_thread(
        self,
        *,
        worker,
        success_signal,
        success_slot,
        error_signal,
        error_slot,
        clear_callback,
        canceled_signal=None,
        canceled_slot=None,
    ) -> QThread:
        """Move one QObject worker onto a QThread and start it."""
        app = QApplication.instance()
        thread = QThread(app)
        worker.moveToThread(thread)
        success_signal.connect(success_slot)
        error_signal.connect(error_slot)
        success_signal.connect(thread.quit)
        error_signal.connect(thread.quit)
        if canceled_signal is not None and canceled_slot is not None:
            canceled_signal.connect(canceled_slot)
            canceled_signal.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(clear_callback)
        thread.started.connect(worker.run)
        thread.start()
        return thread

    def _stop_thread(self, thread: Optional[QThread]) -> None:
        """Quit one thread and wait briefly when it still exists."""
        if thread is None:
            return
        thread.quit()
        thread.wait(1000)

    def _clear_search_worker(self) -> None:
        """Clear one completed search worker reference."""
        self._search_thread = None
        self._search_worker = None

    def _clear_info_worker(self) -> None:
        """Clear one completed detail worker reference."""
        self._info_thread = None
        self._info_worker = None

    def _clear_download_worker(self) -> None:
        """Clear one completed download worker reference."""
        self._download_thread = None
        self._download_worker = None

    def _clear_image_worker(self, key: str) -> None:
        """Drop one completed image worker reference."""
        thread = self._image_threads.pop(key, None)
        self._image_workers.pop(key, None)
        self._pending_image_jobs.pop(key, None)
        if thread is None:
            return
        self._start_next_image_worker()

    def _close_progress_dialog(self) -> None:
        """Close and forget the active progress dialog."""
        if self._progress_dialog is not None:
            self._progress_dialog.close()
            self._progress_dialog = None

    @property
    def _api_key(self) -> str:
        """Return the configured CivitAI API key."""
        return str(
            getattr(self.application_settings, "civit_ai_api_key", "")
            or ""
        )


def show_download_model_dialog(parent, path_settings, application_settings):
    """Open the CivitAI browser when the provider is enabled."""
    from airunner.components.application.gui.dialogs.privacy_consent_dialog import (
        is_civitai_allowed,
    )

    if not is_civitai_allowed():
        QMessageBox.warning(
            parent,
            "Downloads Disabled",
            "CivitAI downloads are disabled in privacy settings.\n\n"
            "You can enable them in Preferences -> Privacy & Security -> "
            "External Services.",
        )
        return

    dialog = DownloadModelDialog(parent, path_settings, application_settings)
    dialog.exec()
