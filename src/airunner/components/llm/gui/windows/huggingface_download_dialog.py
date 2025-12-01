"""Dialog for showing HuggingFace model download progress."""

from typing import Dict

from PySide6.QtWidgets import (
    QDialog,
    QTableWidgetItem,
    QHeaderView,
    QProgressBar,
    QDialogButtonBox,
    QVBoxLayout,
    QLabel,
)
from PySide6.QtCore import Qt, QTimer

from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)
from airunner.components.llm.gui.windows.templates.huggingface_download_dialog_ui import (
    Ui_HuggingFaceDownloadDialog,
)
from airunner.components.settings.gui.widgets.huggingface_settings.huggingface_settings_widget import (
    HuggingfaceSettingsWidget,
)
from airunner.enums import SignalCode
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.utils.settings.get_qsettings import get_qsettings

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class HuggingFaceDownloadDialog(MediatorMixin, SettingsMixin, QDialog):
    """Dialog for showing HuggingFace model download progress with real-time updates."""

    def __init__(self, parent, model_name: str, model_path: str, batch_mode: bool = False):
        """
        Initialize the download dialog.

        Args:
            parent: Parent widget
            model_name: Display name of model being downloaded
            model_path: Path where model will be saved
            batch_mode: If True, dialog will NOT auto-register for download signals
                        and will NOT auto-close on download_complete. The caller
                        must manage signals and closing explicitly.
        """
        # NOTE: We do NOT register for HUGGINGFACE_DOWNLOAD_COMPLETE here!
        # This caused issues where multiple dialogs would all close when
        # ANY download completed. The caller must explicitly connect signals.
        self.signal_handlers = {}
        self._batch_mode = batch_mode
        super().__init__(parent=parent)

        self.model_name = model_name
        self.model_path = model_path
        self._last_progress = -1.0
        self._progress_started = False
        self._file_progress_bars: Dict[str, QProgressBar] = {}

        self.ui = Ui_HuggingFaceDownloadDialog()
        self.ui.setupUi(self)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Configure UI components after loading from template."""
        self.ui.title_label.setText(f"Downloading {self.model_name}")
        self.ui.path_label.setText(f"Destination: {self.model_path}")

        header = self.ui.file_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

        self.ui.cancel_button.clicked.connect(self.on_cancel_clicked)

    def on_progress_updated(self, data: dict) -> None:
        """Update overall progress bar and status label."""
        progress = data.get("progress", 0.0)

        if progress <= 0:
            self.ui.stats_label.setText("Preparing to download...")
            return

        if not self._progress_started:
            self._progress_started = True
            self.ui.progress_bar.setRange(0, 1000)
            self.ui.stats_label.setText("Downloading...")

        if abs(progress - self._last_progress) >= 0.01:
            self._last_progress = progress
            scaled_value = min(1000, int(round(progress * 10.0)))
            self.ui.progress_bar.setValue(scaled_value)
            self.ui.progress_bar.setFormat(f"{progress:.1f}%")

            if progress < 100:
                self.ui.stats_label.setText(
                    f"Downloading... {progress:.1f}% complete"
                )
            else:
                self.ui.stats_label.setText("Download complete!")

    def on_file_progress_updated(self, data: dict) -> None:
        """Update per-file progress in the table."""
        filename = data.get("filename", "")
        downloaded = data.get("downloaded", 0)
        total = data.get("total", 0)

        if filename not in self._file_progress_bars:
            row = self.ui.file_table.rowCount()
            self.ui.file_table.insertRow(row)

            name_item = QTableWidgetItem(filename)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.ui.file_table.setItem(row, 0, name_item)

            progress_bar = QProgressBar()
            progress_bar.setRange(0, 1000)
            progress_bar.setValue(0)
            progress_bar.setTextVisible(True)
            progress_bar.setFormat("0.0%")
            self.ui.file_table.setCellWidget(row, 1, progress_bar)
            self.ui.file_table.setRowHeight(
                row, max(progress_bar.sizeHint().height(), 22)
            )
            self.ui.file_table.resizeRowToContents(row)

            self._file_progress_bars[filename] = progress_bar

        progress_bar = self._file_progress_bars[filename]
        if total > 0:
            percent = min(100.0, (downloaded * 100.0) / total)
            scaled_value = min(1000, int(round(percent * 10.0)))
            progress_bar.setValue(scaled_value)
            progress_bar.setFormat(f"{percent:.1f}%")

    def on_log_updated(self, data: dict) -> None:
        """Append message to log display."""
        message = data.get("message", "")
        if message:
            self.ui.log_display.append(message)
            scrollbar = self.ui.log_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def on_download_complete(self, data: dict) -> None:
        """Handle successful download completion.
        
        In batch mode, this just updates the UI but doesn't auto-close.
        """
        self.ui.log_display.append("\n✓ Download complete!")
        self.ui.progress_bar.setValue(1000)
        
        if self._batch_mode:
            # In batch mode, don't auto-close - caller will close when all done
            self.ui.log_display.append("All downloads finished!")
            self.ui.cancel_button.setText("Close")
            self.ui.cancel_button.setEnabled(True)
        else:
            self.ui.log_display.append(
                "Closing dialog and proceeding with model setup..."
            )
            self.ui.cancel_button.setEnabled(False)
            # Close dialog after brief delay
            QTimer.singleShot(1000, self.accept)

    def on_download_failed(self, data: dict) -> None:
        """Handle download failure."""
        error = data.get("error", "Unknown error")
        self.ui.log_display.append(f"\n✗ Download failed: {error}")

        if "401" in str(error) and "Unauthorized" in str(error):
            self._handle_auth_error()
        else:
            self.ui.cancel_button.setText("Close")

    def _handle_auth_error(self) -> None:
        """Handle 401 Unauthorized errors."""
        settings = get_qsettings()
        api_key = settings.value("huggingface/api_key", "")

        if not api_key:
            self.ui.log_display.append("\n⚠ Authentication required!")
            self.ui.log_display.append(
                "You need to configure your HuggingFace API key."
            )
            self.ui.cancel_button.setText("Close")

            QTimer.singleShot(1500, self._show_api_key_dialog)
        else:
            self.ui.log_display.append("\n⚠ Access denied!")
            self.ui.log_display.append(
                "You have an API key configured, but access was denied."
            )
            self.ui.log_display.append(
                "\nThis model may require you to accept a license agreement."
            )
            self.ui.log_display.append(
                "Please visit the model page on HuggingFace"
            )
            self.ui.log_display.append(
                "and click 'Agree and access repository' if prompted."
            )
            self.ui.cancel_button.setText("Close")

    def _show_api_key_dialog(self) -> None:
        """Show dialog for entering HuggingFace API key."""
        dialog = QDialog(self.parent())
        dialog.setWindowTitle("HuggingFace API Key Required")
        dialog.setMinimumSize(500, 250)

        layout = QVBoxLayout(dialog)

        explanation = QLabel(
            "This model requires authentication with HuggingFace.\n\n"
            "Please enter your HuggingFace API key below, then click OK to retry the download:"
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)

        settings_widget = HuggingfaceSettingsWidget()
        layout.addWidget(settings_widget)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            logger.info(
                "API key configured, but cannot retry download from here"
            )
            self.reject()
        else:
            self.reject()

    def on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        self.ui.log_display.append("\nCancelling download...")
        self.emit_signal(SignalCode.CANCEL_HUGGINGFACE_DOWNLOAD, {})
        self.ui.cancel_button.setEnabled(False)
        self.reject()

    def closeEvent(self, event) -> None:
        """Handle dialog close event."""
        self.emit_signal(SignalCode.CANCEL_HUGGINGFACE_DOWNLOAD, {})
        super().closeEvent(event)
