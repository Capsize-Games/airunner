import json
import os
import os
import json
from typing import List, Dict, Optional

from PySide6.QtCore import Slot, Qt, QEvent, QPoint
from PySide6.QtWidgets import (
    QListWidgetItem,
    QPushButton,
    QMessageBox,
    QDialog,
    QListWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidgetItem,
    QMenu,
    QTextEdit,
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
from airunner.components.llm.training_presets import (
    TrainingScenario,
    TrainingPreset,
    get_preset,
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
        self._current_preset: Optional[TrainingPreset] = None
        self._initialized = False
        self._is_restoring = False  # Flag to prevent saves during restoration

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Initialize UI components and their state."""
        self._setup_file_list()
        self._setup_scenario_combo()
        self._setup_preview_controls()
        self.ui.status_message.hide()
        self.ui.progress_bar.setValue(0)

    def _setup_file_list(self):
        """Configure the file list widget for drag and drop."""
        self.ui.files_list.setAcceptDrops(True)
        self.ui.files_list.setDragEnabled(True)
        self.ui.files_list.installEventFilter(self)

    def _setup_scenario_combo(self):
        """Populate the scenario combo box with available scenarios."""
        self.ui.scenario_combo.blockSignals(True)
        self.ui.scenario_combo.clear()
        for scenario in TrainingScenario:
            preset = get_preset(scenario)
            display_name = preset.name
            self.ui.scenario_combo.addItem(display_name, scenario.value)
        self.ui.scenario_combo.blockSignals(False)

    def _setup_preview_controls(self):
        """Setup preview table and manage model controls."""
        self.ui.preview_table.horizontalHeader().setStretchLastSection(True)
        self.ui.preview_table.setColumnWidth(0, 50)
        self.ui.preview_table.setColumnWidth(1, 150)
        self.ui.preview_table.customContextMenuRequested.connect(
            self.on_preview_table_context_menu
        )
        self.ui.preview_table.cellDoubleClicked.connect(
            self.on_preview_table_double_clicked
        )

    def showEvent(self, event):
        """Handle widget show event to initialize sliders after they're ready."""
        super().showEvent(event)
        self.logger.debug(
            f"TrainingWidget showEvent called, _initialized={self._initialized}"
        )
        if not self._initialized:
            self._initialized = True
            self.logger.debug(
                "TrainingWidget initializing for first time, restoring state"
            )
            # Block scenario signal during restoration to prevent premature application
            # Restore state after sliders are initialized
            self._restore_persistent_state()
            # Re-enable scenario signal
            # Apply the current scenario now that everything is initialized
            self.ui.scenario_combo.blockSignals(True)
            if self.ui.scenario_combo.currentIndex() >= 0:
                self.on_scenario_combo_currentIndexChanged(
                    self.ui.scenario_combo.currentIndex()
                )
            self.ui.scenario_combo.blockSignals(False)

    def _connect_signals(self):
        """Connect all UI signals to their handlers."""
        self._connect_input_signals()
        self._connect_list_model_signals()

    def _connect_input_signals(self):
        """Connect input widget signals for state persistence."""
        # Connect advanced settings to save on change
        self.ui.advanced_group.toggled.connect(
            lambda _: self._save_persistent_state()
        )

        # Connect gradient checkpointing checkbox
        self.ui.gradient_checkpointing_checkbox.toggled.connect(
            lambda _: self._save_persistent_state()
        )

    @Slot()
    def on_model_name_input_editingFinished(self):
        """Handle model name input editing finished."""
        self._save_persistent_state()

    @Slot(bool)
    def on_advanced_group_toggled(self, checked: bool):
        """Handle advanced group toggled."""
        self._save_persistent_state()

    @Slot(bool)
    def on_gradient_checkpointing_checkbox_toggled(self, checked: bool):
        """Handle gradient checkpointing checkbox toggled."""
        self._save_persistent_state()

    @Slot(QPoint)
    def on_preview_table_context_menu(self, pos: QPoint):
        """Handle right-click context menu on preview table."""
        selected_rows = self.ui.preview_table.selectionModel().selectedRows()
        if not selected_rows:
            return

        menu = QMenu(self)
        row_count = len(selected_rows)
        delete_text = f"Delete {row_count} row{'s' if row_count > 1 else ''}"
        delete_action = menu.addAction(delete_text)
        action = menu.exec(self.ui.preview_table.mapToGlobal(pos))

        if action == delete_action:
            self._delete_selected_preview_examples()

    @Slot(int, int)
    def on_preview_table_double_clicked(self, row: int, column: int):
        """Handle double-click on table row to view/edit example."""
        if not self._preview_examples_selected or row >= len(
            self._preview_examples_selected
        ):
            return

        title, text = self._preview_examples_selected[row]
        self._show_example_editor(row, title, text)

    def _connect_list_model_signals(self):
        """Connect list model signals to detect external changes."""
        model = self.ui.files_list.model()
        if model is not None:
            model.rowsInserted.connect(
                lambda *a: self._on_files_list_changed()
            )
            model.rowsRemoved.connect(lambda *a: self._on_files_list_changed())

    def _on_files_list_changed(self):
        """Called when the QListWidget's model changes (rows inserted/removed)."""
        try:
            self._sync_files_from_ui()
            self._save_persistent_state()
        except Exception as e:
            self.logger.error(f"Error handling files list change: {str(e)}")

    def _sync_files_from_ui(self):
        """Ensure self._files matches what's in the ui.files_list widget."""
        try:
            files = []
            for i in range(self.ui.files_list.count()):
                file_path = self._get_item_file_path(i)
                if file_path:
                    files.append(file_path)
            self._files = files
        except Exception as e:
            self.logger.error(f"Error syncing files from UI: {str(e)}")

    def _get_item_file_path(self, index: int) -> Optional[str]:
        """Get the file path stored in a list item."""
        try:
            item = self.ui.files_list.item(index)
            data = item.data(Qt.UserRole)
            if data:
                return data
            return item.text()
        except Exception as e:
            self.logger.error(f"Error getting item file path: {str(e)}")
            return None

    @Slot()
    def on_add_button_clicked(self):
        # Placeholder for manual add - keep minimal for now
        pass

    @Slot()
    def on_remove_button_clicked(self):
        current = self.ui.files_list.currentItem()
        if not current:
            return
        path = current.data(Qt.UserRole)
        self._files.remove(path)
        self.ui.files_list.takeItem(self.ui.files_list.currentRow())
        self._save_persistent_state()

    @Slot()
    def on_start_button_clicked(self):
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
            "adapter_name": model_name,
            "model_name": model_name,
            "format": fmt,
        }

        # Add scenario/preset if selected
        scenario_name = self.ui.scenario_combo.currentData()
        if scenario_name:
            payload["preset"] = scenario_name

        # Add advanced settings if group is checked
        if self.ui.advanced_group.isChecked():
            payload["learning_rate"] = self.ui.learning_rate_slider.value()
            payload["num_train_epochs"] = int(self.ui.epochs_slider.value())
            payload["per_device_train_batch_size"] = int(
                self.ui.batch_size_slider.value()
            )
            payload["gradient_accumulation_steps"] = int(
                self.ui.gradient_accumulation_slider.value()
            )
            payload["warmup_steps"] = int(self.ui.warmup_steps_slider.value())
            payload["gradient_checkpointing"] = (
                self.ui.gradient_checkpointing_checkbox.isChecked()
            )

        if self._preview_examples_selected:
            payload["examples"] = self._preview_examples_selected

        return payload

    def _get_selected_format(self) -> str:
        """Get the format type from the currently selected scenario."""
        if self._current_preset:
            return self._current_preset.format_type

        scenario_name = self.ui.scenario_combo.currentData()
        if scenario_name:
            for s in TrainingScenario:
                if s.value == scenario_name:
                    preset = get_preset(s)
                    return preset.format_type
        return "qa"

    @Slot()
    def on_cancel_button_clicked(self):
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

        # Unload LLM to free up memory after training
        self.emit_signal(SignalCode.LLM_UNLOAD_SIGNAL)

    @Slot(dict)
    def on_cancelled(self, data: Dict):
        """Handle training cancellation."""
        self._set_training_state(active=False)
        self.ui.progress_bar.setValue(0)
        self.set_status_message_text("Fine-tune cancelled")

    @Slot(int)
    def on_scenario_combo_currentIndexChanged(self, index: int):
        """Handle scenario selection - auto-populate parameters and update description."""
        if index < 0:
            return

        scenario_name = self.ui.scenario_combo.currentData()
        if not scenario_name:
            return

        for s in TrainingScenario:
            if s.value == scenario_name:
                preset = get_preset(s)
                self._current_preset = preset
                self._apply_scenario_to_ui(preset)
                break
        self._save_persistent_state()

    def _apply_scenario_to_ui(self, preset: TrainingPreset):
        """Apply scenario preset values to all UI controls."""
        self.ui.scenario_description.setText(preset.description)

        # Set values directly via spinbox (bypasses slider normalization issues)
        # The spinbox valueChanged signal will update the slider automatically
        self.ui.learning_rate_slider.ui.slider_spinbox.setValue(
            preset.learning_rate
        )
        self.ui.epochs_slider.ui.slider_spinbox.setValue(
            preset.num_train_epochs
        )
        self.ui.batch_size_slider.ui.slider_spinbox.setValue(
            preset.per_device_train_batch_size
        )
        self.ui.gradient_accumulation_slider.ui.slider_spinbox.setValue(
            preset.gradient_accumulation_steps
        )
        self.ui.warmup_steps_slider.ui.slider_spinbox.setValue(
            preset.warmup_steps
        )
        self.ui.gradient_checkpointing_checkbox.setChecked(
            preset.gradient_checkpointing
        )

    @Slot(QListWidgetItem)
    def on_files_list_itemDoubleClicked(self, item: QListWidgetItem):
        """Handle double-click on a file to show its details."""
        file_path = item.data(Qt.UserRole)
        if not file_path:
            return

        try:
            # Try to find the document in the database
            doc = DBDocument.objects.get_by_path(file_path)
            if doc:
                self.emit_signal(
                    SignalCode.DOCUMENT_OPEN_IN_VIEWER,
                    {"document_id": doc.id},
                )
            else:
                QMessageBox.information(
                    self,
                    "Document Not Found",
                    "The selected file is not found in the document database.",
                )
        except Exception as e:
            self.set_status_message_text(f"Error opening document: {str(e)}")

    @Slot()
    def on_manage_adapters_button_clicked(self):
        """Show dialog to manage trained adapters."""
        try:
            adapters = FineTunedModel.get_all_records()
            if not adapters:
                QMessageBox.information(
                    self, "Manage Adapters", "No trained adapters found."
                )
                return

            dlg = self._create_adapter_management_dialog(adapters)
            dlg.exec()
        except Exception as e:
            self.set_status_message_text(f"Error managing adapters: {str(e)}")

    def _create_adapter_management_dialog(self, adapters: List) -> QDialog:
        """Create dialog showing all adapters with load/delete options."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Manage Trained Adapters")
        dlg.resize(600, 400)
        layout = QVBoxLayout(dlg)

        # Create list widget
        list_widget = QListWidget(dlg)
        for adapter in adapters:
            item_text = f"{adapter.name}"
            if adapter.adapter_path:
                item_text += f" ({adapter.adapter_path})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, adapter.id)
            list_widget.addItem(item)
        layout.addWidget(list_widget)

        # Create buttons
        btn_layout = QHBoxLayout()
        load_btn = QPushButton("Load Adapter", dlg)
        delete_btn = QPushButton("Delete Adapter", dlg)
        close_btn = QPushButton("Close", dlg)

        load_btn.clicked.connect(
            lambda: self._load_adapter_from_dialog(list_widget, adapters, dlg)
        )
        delete_btn.clicked.connect(
            lambda: self._delete_adapter_from_dialog(list_widget, adapters)
        )
        close_btn.clicked.connect(dlg.accept)

        btn_layout.addWidget(load_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        return dlg

    def _load_adapter_from_dialog(
        self, list_widget: QListWidget, adapters: List, dlg: QDialog
    ):
        """Load the selected adapter."""
        current = list_widget.currentItem()
        if not current:
            return

        adapter_id = current.data(Qt.UserRole)
        adapter = next((a for a in adapters if a.id == adapter_id), None)
        if adapter:
            self.ui.model_name_input.setText(adapter.name)
            dlg.accept()
            self.set_status_message_text(f"Loaded adapter: {adapter.name}")

    def _delete_adapter_from_dialog(
        self, list_widget: QListWidget, adapters: List
    ):
        """Delete the selected adapter."""
        current = list_widget.currentItem()
        if not current:
            return

        adapter_id = current.data(Qt.UserRole)
        adapter = next((a for a in adapters if a.id == adapter_id), None)
        if not adapter:
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Adapter",
            f"Are you sure you want to delete adapter '{adapter.name}'?\n\nThis will remove the database entry and all associated files.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            try:
                # Delete from database
                adapter.delete()

                # Delete from filesystem if path exists
                if adapter.adapter_path and os.path.exists(
                    adapter.adapter_path
                ):
                    import shutil

                    shutil.rmtree(adapter.adapter_path, ignore_errors=True)

                # Remove from list
                list_widget.takeItem(list_widget.currentRow())
                self.set_status_message_text(
                    f"Deleted adapter: {adapter.name}"
                )
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Delete Failed",
                    f"Failed to delete adapter: {str(e)}",
                )

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
    def on_preview_button_clicked(self):
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
            self._update_preview_table()

    def _prepare_examples(self, fmt: str) -> List:
        """Prepare examples from selected files."""
        all_examples = []
        for path in self._files[:3]:
            examples = prepare_examples_for_preview(path, fmt)
            all_examples.extend(examples)
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
        self._update_preview_table()
        self._save_persistent_state()
        dlg.accept()

    def _update_preview_table(self):
        """Update the preview table with selected examples."""
        self.ui.preview_table.setRowCount(0)

        if not self._preview_examples_selected:
            return

        self.ui.preview_table.setRowCount(len(self._preview_examples_selected))

        for idx, (title, text) in enumerate(self._preview_examples_selected):
            num_item = QTableWidgetItem(str(idx + 1))
            num_item.setTextAlignment(Qt.AlignCenter)
            num_item.setFlags(num_item.flags() & ~Qt.ItemIsEditable)

            title_item = QTableWidgetItem(title[:50])
            title_item.setFlags(title_item.flags() & ~Qt.ItemIsEditable)

            preview_text = text[:100].replace("\n", " ")
            if len(text) > 100:
                preview_text += "..."
            preview_item = QTableWidgetItem(preview_text)
            preview_item.setFlags(preview_item.flags() & ~Qt.ItemIsEditable)

            self.ui.preview_table.setItem(idx, 0, num_item)
            self.ui.preview_table.setItem(idx, 1, title_item)
            self.ui.preview_table.setItem(idx, 2, preview_item)

    def _delete_preview_example(self, row: int):
        """Delete a preview example at the given row."""
        if not self._preview_examples_selected or row >= len(
            self._preview_examples_selected
        ):
            return

        del self._preview_examples_selected[row]
        self._update_preview_table()
        self._save_persistent_state()

    def _delete_selected_preview_examples(self):
        """Delete all selected preview examples."""
        selected_rows = self.ui.preview_table.selectionModel().selectedRows()
        if not selected_rows or not self._preview_examples_selected:
            return

        rows_to_delete = sorted(
            [index.row() for index in selected_rows], reverse=True
        )

        for row in rows_to_delete:
            if row < len(self._preview_examples_selected):
                del self._preview_examples_selected[row]

        self._update_preview_table()
        self._save_persistent_state()

    def _show_example_editor(self, row: int, title: str, text: str):
        """Show dialog to view/edit an example."""
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Edit Example: {title}")
        dlg.resize(800, 600)

        layout = QVBoxLayout(dlg)

        text_edit = QTextEdit(dlg)
        text_edit.setPlainText(text)
        layout.addWidget(text_edit)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save", dlg)
        cancel_btn = QPushButton("Cancel", dlg)

        save_btn.clicked.connect(
            lambda: self._save_example_edit(
                row, title, text_edit.toPlainText(), dlg
            )
        )
        cancel_btn.clicked.connect(dlg.reject)

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        dlg.exec()

    def _save_example_edit(
        self, row: int, title: str, new_text: str, dlg: QDialog
    ):
        """Save edited example text."""
        if row < len(self._preview_examples_selected):
            self._preview_examples_selected[row] = (title, new_text)
            self._update_preview_table()
            self._save_persistent_state()
        dlg.accept()

    @Slot()
    def on_manage_models_button_clicked(self):
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
        except Exception as e:
            self.logger.error(f"Error loading fine-tuned models: {str(e)}")

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

        text = item.text()
        return int(text.split(":")[0])

    def _load_selected_model(self, listw: QListWidget):
        """Load the selected fine-tuned model."""
        model_id = self._get_selected_model_id(listw)
        if not model_id:
            return

        m = FineTunedModel.objects.get_orm(model_id)
        self.emit_signal(
            SignalCode.LLM_LOAD_SIGNAL,
            {"model_name": m.name, "fine_tuned_id": model_id},
        )

    def _delete_selected_model(self, listw: QListWidget):
        """Delete the selected fine-tuned model."""
        model_id = self._get_selected_model_id(listw)
        if not model_id:
            return

        FineTunedModel.objects.delete(model_id)
        listw.takeItem(listw.currentRow())

    def eventFilter(self, obj, event):
        """Accept drops of file paths into the files_list."""
        if obj == self.ui.files_list and event.type() == QEvent.Drop:
            self._handle_drop_event(event)
            return True
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
        """Persist the current files list, model name, scenario and all settings to QSettings."""
        # Don't save during restoration to avoid overwriting data being restored
        if self._is_restoring:
            return

        qs = get_qsettings()
        qs.setValue("training_widget/files", json.dumps(self._files or []))

        # Save model name
        qs.setValue(
            "training_widget/model_name",
            self.ui.model_name_input.text().strip(),
        )

        # Save scenario selection
        qs.setValue(
            "training_widget/scenario",
            self.ui.scenario_combo.currentData(),
        )

        # Save advanced group state
        qs.setValue(
            "training_widget/advanced_checked",
            self.ui.advanced_group.isChecked(),
        )

        # Save slider values
        qs.setValue(
            "training_widget/learning_rate",
            self.ui.learning_rate_slider.value(),
        )
        qs.setValue("training_widget/epochs", self.ui.epochs_slider.value())
        qs.setValue(
            "training_widget/batch_size",
            self.ui.batch_size_slider.value(),
        )
        qs.setValue(
            "training_widget/gradient_accumulation",
            self.ui.gradient_accumulation_slider.value(),
        )
        qs.setValue(
            "training_widget/warmup_steps",
            self.ui.warmup_steps_slider.value(),
        )
        qs.setValue(
            "training_widget/gradient_checkpointing",
            self.ui.gradient_checkpointing_checkbox.isChecked(),
        )

        # Save selected preview examples
        if self._preview_examples_selected:
            examples_json = json.dumps(self._preview_examples_selected)
            self.logger.debug(
                f"Saving {len(self._preview_examples_selected)} preview examples, JSON length: {len(examples_json)}"
            )
            qs.setValue(
                "training_widget/preview_examples_selected",
                examples_json,
            )
        else:
            self.logger.debug("No preview examples to save, removing key")
            qs.remove("training_widget/preview_examples_selected")

        qs.sync()

    def _restore_persistent_state(self):
        """Load persisted files, model name, scenario and all settings from QSettings and restore UI state."""
        self.logger.debug("_restore_persistent_state called")
        self._is_restoring = True
        try:
            qs = get_qsettings()
            self.logger.debug("Restoring files...")
            self._restore_files(qs)
            self.logger.debug("Restoring model name...")
            self._restore_model_name(qs)
            self.logger.debug("Restoring scenario selection...")
            self._restore_scenario_selection(qs)
            self.logger.debug("Restoring advanced settings...")
            self._restore_advanced_settings(qs)
            self.logger.debug("Restoring preview examples...")
            self._restore_preview_examples(qs)
            self.logger.debug("Restoration complete")
            # Note: preview_content is regenerated from preview_examples, so no need to restore it separately
        except Exception as e:
            self.logger.error(f"Error during restoration: {e}", exc_info=True)
        finally:
            self._is_restoring = False

    def _restore_model_name(self, qs):
        """Restore model name from QSettings."""
        model_name = qs.value("training_widget/model_name", "")
        if model_name:
            self.ui.model_name_input.setText(model_name)

    def _restore_scenario_selection(self, qs):
        """Restore scenario selection from QSettings."""
        scenario_name = qs.value("training_widget/scenario", "")
        if scenario_name:
            for i in range(self.ui.scenario_combo.count()):
                if self.ui.scenario_combo.itemData(i) == scenario_name:
                    self.ui.scenario_combo.blockSignals(True)
                    self.ui.scenario_combo.setCurrentIndex(i)
                    self.ui.scenario_combo.blockSignals(False)
                    break

    def _restore_advanced_settings(self, qs):
        """Restore advanced settings from QSettings."""
        advanced_checked = qs.value(
            "training_widget/advanced_checked", False, type=bool
        )
        self.ui.advanced_group.setChecked(advanced_checked)
        learning_rate = qs.value(
            "training_widget/learning_rate", 0.0002, type=float
        )
        epochs = qs.value("training_widget/epochs", 1, type=int)
        batch_size = qs.value("training_widget/batch_size", 1, type=int)
        grad_accum = qs.value(
            "training_widget/gradient_accumulation", 1, type=int
        )
        warmup = qs.value("training_widget/warmup_steps", 0, type=int)
        grad_checkpoint = qs.value(
            "training_widget/gradient_checkpointing", True, type=bool
        )
        # Set values directly via spinbox to avoid slider initialization issues
        self.ui.learning_rate_slider.ui.slider_spinbox.setValue(learning_rate)
        self.ui.epochs_slider.ui.slider_spinbox.setValue(epochs)
        self.ui.batch_size_slider.ui.slider_spinbox.setValue(batch_size)
        self.ui.gradient_accumulation_slider.ui.slider_spinbox.setValue(
            grad_accum
        )
        self.ui.warmup_steps_slider.ui.slider_spinbox.setValue(warmup)
        self.ui.gradient_checkpointing_checkbox.setChecked(grad_checkpoint)

    def _restore_preview_examples(self, qs):
        """Restore selected preview examples from QSettings."""
        examples_raw = qs.value(
            "training_widget/preview_examples_selected", ""
        )
        self.logger.info(
            f"Restoring preview examples, raw: {examples_raw[:100] if examples_raw else 'EMPTY'}"
        )
        if examples_raw:
            try:
                self._preview_examples_selected = json.loads(examples_raw)
                self.logger.info(
                    f"Restored {len(self._preview_examples_selected)} preview examples"
                )
                if self._preview_examples_selected:
                    self._update_preview_table()
                    self.logger.info(
                        f"Preview table updated with {len(self._preview_examples_selected)} examples"
                    )
            except (json.JSONDecodeError, TypeError) as e:
                self.logger.error(f"Error restoring preview examples: {e}")
                self._preview_examples_selected = None
        else:
            self.logger.info("No preview examples to restore")

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
        except Exception as e:
            self.logger.error(f"Error loading files from settings: {str(e)}")
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
        except Exception as e:
            self.logger.error(
                f"Error resolving file path from database: {str(e)}"
            )
            return path

    def _resolve_by_basename(self, path: str) -> str:
        """Try to resolve file path by matching basename."""
        all_docs = DBDocument.objects.all()
        for d in all_docs:
            if os.path.basename(d.path) == os.path.basename(path):
                return d.path
        return path
