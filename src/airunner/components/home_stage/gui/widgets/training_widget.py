import json
import os
from typing import List, Dict, Optional

from PySide6.QtCore import Slot, Qt, QEvent
from PySide6.QtWidgets import (
    QListWidgetItem,
    QPushButton,
    QMessageBox,
    QDialog,
    QListWidget,
    QVBoxLayout,
    QHBoxLayout,
)

from airunner.utils.settings.get_qsettings import get_qsettings
from airunner.components.home_stage.gui.widgets.templates.training_widget_ui import (
    Ui_training_widget,
)
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.enums import SignalCode
from airunner.components.llm.utils.document_extraction import (
    prepare_examples_for_preview,
)
from airunner.components.llm.data.fine_tuned_model import FineTunedModel
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

        self._files: List[str] = []
        self._preview_examples_selected = None
        self._start_connected = False

        self._setup_ui()
        self._connect_signals()
        self._restore_persistent_state()

    def _setup_ui(self):
        """Initialize UI components and their state."""
        self._setup_file_list()
        self._setup_format_combo()
        self._setup_preview_controls()
        self.ui.status_message.hide()
        self.ui.progress_bar.setValue(0)

    def _setup_file_list(self):
        """Configure the file list widget for drag and drop."""
        self.ui.files_list.setAcceptDrops(True)
        self.ui.files_list.setDragEnabled(True)
        self.ui.files_list.installEventFilter(self)

    def _setup_format_combo(self):
        """Populate the format combo box with available options."""
        if not hasattr(self.ui, "format_combo"):
            return

        try:
            self.ui.format_combo.clear()
            self.ui.format_combo.addItem("QA Pairs (default)", "qa")
            self.ui.format_combo.addItem("Long Context", "long")
            self.ui.format_combo.addItem("Author-Style", "author")
        except Exception:
            pass

    def _setup_preview_controls(self):
        """Setup preview and manage model controls."""
        if hasattr(self.ui, "preview_area"):
            try:
                self.ui.preview_area.setReadOnly(True)
            except Exception:
                pass

    def _connect_signals(self):
        """Connect all UI signals to their handlers."""
        self._connect_button_signals()
        self._connect_input_signals()
        self._connect_list_model_signals()

    def _connect_button_signals(self):
        """Connect button click signals."""
        self.ui.add_button.clicked.connect(self.on_add_clicked)
        self.ui.remove_button.clicked.connect(self.on_remove_clicked)
        self.ui.cancel_button.clicked.connect(self.on_cancel_clicked)

        if hasattr(self.ui, "preview_button"):
            try:
                self.ui.preview_button.clicked.connect(self.on_preview_clicked)
            except Exception:
                pass

        if hasattr(self.ui, "manage_models_button"):
            try:
                self.ui.manage_models_button.clicked.connect(
                    self.on_manage_models_clicked
                )
            except Exception:
                pass

        if hasattr(self.ui, "start_button") and not self._start_connected:
            try:
                self.ui.start_button.clicked.connect(self.on_start_clicked)
                self._start_connected = True
            except Exception:
                pass

    def _connect_input_signals(self):
        """Connect input widget signals for state persistence."""
        if hasattr(self.ui, "model_name_input"):
            try:
                self.ui.model_name_input.editingFinished.connect(
                    self._save_persistent_state
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

    def _connect_list_model_signals(self):
        """Connect list model signals to detect external changes."""
        try:
            model = self.ui.files_list.model()
            if model is not None:
                model.rowsInserted.connect(
                    lambda *a: self._on_files_list_changed()
                )
                model.rowsRemoved.connect(
                    lambda *a: self._on_files_list_changed()
                )
        except Exception:
            pass

    def _on_files_list_changed(self):
        """Called when the QListWidget's model changes (rows inserted/removed)."""
        try:
            self._sync_files_from_ui()
            self._save_persistent_state()
        except Exception:
            pass

    def _sync_files_from_ui(self):
        """Ensure self._files matches what's in the ui.files_list widget."""
        try:
            files = []
            for i in range(self.ui.files_list.count()):
                file_path = self._get_item_file_path(i)
                if file_path:
                    files.append(file_path)
            self._files = files
        except Exception:
            pass

    def _get_item_file_path(self, index: int) -> Optional[str]:
        """Get the file path stored in a list item."""
        try:
            item = self.ui.files_list.item(index)
            data = item.data(Qt.UserRole)
            if data:
                return data
            return item.text()
        except Exception:
            return None

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
        """Handle start button click to initiate fine-tuning."""
        self._sync_files_from_ui()

        if not self._validate_training_inputs():
            return

        self._set_training_state(active=True)
        payload = self._create_training_payload()
        self._save_persistent_state()
        self.emit_signal(SignalCode.LLM_START_FINE_TUNE, payload)

    def _validate_training_inputs(self) -> bool:
        """Validate that required inputs are present before starting training."""
        if not self._files:
            self._show_validation_error("No files selected for training")
            return False

        model_name = self.ui.model_name_input.text().strip()
        if not model_name:
            self._show_validation_error("Please enter a model name")
            return False

        return True

    def _show_validation_error(self, message: str):
        """Show validation error to user."""
        try:
            QMessageBox.warning(self, "Start Fine-tune", message)
        except Exception:
            self.set_status_message_text(message)

    def _set_training_state(self, active: bool):
        """Set UI state for training active/inactive."""
        self.ui.start_button.setEnabled(not active)
        self.ui.cancel_button.setEnabled(active)

        if active:
            self.ui.progress_bar.setRange(0, 0)
            self.set_status_message_text("Starting fine-tune...")
        else:
            self.ui.progress_bar.setRange(0, 100)

    def _create_training_payload(self) -> Dict:
        """Create the payload for the training signal."""
        fmt = self._get_selected_format()
        model_name = self.ui.model_name_input.text().strip()

        payload = {
            "files": self._files,
            "model_name": model_name,
            "format": fmt,
        }

        if self._preview_examples_selected:
            payload["examples"] = self._preview_examples_selected

        return payload

    def _get_selected_format(self) -> str:
        """Get the currently selected format from the combo box."""
        try:
            if hasattr(self.ui, "format_combo"):
                return self.ui.format_combo.currentData() or "qa"
        except Exception:
            pass
        return "qa"

    @Slot()
    def on_cancel_clicked(self):
        self.emit_signal(SignalCode.LLM_FINE_TUNE_CANCEL)

    @Slot(dict)
    def on_progress(self, data: Dict):
        """Handle training progress updates."""
        progress = data.get("progress")
        message = data.get("message")
        self.ui.progress_bar.setRange(0, 100)
        self.ui.progress_bar.setValue(int(progress))
        self.set_status_message_text(message)

    @Slot(dict)
    def on_complete(self, data: Dict):
        """Handle training completion."""
        self._set_training_state(active=False)
        self.ui.progress_bar.setValue(100)

        name = data.get("model_name", "")
        message = (
            f"Fine-tune complete: {name}" if name else "Fine-tune complete"
        )
        self.set_status_message_text(message)

    @Slot(dict)
    def on_cancelled(self, data: Dict):
        """Handle training cancellation."""
        self._set_training_state(active=False)
        self.ui.progress_bar.setValue(0)
        self.set_status_message_text("Fine-tune cancelled")

    def add_file(self, file_path: str):
        """Add a file to the training files list."""
        if file_path in self._files:
            return

        self._files.append(file_path)
        self._add_file_to_list_widget(file_path)
        self._save_persistent_state()

    def _add_file_to_list_widget(self, file_path: str):
        """Add a file path to the list widget."""
        item = QListWidgetItem(self._get_display_name(file_path))
        item.setData(Qt.UserRole, file_path)
        self.ui.files_list.addItem(item)

    @Slot()
    def on_preview_clicked(self):
        """Show preview dialog for prepared training examples."""
        self._sync_files_from_ui()

        if not self._files:
            self.set_status_message_text("No files to preview")
            return

        fmt = self._get_selected_format()
        all_examples = self._prepare_examples(fmt)

        if not all_examples:
            self._show_no_examples_message()
            return

        if self._show_preview_dialog(all_examples):
            self._update_preview_area()

    def _prepare_examples(self, fmt: str) -> List:
        """Prepare examples from selected files."""
        all_examples = []
        for path in self._files[:3]:
            try:
                examples = prepare_examples_for_preview(path, fmt)
                all_examples.extend(examples)
            except Exception:
                continue
        return all_examples

    def _show_no_examples_message(self):
        """Show message when no examples could be prepared."""
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

    def _show_preview_dialog(self, all_examples: List) -> bool:
        """Show dialog for previewing and selecting examples."""
        dlg = self._create_preview_dialog(all_examples)
        return dlg.exec() == QDialog.Accepted

    def _create_preview_dialog(self, all_examples: List) -> QDialog:
        """Create the preview dialog with all controls."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Preview & Edit Prepared Examples")
        layout = QVBoxLayout(dlg)

        listw = self._create_example_list(all_examples, dlg)
        layout.addWidget(listw)

        btn_layout = self._create_dialog_buttons(dlg, listw, all_examples)
        layout.addLayout(btn_layout)

        return dlg

    def _create_example_list(
        self, examples: List, parent: QDialog
    ) -> QListWidget:
        """Create the list widget showing examples."""
        listw = QListWidget(parent)
        listw.setSelectionMode(QListWidget.SelectionMode.MultiSelection)

        for idx, ex in enumerate(examples[:100]):
            title, text = ex
            display = f"{title}: {text[:200].replace('\n', ' ')}"
            listw.addItem(display)

        for i in range(listw.count()):
            listw.item(i).setSelected(True)

        return listw

    def _create_dialog_buttons(
        self, dlg: QDialog, listw: QListWidget, all_examples: List
    ) -> QHBoxLayout:
        """Create dialog buttons for example selection."""
        btn_layout = QHBoxLayout()

        select_all = QPushButton("Select All", dlg)
        deselect_all = QPushButton("Deselect All", dlg)
        accept_btn = QPushButton("Use Selected", dlg)
        cancel_btn = QPushButton("Cancel", dlg)

        select_all.clicked.connect(lambda: self._select_all_items(listw))
        deselect_all.clicked.connect(lambda: self._deselect_all_items(listw))
        accept_btn.clicked.connect(
            lambda: self._accept_selection(dlg, listw, all_examples)
        )
        cancel_btn.clicked.connect(dlg.reject)

        btn_layout.addWidget(select_all)
        btn_layout.addWidget(deselect_all)
        btn_layout.addWidget(accept_btn)
        btn_layout.addWidget(cancel_btn)

        return btn_layout

    def _select_all_items(self, listw: QListWidget):
        """Select all items in the list widget."""
        for i in range(listw.count()):
            listw.item(i).setSelected(True)

    def _deselect_all_items(self, listw: QListWidget):
        """Deselect all items in the list widget."""
        for i in range(listw.count()):
            listw.item(i).setSelected(False)

    def _accept_selection(
        self, dlg: QDialog, listw: QListWidget, all_examples: List
    ):
        """Accept the selected examples and close dialog."""
        selected = [i.row() for i in listw.selectedIndexes()]
        self._preview_examples_selected = [all_examples[i] for i in selected]
        dlg.accept()

    def _update_preview_area(self):
        """Update the preview area with selected examples."""
        if not hasattr(self.ui, "preview_area"):
            return

        snippets = [
            f"{t}\n{text[:1000]}{'...' if len(text) > 1000 else ''}"
            for t, text in self._preview_examples_selected
        ]
        self.ui.preview_area.setPlainText("\n\n---\n\n".join(snippets))

    @Slot()
    def on_manage_models_clicked(self):
        """Show dialog for managing fine-tuned models."""
        dlg = self._create_manage_models_dialog()
        dlg.exec()

    def _create_manage_models_dialog(self) -> QDialog:
        """Create the manage models dialog."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Manage Fine-tuned Models")
        layout = QVBoxLayout(dlg)

        listw = self._create_models_list(dlg)
        layout.addWidget(listw)

        btn_layout = self._create_manage_buttons(dlg, listw)
        layout.addLayout(btn_layout)

        return dlg

    def _create_models_list(self, parent: QDialog) -> QListWidget:
        """Create list widget showing available models."""
        listw = QListWidget(parent)

        try:
            models = FineTunedModel.objects.all()
            for m in models:
                item_text = (
                    f"{m.id}: {m.name} (files: {len(m.files_used or [])})"
                )
                listw.addItem(item_text)
        except Exception:
            listw.addItem("(error loading models)")

        return listw

    def _create_manage_buttons(
        self, dlg: QDialog, listw: QListWidget
    ) -> QHBoxLayout:
        """Create buttons for model management dialog."""
        btn_layout = QHBoxLayout()

        load_btn = QPushButton("Load", dlg)
        delete_btn = QPushButton("Delete", dlg)
        close_btn = QPushButton("Close", dlg)

        load_btn.clicked.connect(lambda: self._load_selected_model(listw))
        delete_btn.clicked.connect(lambda: self._delete_selected_model(listw))
        close_btn.clicked.connect(dlg.close)

        btn_layout.addWidget(load_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(close_btn)

        return btn_layout

    def _get_selected_model_id(self, listw: QListWidget) -> Optional[int]:
        """Get the ID of the currently selected model."""
        item = listw.currentItem()
        if not item:
            return None

        try:
            text = item.text()
            return int(text.split(":")[0])
        except Exception:
            return None

    def _load_selected_model(self, listw: QListWidget):
        """Load the selected fine-tuned model."""
        model_id = self._get_selected_model_id(listw)
        if not model_id:
            return

        try:
            m = FineTunedModel.objects.get_orm(model_id)
            self.emit_signal(
                SignalCode.LLM_LOAD_SIGNAL,
                {"model_name": m.name, "fine_tuned_id": model_id},
            )
        except Exception:
            pass

    def _delete_selected_model(self, listw: QListWidget):
        """Delete the selected fine-tuned model."""
        model_id = self._get_selected_model_id(listw)
        if not model_id:
            return

        try:
            FineTunedModel.objects.delete(model_id)
            listw.takeItem(listw.currentRow())
        except Exception:
            pass

    def eventFilter(self, obj, event):
        """Accept drops of file paths into the files_list."""
        try:
            if obj == self.ui.files_list and event.type() == QEvent.Drop:
                self._handle_drop_event(event)
                return True
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def _handle_drop_event(self, event):
        """Handle drop event for files list."""
        mime = event.mimeData()

        if mime.hasUrls():
            self._add_dropped_urls(mime.urls())
        elif mime.hasText():
            self._add_dropped_text(mime.text())

    def _add_dropped_urls(self, urls):
        """Add files from dropped URLs."""
        for url in urls:
            path = url.toLocalFile()
            if path:
                self.add_file(path)

    def _add_dropped_text(self, text: str):
        """Add files from dropped text paths."""
        for line in text.strip().splitlines():
            path = line.strip()
            if path:
                self.add_file(path)

    def _get_display_name(self, file_path: str) -> str:
        """Get display name for a file path."""
        return os.path.basename(file_path)

    def _save_persistent_state(self):
        """Persist the current files list, model name and chosen format to QSettings."""
        try:
            qs = get_qsettings()
            qs.setValue("training_widget/files", json.dumps(self._files or []))
            qs.setValue("training_widget/model_name", self._get_model_name())
            qs.setValue("training_widget/format", self._get_selected_format())
            qs.sync()
        except Exception:
            pass

    def _get_model_name(self) -> str:
        """Get the current model name from input."""
        if not hasattr(self.ui, "model_name_input"):
            return ""

        try:
            return self.ui.model_name_input.text().strip()
        except Exception:
            return ""

    def _restore_persistent_state(self):
        """Load persisted files, model name and format from QSettings and restore UI state."""
        try:
            qs = get_qsettings()
            self._restore_files(qs)
            self._restore_model_name(qs)
            self._restore_format_selection(qs)
        except Exception:
            pass

    def _restore_files(self, qs):
        """Restore file list from QSettings."""
        files = self._load_files_from_settings(qs)
        self._files = []
        self.ui.files_list.clear()

        for path in files:
            resolved = self._resolve_file_path(path)
            self._files.append(resolved)
            self._add_file_to_list_widget(resolved)

    def _load_files_from_settings(self, qs) -> List[str]:
        """Load files list from QSettings."""
        files_raw = qs.value("training_widget/files", "")
        if not files_raw:
            return []

        try:
            if isinstance(files_raw, (list, tuple)):
                return list(files_raw)
            return json.loads(str(files_raw))
        except Exception:
            return []

    def _resolve_file_path(self, path: str) -> str:
        """Resolve a file path, checking DB if file doesn't exist."""
        if os.path.exists(path):
            return path

        return self._resolve_from_database(path)

    def _resolve_from_database(self, path: str) -> str:
        """Try to resolve file path from database records."""
        try:
            db_docs = DBDocument.objects.filter_by(path=path)
            if db_docs and len(db_docs) > 0:
                return db_docs[0].path

            return self._resolve_by_basename(path)
        except Exception:
            return path

    def _resolve_by_basename(self, path: str) -> str:
        """Try to resolve file path by matching basename."""
        try:
            all_docs = DBDocument.objects.all()
            for d in all_docs:
                if os.path.basename(d.path) == os.path.basename(path):
                    return d.path
        except Exception:
            pass
        return path

    def _restore_model_name(self, qs):
        """Restore model name from QSettings."""
        if not hasattr(self.ui, "model_name_input"):
            return

        try:
            model_name = qs.value("training_widget/model_name", "") or ""
            if model_name:
                self.ui.model_name_input.setText(str(model_name))
        except Exception:
            pass

    def _restore_format_selection(self, qs):
        """Restore format selection from QSettings."""
        if not hasattr(self.ui, "format_combo"):
            return

        try:
            fmt = qs.value("training_widget/format", "") or ""
            if not fmt:
                return

            for idx in range(self.ui.format_combo.count()):
                if self.ui.format_combo.itemData(idx) == fmt:
                    self.ui.format_combo.setCurrentIndex(idx)
                    break
        except Exception:
            pass
