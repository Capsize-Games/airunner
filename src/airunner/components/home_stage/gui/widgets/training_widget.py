from typing import List, Dict
import json

from airunner.utils.settings.get_qsettings import get_qsettings
from PySide6.QtCore import Slot, Qt
from PySide6.QtWidgets import (
    QListWidgetItem,
    QComboBox,
    QLabel,
    QPushButton,
    QMessageBox,
)

from airunner.components.home_stage.gui.widgets.templates.training_widget_ui import (
    Ui_training_widget,
)
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.enums import SignalCode
from airunner.components.llm.utils.document_extraction import (
    prepare_examples_for_preview,
)
from PySide6.QtWidgets import QTextEdit
from PySide6.QtWidgets import QDialog, QListWidget, QVBoxLayout, QHBoxLayout
from airunner.components.llm.data.fine_tuned_model import FineTunedModel
from airunner.enums import SignalCode as _SignalCode
from airunner.components.documents.data.models.document import (
    Document as DBDocument,
)


class TrainingWidget(BaseWidget):
    """Widget to manage fine-tuning inputs and start/cancel operations."""

    widget_class_ = Ui_training_widget

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.LLM_FINE_TUNE_PROGRESS: self.on_progress,
            SignalCode.LLM_FINE_TUNE_COMPLETE: self.on_complete,
            SignalCode.LLM_FINE_TUNE_CANCEL: self.on_cancelled,
        }
        super().__init__(*args, **kwargs)
        # connect basic buttons
        self.ui.add_button.clicked.connect(self.on_add_clicked)
        self.ui.remove_button.clicked.connect(self.on_remove_clicked)
        # start_button connection is established once to avoid duplicate calls
        self.ui.cancel_button.clicked.connect(self.on_cancel_clicked)
        # Allow drops from other parts of the app (documents)
        self.ui.files_list.setAcceptDrops(True)
        self.ui.files_list.setDragEnabled(True)
        # Install an event filter to accept drops of file paths
        self.ui.files_list.installEventFilter(self)
        self.ui.status_message.hide()

        # Track files (absolute paths expected)
        self._files: List[str] = []
        # Last prepared preview selection (list of (title, text))
        self._preview_examples_selected = None
        # guard to prevent multiple start button connections
        self._start_connected = False

        # Initialize UI state
        self.ui.progress_bar.setValue(0)

        # Populate UI controls that live in the generated .ui file
        try:
            if hasattr(self.ui, "format_combo"):
                try:
                    self.ui.format_combo.clear()
                    self.ui.format_combo.addItem("QA Pairs (default)", "qa")
                    self.ui.format_combo.addItem("Long Context", "long")
                    self.ui.format_combo.addItem("Author-Style", "author")
                except Exception:
                    pass
            # ensure preview/manage controls are hooked up
            try:
                if hasattr(self.ui, "preview_button"):
                    self.ui.preview_button.clicked.connect(
                        self.on_preview_clicked
                    )
            except Exception:
                pass
            try:
                if hasattr(self.ui, "preview_area"):
                    self.ui.preview_area.setReadOnly(True)
            except Exception:
                pass
            try:
                if hasattr(self.ui, "manage_models_button"):
                    self.ui.manage_models_button.clicked.connect(
                        self.on_manage_models_clicked
                    )
            except Exception:
                pass
        except Exception:
            pass

        # Restore persisted widget state (files, model name, format)
        try:
            self._restore_persistent_state()
        except Exception:
            pass

        # Ensure controls are connected to save state changes
        try:
            if hasattr(self.ui, "model_name_input"):
                try:
                    self.ui.model_name_input.editingFinished.connect(
                        lambda: self._save_persistent_state()
                    )
                except Exception:
                    pass
            if hasattr(self.ui, "format_combo"):
                try:
                    self.ui.format_combo.currentIndexChanged.connect(
                        lambda _: self._save_persistent_state()
                    )
                except Exception:
                    pass
            # Ensure start button is connected (only once)
            if hasattr(self.ui, "start_button") and not getattr(
                self, "_start_connected", False
            ):
                try:
                    self.ui.start_button.clicked.connect(self.on_start_clicked)
                    self._start_connected = True
                except Exception:
                    pass
            # Monitor changes to the underlying list model so external drops (from OS) are detected
            try:
                model = self.ui.files_list.model()
                if model is not None:
                    try:
                        model.rowsInserted.connect(
                            lambda *a: self._on_files_list_changed()
                        )
                        model.rowsRemoved.connect(
                            lambda *a: self._on_files_list_changed()
                        )
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            pass

    def _on_files_list_changed(self) -> None:
        """Called when the QListWidget's model changes (rows inserted/removed) — sync and persist."""
        try:
            self._sync_files_from_ui()
            self._save_persistent_state()
        except Exception:
            pass

    def _sync_files_from_ui(self) -> None:
        """Ensure self._files matches what's in the ui.files_list widget."""
        try:
            files = []
            for i in range(self.ui.files_list.count()):
                it = self.ui.files_list.item(i)
                try:
                    data = it.data(Qt.UserRole)
                except Exception:
                    data = None
                # if no stored data, try using the visible text as a path fallback
                if not data:
                    try:
                        data = it.text()
                    except Exception:
                        data = None
                if data:
                    files.append(data)
            self._files = files
        except Exception:
            pass

    @Slot()
    def on_add_clicked(self):
        # Placeholder for manual add - keep minimal for now
        pass

    @Slot()
    def on_remove_clicked(self):
        current = self.ui.files_list.currentItem()
        if not current:
            return
        path = current.data(Qt.UserRole)
        try:
            self._files.remove(path)
        except ValueError:
            pass
        self.ui.files_list.takeItem(self.ui.files_list.currentRow())
        try:
            self._save_persistent_state()
        except Exception:
            pass

    @Slot()
    def on_start_clicked(self):
        # ensure _files reflects current UI contents (in case of external drops)
        try:
            self._sync_files_from_ui()
        except Exception:
            pass

        if not self._files:
            try:
                QMessageBox.warning(
                    self, "Start Fine-tune", "No files selected for training"
                )
            except Exception:
                self.set_status_message_text("No files selected for training")
            return
        model_name = self.ui.model_name_input.text().strip()
        if not model_name:
            try:
                QMessageBox.warning(
                    self, "Start Fine-tune", "Please enter a model name"
                )
            except Exception:
                self.set_status_message_text("Please enter a model name")
            return

        self.ui.start_button.setEnabled(False)
        self.ui.cancel_button.setEnabled(True)
        self.ui.progress_bar.setRange(0, 0)  # indeterminate while starting
        self.set_status_message_text("Starting fine-tune...")

        # Determine chosen formatting
        fmt = "qa"
        try:
            if hasattr(self.ui, "format_combo"):
                fmt = self.ui.format_combo.currentData() or "qa"
        except Exception:
            fmt = "qa"

        # Emit signal to start fine tuning in worker with format selection.
        # If user previewed and selected a custom set of examples, prefer sending them
        payload = {
            "files": self._files,
            "model_name": model_name,
            "format": fmt,
        }
        if self._preview_examples_selected:
            payload["examples"] = self._preview_examples_selected

        # persist chosen settings before emitting
        try:
            self._save_persistent_state()
        except Exception:
            pass

        self.emit_signal(SignalCode.LLM_START_FINE_TUNE, payload)

    @Slot()
    def on_cancel_clicked(self):
        self.emit_signal(SignalCode.LLM_FINE_TUNE_CANCEL)

    @Slot(dict)
    def on_progress(self, data: Dict):
        # data expected to contain progress (0-100) and optional message
        progress = data.get("progress")
        message = data.get("message")
        self.ui.progress_bar.setRange(0, 100)
        self.ui.progress_bar.setValue(int(progress))
        self.set_status_message_text(message)

    @Slot(dict)
    def on_complete(self, data: Dict):
        name = data.get("model_name", "")
        self.ui.start_button.setEnabled(True)
        self.ui.cancel_button.setEnabled(False)
        try:
            self.ui.progress_bar.setRange(0, 100)
            self.ui.progress_bar.setValue(100)
        except Exception:
            pass
        self.set_status_message_text(
            f"Fine-tune complete: {name}" if name else "Fine-tune complete"
        )

    @Slot(dict)
    def on_cancelled(self, data: Dict):
        self.ui.start_button.setEnabled(True)
        self.ui.cancel_button.setEnabled(False)
        try:
            self.ui.progress_bar.setRange(0, 100)
            self.ui.progress_bar.setValue(0)
        except Exception:
            pass
        self.set_status_message_text("Fine-tune cancelled")

    def add_file(self, file_path: str):
        if file_path in self._files:
            return
        self._files.append(file_path)
        item = QListWidgetItem(self._get_display_name(file_path))
        item.setData(Qt.UserRole, file_path)
        self.ui.files_list.addItem(item)
        try:
            self._save_persistent_state()
        except Exception:
            pass

    @Slot()
    def on_preview_clicked(self):
        # Show the first few prepared examples for the currently selected files
        fmt = "qa"
        try:
            if hasattr(self.ui, "format_combo"):
                fmt = self.ui.format_combo.currentData() or "qa"
        except Exception:
            fmt = "qa"

        # ensure we use the current files shown in the UI
        try:
            self._sync_files_from_ui()
        except Exception:
            pass
        files = self._files
        if not files:
            self.set_status_message_text("No files to preview")
            return

        # Ensure we use the current files shown in the UI
        try:
            self._sync_files_from_ui()
        except Exception:
            pass

        # Prepare examples for all selected files (limit to 3 files)
        all_examples = []
        for path in files[:3]:
            try:
                examples = prepare_examples_for_preview(path, fmt)
                all_examples.extend(examples)
            except Exception:
                continue

        if not all_examples:
            try:
                QMessageBox.information(
                    self,
                    "Preview",
                    "No examples could be prepared for preview for the selected files.",
                )
            except Exception:
                self.set_status_message_text(
                    "No examples could be prepared for preview"
                )
            return

        # Build a preview-and-edit dialog
        dlg = QDialog(self)
        dlg.setWindowTitle("Preview & Edit Prepared Examples")
        layout = QVBoxLayout(dlg)
        listw = QListWidget(dlg)
        listw.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        # show up to first 100 examples
        for idx, ex in enumerate(all_examples[:100]):
            title, text = ex
            display = f"{title}: {text[:200].replace('\n', ' ')}"
            listw.addItem(display)
        layout.addWidget(listw)

        btn_layout = QHBoxLayout()
        select_all = QPushButton("Select All", dlg)
        deselect_all = QPushButton("Deselect All", dlg)
        accept_btn = QPushButton("Use Selected", dlg)
        cancel_btn = QPushButton("Cancel", dlg)
        btn_layout.addWidget(select_all)
        btn_layout.addWidget(deselect_all)
        btn_layout.addWidget(accept_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        def _select_all():
            for i in range(listw.count()):
                item = listw.item(i)
                item.setSelected(True)

        def _deselect_all():
            for i in range(listw.count()):
                item = listw.item(i)
                item.setSelected(False)

        def _accept():
            selected = [i.row() for i in listw.selectedIndexes()]
            self._preview_examples_selected = [
                all_examples[i] for i in selected
            ]
            dlg.accept()

        select_all.clicked.connect(_select_all)
        deselect_all.clicked.connect(_deselect_all)
        accept_btn.clicked.connect(_accept)
        cancel_btn.clicked.connect(dlg.reject)

        # Default: select first few
        _select_all()
        res = dlg.exec()
        if res == QDialog.Rejected:
            # user cancelled; keep previous selection unchanged
            return
        # Populate preview_area with chosen examples for quick review
        if hasattr(self.ui, "preview_area"):
            snippets = [
                f"{t}\n{text[:1000]}{'...' if len(text)>1000 else ''}"
                for t, text in self._preview_examples_selected
            ]
            self.ui.preview_area.setPlainText("\n\n---\n\n".join(snippets))

    @Slot()
    def on_manage_models_clicked(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Manage Fine-tuned Models")
        layout = QVBoxLayout(dlg)
        listw = QListWidget(dlg)
        layout.addWidget(listw)

        # Load models from DB
        try:
            models = FineTunedModel.objects.all()
            for m in models:
                item_text = (
                    f"{m.id}: {m.name} (files: {len(m.files_used or [])})"
                )
                listw.addItem(item_text)
        except Exception:
            listw.addItem("(error loading models)")

        btn_layout = QHBoxLayout()
        load_btn = QPushButton("Load", dlg)
        delete_btn = QPushButton("Delete", dlg)
        close_btn = QPushButton("Close", dlg)
        btn_layout.addWidget(load_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        def _selected_model_id():
            it = listw.currentItem()
            if not it:
                return None
            text = it.text()
            try:
                return int(text.split(":")[0])
            except Exception:
                return None

        def _do_load():
            mid = _selected_model_id()
            if not mid:
                return
            try:
                m = FineTunedModel.objects.get_orm(mid)
                # Emit a signal to request model load; the consuming handler can implement loading adapter
                self.emit_signal(
                    _SignalCode.LLM_LOAD_SIGNAL,
                    {"model_name": m.name, "fine_tuned_id": mid},
                )
            except Exception:
                pass

        def _do_delete():
            mid = _selected_model_id()
            if not mid:
                return
            try:
                FineTunedModel.objects.delete(mid)
                # remove from list
                listw.takeItem(listw.currentRow())
            except Exception:
                pass

        load_btn.clicked.connect(_do_load)
        delete_btn.clicked.connect(_do_delete)
        close_btn.clicked.connect(dlg.close)
        dlg.exec()

    def eventFilter(self, obj, event):
        """Accept drops of file paths into the files_list."""
        try:
            from PySide6.QtCore import QEvent, Qt

            if obj == self.ui.files_list and event.type() == QEvent.Drop:
                mime = event.mimeData()
                # If files were dragged from OS/file explorer
                if mime.hasUrls():
                    for url in mime.urls():
                        path = url.toLocalFile()
                        if path:
                            self.add_file(path)
                    return True
                # If internal drag provides plain text paths
                if mime.hasText():
                    text = mime.text().strip()
                    # Support multiple lines
                    for line in text.splitlines():
                        p = line.strip()
                        if p:
                            self.add_file(p)
                    return True
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def _get_display_name(self, file_path: str) -> str:
        # Simplified display name
        import os

        return os.path.basename(file_path)

    def _save_persistent_state(self) -> None:
        """Persist the current files list, model name and chosen format to QSettings."""
        try:
            qs = get_qsettings()
            # files as JSON list
            qs.setValue("training_widget/files", json.dumps(self._files or []))
            # model name
            model_name = ""
            if hasattr(self.ui, "model_name_input"):
                try:
                    model_name = self.ui.model_name_input.text().strip()
                except Exception:
                    model_name = ""
            qs.setValue("training_widget/model_name", model_name)
            # format: store the currentData() (the format key)
            fmt = ""
            if hasattr(self.ui, "format_combo"):
                try:
                    fmt = self.ui.format_combo.currentData() or ""
                except Exception:
                    fmt = ""
            qs.setValue("training_widget/format", fmt)
            try:
                qs.sync()
            except Exception:
                pass
        except Exception:
            # best-effort; do not crash the widget
            pass

    def _restore_persistent_state(self) -> None:
        """Load persisted files, model name and format from QSettings and restore UI state."""
        try:
            qs = get_qsettings()
            files_raw = qs.value("training_widget/files", "")
            files = []
            if files_raw:
                try:
                    if isinstance(files_raw, (list, tuple)):
                        files = list(files_raw)
                    else:
                        files = json.loads(str(files_raw))
                except Exception:
                    files = []
            # populate internal list and UI list widget without triggering multiple saves
            self._files = []
            try:
                self.ui.files_list.clear()
            except Exception:
                pass
            for p in files:
                try:
                    resolved = p
                    try:
                        import os

                        # If the stored path doesn't exist, try to resolve via DB document records
                        if not os.path.exists(resolved):
                            try:
                                # exact path match
                                db_docs = DBDocument.objects.filter_by(
                                    path=resolved
                                )
                                if db_docs and len(db_docs) > 0:
                                    resolved = db_docs[0].path
                                else:
                                    # try matching by basename
                                    all_docs = DBDocument.objects.all()
                                    for d in all_docs:
                                        try:
                                            if os.path.basename(
                                                d.path
                                            ) == os.path.basename(p):
                                                resolved = d.path
                                                break
                                        except Exception:
                                            continue
                            except Exception:
                                pass
                    except Exception:
                        pass

                    self._files.append(resolved)
                    item = QListWidgetItem(self._get_display_name(resolved))
                    item.setData(Qt.UserRole, resolved)
                    try:
                        self.ui.files_list.addItem(item)
                    except Exception:
                        pass
                except Exception:
                    continue

            # restore model name
            try:
                mname = qs.value("training_widget/model_name", "") or ""
                if mname and hasattr(self.ui, "model_name_input"):
                    try:
                        self.ui.model_name_input.setText(str(mname))
                    except Exception:
                        pass
            except Exception:
                pass

            # restore format selection
            try:
                fmt = qs.value("training_widget/format", "") or ""
                if fmt and hasattr(self.ui, "format_combo"):
                    # find index with matching data
                    for idx in range(self.ui.format_combo.count()):
                        try:
                            if self.ui.format_combo.itemData(idx) == fmt:
                                self.ui.format_combo.setCurrentIndex(idx)
                                break
                        except Exception:
                            continue
            except Exception:
                pass
        except Exception:
            pass
