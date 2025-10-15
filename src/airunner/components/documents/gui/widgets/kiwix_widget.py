import os
import re
import json
import pprint
import tempfile
import webbrowser
import urllib.parse
import datetime
import requests

from PySide6.QtCore import Signal, Qt, QObject, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QListWidgetItem,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QMessageBox,
    QFileDialog,
    QProgressDialog,
)

from airunner.utils.application.create_worker import create_worker
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.documents.data.scan_zimfiles import scan_zimfiles
from airunner.components.documents.data.models.zimfile import ZimFile
from airunner.components.documents.kiwix_api import KiwixAPI


class KiwixWidget(BaseWidget):
    """Widget for managing Kiwix ZIM files."""

    zimDownloadFinished = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.signal_handlers = {}
        self.setup_ui()

    def setup_ui(self):
        """Setup UI references from parent widget."""
        # These should be set by the parent widget after initialization
        self.local_zims_list = None
        self.search_results_list = None
        self.kiwix_search_bar = None
        self.kiwix_lang_combo = None
        self.kiwix_search_button = None
        self.show_local_zims_only = True

    def initialize(
        self,
        local_zims_list,
        search_results_list,
        kiwix_search_bar,
        kiwix_lang_combo,
        kiwix_search_button,
    ):
        """Initialize with UI components from parent."""
        self.local_zims_list = local_zims_list
        self.search_results_list = search_results_list
        self.kiwix_search_bar = kiwix_search_bar
        self.kiwix_lang_combo = kiwix_lang_combo
        self.kiwix_search_button = kiwix_search_button

        # Connect signals
        self.kiwix_search_bar.returnPressed.connect(
            self.on_kiwix_search_clicked
        )
        self.kiwix_search_button.clicked.connect(self.on_kiwix_search_clicked)
        self.kiwix_lang_combo.currentTextChanged.connect(
            self.refresh_kiwix_lists
        )
        self.zimDownloadFinished.connect(self.refresh_kiwix_lists)

        # Initial refresh
        self.refresh_kiwix_lists()

    def on_kiwix_search_clicked(self):
        """Handle search button click."""
        self.show_local_zims_only = False
        self.refresh_kiwix_lists()

    def on_kiwix_search_changed(self, text):
        """Handle search text changes."""
        if not text.strip():
            self.show_local_zims_only = True
            self.refresh_kiwix_lists()

    def refresh_kiwix_lists(self):
        """Refresh both local and remote ZIM lists."""
        self.refresh_local_zims_list()
        self.refresh_search_results_list()

    def refresh_local_zims_list(self):
        """Refresh the list of locally installed ZIM files."""
        zim_dir = os.path.join(
            os.path.expanduser(self.path_settings.base_path), "zim"
        )
        scan_zimfiles(zim_dir)
        self.local_zims_list.clear()
        local_zims = ZimFile.objects.all()

        for zim in sorted(local_zims, key=lambda z: z.name.lower()):
            meta = {
                "title": zim.title,
                "summary": zim.summary,
                "updated": zim.updated,
            }
            fname = zim.name
            fpath = zim.path
            size = zim.size

            row_widget = self._create_local_zim_widget(
                fname, fpath, size, meta
            )
            item = QListWidgetItem()
            item.setSizeHint(row_widget.sizeHint())
            self.local_zims_list.addItem(item)
            self.local_zims_list.setItemWidget(item, row_widget)

    def _create_local_zim_widget(self, fname, fpath, size, meta):
        """Create widget for displaying a local ZIM file."""
        row_widget = QWidget()
        row_layout = QVBoxLayout(row_widget)
        row_layout.setContentsMargins(6, 6, 6, 6)
        row_layout.setSpacing(2)

        top_row = QHBoxLayout()
        title = meta.get("title") or fname
        title_label = QLabel(f"<b>{title}</b>")
        title_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        top_row.addWidget(title_label, 2)

        size_label = QLabel(
            f"<span style='color:gray'>({self._format_size(size)})</span>"
        )
        size_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        top_row.addWidget(size_label, 0)

        if meta.get("updated"):
            date_label = QLabel(
                f"<span style='color:gray'>{meta['updated']}</span>"
            )
            date_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            top_row.addWidget(date_label, 0)

        top_row.addStretch(1)

        del_btn = QPushButton("Delete")
        del_btn.setFixedWidth(90)
        del_btn.clicked.connect(
            lambda _, f=fpath, n=fname: self.confirm_delete_zim(f, n)
        )
        top_row.addWidget(del_btn, 0)
        row_layout.addLayout(top_row)

        if meta.get("summary"):
            desc_label = QLabel(meta["summary"])
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #555; font-size: 10pt;")
            desc_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            row_layout.addWidget(desc_label)

        row_widget.setLayout(row_layout)
        return row_widget

    def refresh_search_results_list(self):
        """Refresh the list of available ZIM files from Kiwix."""
        self.search_results_list.clear()
        lang = (
            self.kiwix_lang_combo.currentText()
            if self.kiwix_lang_combo
            else "eng"
        )
        if lang == "all":
            lang = None

        query = (
            self.kiwix_search_bar.text().strip()
            if self.kiwix_search_bar
            else None
        )
        if not query:
            return

        try:
            zim_files = KiwixAPI.list_zim_files(language=lang, query=query)
            self.logger.debug("Kiwix API search results:")
            pprint.pprint(zim_files)
        except Exception as e:
            QMessageBox.critical(
                self, "Kiwix", f"Failed to fetch ZIM list: {e}"
            )
            return

        if not isinstance(zim_files, list):
            QMessageBox.critical(
                self, "Kiwix", "Invalid response from Kiwix API."
            )
            return

        # Get list of locally downloaded ZIM files
        local_zims = set()
        zim_dir = os.path.join(
            os.path.expanduser(self.path_settings.base_path), "zim"
        )
        if os.path.exists(zim_dir):
            for f in os.listdir(zim_dir):
                if f.lower().endswith(".zim"):
                    local_zims.add(f)

        for zim in zim_files:
            name = zim.get("id") or zim.get("name") or zim.get("title")
            row_widget = self._create_remote_zim_widget(zim, name, local_zims)
            item = QListWidgetItem()
            item.setSizeHint(row_widget.sizeHint())
            self.search_results_list.addItem(item)
            self.search_results_list.setItemWidget(item, row_widget)

    def _create_remote_zim_widget(self, zim, name, local_zims):
        """Create widget for displaying a remote ZIM file."""
        title = zim.get("title") or zim.get("name") or name
        size = self._extract_size_from_zim(zim)
        desc = zim.get("description") or zim.get("summary") or ""
        url = self._extract_url_from_zim(zim)
        is_downloaded = name in local_zims
        updated = self._extract_updated_from_zim(zim)

        row_widget = QWidget()
        row_layout = QVBoxLayout(row_widget)
        row_layout.setContentsMargins(6, 6, 6, 6)
        row_layout.setSpacing(2)

        # Add illustration if available
        self._add_illustration_to_layout(zim, row_layout)

        # Title and size row
        top_row = QHBoxLayout()
        title_label = QLabel(f"<b>{title}</b>")
        title_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        top_row.addWidget(title_label, 2)

        size_label = QLabel(
            f"<span style='color:gray'>({self._format_size(size)})</span>"
        )
        size_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        top_row.addWidget(size_label, 0)

        if updated:
            date_label = QLabel(f"<span style='color:gray'>{updated}</span>")
            date_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            top_row.addWidget(date_label, 0)

        top_row.addStretch(1)

        # Add action button
        if is_downloaded:
            downloaded_label = QLabel(
                "<span style='color:green'>[Downloaded]</span>"
            )
            top_row.addWidget(downloaded_label, 0)
        elif url and url.endswith(".zim") and url.startswith("http"):
            btn = QPushButton("Download")
            btn.setFixedWidth(90)
            btn.clicked.connect(
                lambda _, z=zim: self.download_kiwix_zim({**zim, "url": url})
            )
            top_row.addWidget(btn, 0)
        else:
            search_btn = QPushButton("Search on Kiwix.org")
            search_btn.setFixedWidth(150)
            search_btn.clicked.connect(
                lambda _, t=title: self.open_kiwix_search(t)
            )
            top_row.addWidget(search_btn, 0)

        row_layout.addLayout(top_row)

        # Description row
        if desc:
            desc_label = QLabel(desc)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #555; font-size: 10pt;")
            desc_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            row_layout.addWidget(desc_label)

        row_widget.setLayout(row_layout)
        return row_widget

    def _extract_size_from_zim(self, zim):
        """Extract size from ZIM metadata."""
        size = zim.get("size")
        if size is None:
            summary = zim.get("summary", "")
            m = re.search(r"(\d+(?:\.\d+)?)\s*(MB|GB|GiB|MiB)", summary)
            if m:
                val, unit = m.groups()
                try:
                    val = float(val)
                    if unit in ("GB", "GiB"):
                        size = int(val * 1024 * 1024 * 1024)
                    else:
                        size = int(val * 1024 * 1024)
                except Exception:
                    size = 0
            else:
                size = 0
        return size

    def _extract_url_from_zim(self, zim):
        """Extract download URL from ZIM metadata."""
        url = zim.get("url")
        if not url and "links" in zim:
            for link in zim["links"]:
                href = link.get("href")
                if (
                    link.get("rel") == "enclosure"
                    and href
                    and href.endswith(".zim")
                ):
                    url = href
                    break
        # If url is relative, prepend Kiwix base
        if url and url.startswith("/"):
            url = urllib.parse.urljoin("https://library.kiwix.org", url)
        return url

    def _extract_updated_from_zim(self, zim):
        """Extract updated date from ZIM metadata."""
        updated = zim.get("updated") or zim.get("date")
        if updated:
            try:
                updated = str(
                    datetime.datetime.fromisoformat(
                        updated.replace("Z", "+00:00")
                    ).date()
                )
            except Exception:
                updated = str(updated)
        return updated

    def _add_illustration_to_layout(self, zim, layout):
        """Add illustration image to layout if available."""
        img_url = zim.get("url")
        if img_url and "/illustration/" in img_url:
            # Fix double https:// if present
            if img_url.startswith("//"):
                img_url = "https:" + img_url
            elif img_url.startswith("/catalog/"):
                img_url = "https://library.kiwix.org" + img_url
            try:
                cache_dir = tempfile.gettempdir()
                img_cache_path = os.path.join(
                    cache_dir, os.path.basename(img_url)
                )
                if not os.path.exists(img_cache_path):
                    r = requests.get(img_url, timeout=10)
                    if r.status_code == 200:
                        with open(img_cache_path, "wb") as f:
                            f.write(r.content)
                pixmap = QPixmap(img_cache_path)
                if not pixmap.isNull():
                    img_label = QLabel()
                    img_label.setPixmap(pixmap.scaledToHeight(48))
                    layout.addWidget(img_label, alignment=Qt.AlignLeft)
            except Exception:
                pass

    def _format_size(self, size):
        """Format file size for display."""
        if not size or size <= 0:
            return "? MB"
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return (
                    f"{size:.1f} {unit}"
                    if unit != "B"
                    else f"{int(size)} {unit}"
                )
            size /= 1024
        return f"{size:.1f} PB"

    def open_kiwix_search(self, title):
        """Open Kiwix website search for the given title."""
        url = f"https://library.kiwix.org/?q={urllib.parse.quote(title)}"
        webbrowser.open(url)

    def download_kiwix_zim(self, zim):
        """Download a ZIM file from Kiwix."""
        name = zim.get("id") or zim.get("name") or zim.get("title")
        url = zim.get("url")
        if not url:
            QMessageBox.warning(self, "Kiwix", f"No download URL for {name}")
            return

        zim_dir = os.path.join(
            os.path.expanduser(self.path_settings.base_path), "zim"
        )
        if not os.path.exists(zim_dir):
            os.makedirs(zim_dir, exist_ok=True)

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save ZIM File",
            os.path.join(zim_dir, f"{name}.zim"),
            "ZIM Files (*.zim)",
        )
        if not save_path:
            return

        meta_path = save_path + ".json"
        progress_dialog = QProgressDialog(
            f"Downloading {name}...", "Cancel", 0, 100, self
        )
        progress_dialog.setWindowTitle("Downloading ZIM File")
        progress_dialog.setWindowModality(Qt.ApplicationModal)
        progress_dialog.setMinimumDuration(0)
        progress_dialog.setValue(0)
        progress_dialog.setAutoClose(False)
        progress_dialog.setAutoReset(False)

        class DownloadWorker(QObject):
            finished = Signal(bool, object)
            progress = Signal(object)

            def __init__(self, url, save_path):
                super().__init__()
                self.url = url
                self.save_path = save_path
                self._abort = False

            def run(self):
                try:
                    with requests.get(self.url, stream=True, timeout=60) as r:
                        r.raise_for_status()
                        total = int(r.headers.get("content-length", 0))
                        downloaded = 0
                        with open(self.save_path, "wb") as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                if self._abort:
                                    self.finished.emit(
                                        False, "Download cancelled"
                                    )
                                    return
                                if chunk:
                                    f.write(chunk)
                                    downloaded += len(chunk)
                                    percent = (
                                        int(downloaded * 100 / total)
                                        if total
                                        else 0
                                    )
                                    self.progress.emit(percent)
                    self.finished.emit(True, None)
                except Exception as e:
                    self.finished.emit(False, str(e))

            def abort(self):
                self._abort = True

        worker = create_worker(DownloadWorker, url=url, save_path=save_path)

        def on_progress(val):
            progress_dialog.setValue(val)

        def on_finished(success, error=None):
            progress_dialog.reset()
            progress_dialog.deleteLater()
            if success:
                try:
                    with open(meta_path, "w", encoding="utf-8") as mf:
                        json.dump(zim, mf, ensure_ascii=False, indent=2)
                except Exception:
                    pass
                self.zimDownloadFinished.emit()
            else:
                QMessageBox.critical(
                    self, "Kiwix", f"Download failed: {error}"
                )

        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        progress_dialog.canceled.connect(worker.abort)
        progress_dialog.show()

    def confirm_delete_zim(self, fpath, fname):
        """Confirm and delete a ZIM file."""
        reply = QMessageBox.question(
            self,
            "Delete ZIM File",
            f"Are you sure you want to delete '{fname}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                os.remove(fpath)
                meta_path = fpath + ".json"
                if os.path.exists(meta_path):
                    os.remove(meta_path)
                QTimer.singleShot(0, self.refresh_kiwix_lists)
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to delete file: {e}"
                )
