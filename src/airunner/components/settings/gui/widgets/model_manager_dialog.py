"""Manage Models Dialog for downloading, deleting, and configuring LLM models.

Provides a comprehensive UI for:
- Viewing available models from HuggingFace
- Downloading models using the preferred artifact format
- Deleting local models
- Viewing model details and disk usage
"""

from typing import Optional, Dict
import os

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QComboBox,
    QMessageBox,
    QHeaderView,
    QProgressBar,
    QGroupBox,
    QTextEdit,
)
from PySide6.QtCore import Qt, Signal, Slot

from airunner.components.llm.config.provider_config import LLMProviderConfig
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)
from airunner.utils.application.mediator_mixin import MediatorMixin


class ManageModelsDialog(MediatorMixin, SettingsMixin, QDialog):
    """Dialog for managing local LLM models.

    Features:
    - Browse available HuggingFace models
    - Download models using AIRunner's preferred artifact
    - View local model disk usage
    - Delete local models
    - View model capabilities and requirements
    """

    # Signals
    download_requested = Signal(dict)
    delete_requested = Signal(str)  # model_path

    def __init__(self, parent: Optional[QDialog] = None):
        """Initialize manage models dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Manage Models")
        self.setMinimumSize(900, 600)
        self._setup_ui()
        self._populate_models()

    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Header
        header_label = QLabel("LLM Model Management")
        header_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; padding: 10px;"
        )
        layout.addWidget(header_label)

        # Available models section
        available_group = QGroupBox("Available Models (HuggingFace)")
        available_layout = QVBoxLayout(available_group)

        # Models table
        self.models_table = QTableWidget()
        self.models_table.setColumnCount(6)
        self.models_table.setHorizontalHeaderLabels(
            [
                "Model",
                "Context",
                "VRAM (4-bit)",
                "Tool Calling",
                "Status",
                "Actions",
            ]
        )
        self.models_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        self.models_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.models_table.setSelectionMode(QTableWidget.SingleSelection)
        available_layout.addWidget(self.models_table)

        layout.addWidget(available_group)

        # Model details section
        details_group = QGroupBox("Model Details")
        details_layout = QVBoxLayout(details_group)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(150)
        details_layout.addWidget(self.details_text)

        layout.addWidget(details_group)

        # Download progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._populate_models)
        button_layout.addWidget(self.refresh_button)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def _populate_models(self):
        """Populate the models table with available models."""
        self.models_table.setRowCount(0)

        # Get local models from provider config
        models = LLMProviderConfig.LOCAL_MODELS

        for row, (model_id, model_info) in enumerate(models.items()):
            if model_id == "custom":
                continue  # Skip custom entry

            self.models_table.insertRow(row)

            # Model name
            name_item = QTableWidgetItem(model_info["name"])
            name_item.setData(Qt.UserRole, model_id)
            self.models_table.setItem(row, 0, name_item)

            # Context length
            context = model_info.get("context_length", 0)
            if context >= 1000000:
                context_text = f"{context // 1000000}M"
            elif context >= 1000:
                context_text = f"{context // 1000}K"
            else:
                context_text = str(context)
            self.models_table.setItem(row, 1, QTableWidgetItem(context_text))

            # VRAM (4-bit)
            vram_4bit = model_info.get("vram_4bit_gb", 0)
            vram_text = f"~{vram_4bit} GB" if vram_4bit > 0 else "Unknown"
            self.models_table.setItem(row, 2, QTableWidgetItem(vram_text))

            # Tool calling
            has_tools = model_info.get("function_calling", False)
            tool_mode = model_info.get("tool_calling_mode", "none")
            tools_text = f"Yes ({tool_mode})" if has_tools else "No"
            self.models_table.setItem(row, 3, QTableWidgetItem(tools_text))

            # Status (check if downloaded)
            artifact_path = self._get_model_artifact_path(
                model_info["name"],
                model_id,
            )
            is_downloaded = os.path.exists(artifact_path)
            status_text = "Downloaded" if is_downloaded else "Not Downloaded"
            status_item = QTableWidgetItem(status_text)
            if is_downloaded:
                status_item.setForeground(Qt.darkGreen)
            self.models_table.setItem(row, 4, status_item)

            # Action buttons
            button_widget = self._create_action_buttons(
                model_id, model_info, is_downloaded
            )
            self.models_table.setCellWidget(row, 5, button_widget)

        # Connect selection change
        self.models_table.itemSelectionChanged.connect(
            self._on_selection_changed
        )

    def _create_action_buttons(
        self, model_id: str, model_info: Dict, is_downloaded: bool
    ) -> QTableWidget:
        """Create action buttons for a model row.

        Args:
            model_id: Model identifier
            model_info: Model information dict
            is_downloaded: Whether model is already downloaded

        Returns:
            Widget containing action buttons
        """
        button_widget = QTableWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(2, 2, 2, 2)

        if not is_downloaded:
            has_gguf = LLMProviderConfig.has_gguf_variant(model_id)
            download_btn = QPushButton(
                "Download GGUF" if has_gguf else "Download"
            )
            download_btn.clicked.connect(
                lambda checked, mid=model_id, mi=model_info: self._on_download_clicked(
                    mid,
                    mi,
                )
            )
            button_layout.addWidget(download_btn)
        else:
            # Delete button
            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(
                lambda checked, mi=model_info: self._on_delete_clicked(mi)
            )
            button_layout.addWidget(delete_btn)

        button_layout.addStretch()
        return button_widget

    def _get_model_path(self, model_name: str, model_id: Optional[str] = None) -> str:
        """Get the local storage directory for a model.

        Args:
            model_name: Model name
            model_id: Optional provider-config model identifier

        Returns:
            Absolute path to model storage directory
        """
        resolved_model_id = model_id or LLMProviderConfig.get_model_id_for_name(
            "local",
            model_name,
        )
        return LLMProviderConfig.get_local_storage_path(
            self.path_settings.base_path,
            "local",
            model_id=resolved_model_id or None,
        )

    def _get_model_artifact_path(
        self,
        model_name: str,
        model_id: Optional[str] = None,
    ) -> str:
        """Get the exact file or directory that indicates the model is installed."""
        resolved_model_id = model_id or LLMProviderConfig.get_model_id_for_name(
            "local",
            model_name,
        )
        return LLMProviderConfig.get_expected_local_artifact_path(
            self.path_settings.base_path,
            "local",
            model_id=resolved_model_id or None,
        )

    @Slot()
    def _on_selection_changed(self):
        """Handle table selection change to show model details."""
        selected_items = self.models_table.selectedItems()
        if not selected_items:
            self.details_text.clear()
            return

        row = selected_items[0].row()
        name_item = self.models_table.item(row, 0)
        model_id = name_item.data(Qt.UserRole)

        # Get model info
        model_info = LLMProviderConfig.LOCAL_MODELS.get(model_id)
        if not model_info:
            return

        # Build details text
        details = []
        details.append(f"<b>Model:</b> {model_info['name']}")
        details.append(
            f"<b>Repository:</b> {model_info.get('repo_id', 'N/A')}"
        )
        details.append(f"<b>Type:</b> {model_info.get('model_type', 'llm')}")
        details.append(
            f"<b>Context Length:</b> {model_info.get('context_length', 0):,} tokens"
        )

        # VRAM requirements
        details.append("<b>VRAM Requirements:</b>")
        details.append(f"  • 2-bit: ~{model_info.get('vram_2bit_gb', 0)} GB")
        details.append(f"  • 4-bit: ~{model_info.get('vram_4bit_gb', 0)} GB")
        details.append(f"  • 8-bit: ~{model_info.get('vram_8bit_gb', 0)} GB")

        # Capabilities
        has_tools = model_info.get("function_calling", False)
        tool_mode = model_info.get("tool_calling_mode", "none")
        details.append(
            f"<b>Function Calling:</b> {'Yes' if has_tools else 'No'}"
        )
        if has_tools:
            details.append(f"<b>Tool Calling Mode:</b> {tool_mode}")

        # Description
        if model_info.get("description"):
            details.append(
                f"<br><b>Description:</b><br>{model_info['description']}"
            )

        # Check local status
        artifact_path = self._get_model_artifact_path(
            model_info["name"],
            model_id,
        )
        if os.path.exists(artifact_path):
            # Get disk usage
            try:
                if os.path.isfile(artifact_path):
                    total_size = os.path.getsize(artifact_path)
                else:
                    total_size = 0
                    for dirpath, dirnames, filenames in os.walk(artifact_path):
                        for filename in filenames:
                            filepath = os.path.join(dirpath, filename)
                            total_size += os.path.getsize(filepath)

                size_gb = total_size / (1024**3)
                details.append(f"<br><b>Disk Usage:</b> {size_gb:.2f} GB")
                details.append(f"<b>Location:</b> {artifact_path}")
            except Exception as e:
                details.append(
                    f"<br><b>Status:</b> Error reading disk usage: {e}"
                )

        self.details_text.setHtml("<br>".join(details))

    @Slot()
    def _on_download_clicked(self, model_id: str, model_info: Dict):
        """Handle download button click.

        Args:
            model_id: Model identifier
            model_info: Model information
        """
        download_info = LLMProviderConfig.resolve_download_target(
            "local",
            model_id=model_id,
            prefer_pre_quantized=True,
        )
        if not download_info or not download_info.get("repo_id"):
            QMessageBox.warning(
                self,
                "Cannot Download",
                f"No download source found for {model_info['name']}",
            )
            return

        is_gguf = download_info.get("model_type") == "gguf"
        repo_id = download_info["repo_id"]
        quant_bits = download_info.get("quantization_bits") or 4
        format_label = "Pre-quantized GGUF" if is_gguf else "Transformers"
        file_label = download_info.get("gguf_filename")

        # Confirm download
        msg = (
            f"Download {model_info['name']}?\n\n"
            f"Format: {format_label}\n"
            f"Estimated VRAM: ~{model_info.get(f'vram_{quant_bits}bit_gb', 0)} GB\n"
            f"Repository: {repo_id}"
        )
        if file_label:
            msg += f"\nFile: {file_label}"

        reply = QMessageBox.question(
            self,
            "Confirm Download",
            msg,
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            payload = {
                "model_id": model_id,
                "model_name": model_info["name"],
                "model_path": self._get_model_path(model_info["name"], model_id),
                "repo_id": repo_id,
                "model_type": download_info.get("model_type", "llm"),
                "quantization_bits": download_info.get("quantization_bits") or 4,
            }
            if file_label:
                payload["gguf_filename"] = file_label

            self.download_requested.emit(payload)

            # Show progress bar
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate

    @Slot()
    def _on_delete_clicked(self, model_info: Dict):
        """Handle delete button click.

        Args:
            model_info: Model information
        """
        model_id = LLMProviderConfig.get_model_id_for_name(
            "local",
            model_info["name"],
        )
        model_path = self._get_model_artifact_path(model_info["name"], model_id)

        # Confirm deletion
        msg = (
            f"Delete {model_info['name']}?\n\n"
            f"This will remove all files from:\n{model_path}\n\n"
            f"This action cannot be undone."
        )

        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            msg,
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            # Emit signal to delete model
            self.delete_requested.emit(model_path)

            # Refresh table
            self._populate_models()

    def set_download_progress(self, progress: int):
        """Set download progress.

        Args:
            progress: Progress percentage (0-100)
        """
        self.progress_bar.setVisible(True)

        if progress < 0:
            self.progress_bar.setRange(0, 0)  # Indeterminate
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(progress)

    def download_complete(self):
        """Handle download completion."""
        self.progress_bar.setVisible(False)
        self._populate_models()

        QMessageBox.information(
            self,
            "Download Complete",
            "Model download completed successfully!",
        )

    def download_failed(self, error: str):
        """Handle download failure.

        Args:
            error: Error message
        """
        self.progress_bar.setVisible(False)

        QMessageBox.critical(
            self,
            "Download Failed",
            f"Model download failed:\n\n{error}",
        )
