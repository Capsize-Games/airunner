"""Dialog for downloading bootstrap models from HuggingFace.

Allows users to select which model categories to download (SD, LLM, STT, TTS, etc.)
and uses the standard HuggingFace download infrastructure with progress dialogs.
"""

import os
from typing import Dict, List, Optional, Callable

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QCheckBox,
    QGroupBox,
    QScrollArea,
    QWidget,
    QProgressBar,
    QMessageBox,
)
from PySide6.QtCore import Qt, QTimer

from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)
from airunner.components.data.bootstrap.model_bootstrap_data import (
    model_bootstrap_data,
)
from airunner.components.art.data.bootstrap.controlnet_bootstrap_data import (
    controlnet_bootstrap_data,
)
from airunner.components.art.data.bootstrap.sd_file_bootstrap_data import (
    SD_FILE_BOOTSTRAP_DATA,
)
from airunner.components.tts.data.bootstrap.openvoice_bootstrap_data import (
    OPENVOICE_FILES,
)
from airunner.components.llm.data.bootstrap.llm_file_bootstrap_data import (
    LLM_FILE_BOOTSTRAP_DATA,
)
from airunner.components.stt.data.bootstrap.whisper import WHISPER_FILES
from airunner.enums import SignalCode
from airunner.settings import AIRUNNER_LOG_LEVEL, AIRUNNER_ART_ENABLED
from airunner.utils.application import get_logger
from airunner.utils.application.mediator_mixin import MediatorMixin

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class DownloadModelsDialog(MediatorMixin, SettingsMixin, QDialog):
    """Dialog for selecting and downloading bootstrap models."""

    def __init__(self, parent: QWidget) -> None:
        """Initialize the download models dialog.

        Args:
            parent: Parent widget (main window).
        """
        self.signal_handlers = {}
        super().__init__(parent=parent)
        
        self.setWindowTitle("Download Models")
        self.setMinimumSize(500, 600)
        self.setModal(True)
        
        # Track selected models and download state
        self._selected_models: Dict[str, bool] = {}
        self._download_queue: List[Dict] = []
        self._current_download_index = 0
        self._is_downloading = False
        
        self._setup_ui()
        
    def _setup_ui(self) -> None:
        """Set up the dialog UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("Select Models to Download")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)
        
        description = QLabel(
            "Choose which model categories you want to download. "
            "Models will be downloaded from HuggingFace using your configured settings."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        
        # Scroll area for model checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(10)
        
        # Add model category groups
        if AIRUNNER_ART_ENABLED:
            self._add_sd_group(scroll_layout)
            self._add_controlnet_group(scroll_layout)
        
        self._add_llm_group(scroll_layout)
        self._add_stt_group(scroll_layout)
        self._add_tts_group(scroll_layout)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll, 1)
        
        # Progress section (hidden by default)
        self._progress_widget = QWidget()
        progress_layout = QVBoxLayout(self._progress_widget)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        
        self._progress_label = QLabel("Preparing downloads...")
        progress_layout.addWidget(self._progress_label)
        
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        progress_layout.addWidget(self._progress_bar)
        
        self._progress_widget.hide()
        layout.addWidget(self._progress_widget)
        
        # Button row
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self._cancel_button = QPushButton("Cancel")
        self._cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self._cancel_button)
        
        self._download_button = QPushButton("Download Selected")
        self._download_button.clicked.connect(self._start_downloads)
        self._download_button.setDefault(True)
        button_layout.addWidget(self._download_button)
        
        layout.addLayout(button_layout)
        
    def _add_sd_group(self, layout: QVBoxLayout) -> None:
        """Add Stable Diffusion model selection group."""
        group = QGroupBox("Stable Diffusion Models")
        group_layout = QVBoxLayout(group)
        
        # Get unique SD versions from model bootstrap data
        sd_models = [m for m in model_bootstrap_data if m.get("category") in ("stablediffusion", "flux", "zimage")]
        
        for model in sd_models:
            key = f"sd_{model['path']}"
            checkbox = QCheckBox(f"{model['name']} ({model['version']})")
            checkbox.setChecked(False)
            checkbox.stateChanged.connect(
                lambda state, k=key: self._on_checkbox_changed(k, state)
            )
            self._selected_models[key] = False
            group_layout.addWidget(checkbox)
            
            # Store model info for download
            setattr(checkbox, "_model_info", model)
        
        layout.addWidget(group)
        
    def _add_controlnet_group(self, layout: QVBoxLayout) -> None:
        """Add ControlNet model selection group."""
        if not controlnet_bootstrap_data:
            return
            
        group = QGroupBox("ControlNet Models")
        group_layout = QVBoxLayout(group)
        
        for model in controlnet_bootstrap_data:
            key = f"controlnet_{model['name']}"
            checkbox = QCheckBox(f"{model['display_name']} ({model['version']})")
            checkbox.setChecked(False)
            checkbox.stateChanged.connect(
                lambda state, k=key: self._on_checkbox_changed(k, state)
            )
            self._selected_models[key] = False
            group_layout.addWidget(checkbox)
            
            setattr(checkbox, "_model_info", model)
        
        layout.addWidget(group)
        
    def _add_llm_group(self, layout: QVBoxLayout) -> None:
        """Add LLM model selection group."""
        group = QGroupBox("Language Models (LLM)")
        group_layout = QVBoxLayout(group)
        
        llm_models = [m for m in model_bootstrap_data if m.get("category") == "llm"]
        
        for model in llm_models:
            key = f"llm_{model['path']}"
            action_label = "Embedding" if model["pipeline_action"] == "embedding" else "Chat"
            checkbox = QCheckBox(f"{model['name']} [{action_label}]")
            checkbox.setChecked(False)
            checkbox.stateChanged.connect(
                lambda state, k=key: self._on_checkbox_changed(k, state)
            )
            self._selected_models[key] = False
            group_layout.addWidget(checkbox)
            
            setattr(checkbox, "_model_info", model)
        
        layout.addWidget(group)
        
    def _add_stt_group(self, layout: QVBoxLayout) -> None:
        """Add Speech-to-Text model selection group."""
        group = QGroupBox("Speech-to-Text (STT)")
        group_layout = QVBoxLayout(group)
        
        for repo_id in WHISPER_FILES.keys():
            key = f"stt_{repo_id}"
            name = repo_id.split("/")[-1] if "/" in repo_id else repo_id
            checkbox = QCheckBox(name)
            checkbox.setChecked(False)
            checkbox.stateChanged.connect(
                lambda state, k=key: self._on_checkbox_changed(k, state)
            )
            self._selected_models[key] = False
            group_layout.addWidget(checkbox)
            
            setattr(checkbox, "_model_info", {"repo_id": repo_id, "type": "stt"})
        
        layout.addWidget(group)
        
    def _add_tts_group(self, layout: QVBoxLayout) -> None:
        """Add Text-to-Speech model selection group."""
        group = QGroupBox("Text-to-Speech (TTS / OpenVoice)")
        group_layout = QVBoxLayout(group)
        
        # Group by provider
        melo_models = []
        bert_models = []
        
        for repo_id in OPENVOICE_FILES.keys():
            if "MeloTTS" in repo_id:
                melo_models.append(repo_id)
            else:
                bert_models.append(repo_id)
        
        # Add MeloTTS models
        if melo_models:
            melo_label = QLabel("MeloTTS Models:")
            melo_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
            group_layout.addWidget(melo_label)
            
            for repo_id in melo_models:
                key = f"tts_{repo_id}"
                name = repo_id.split("/")[-1] if "/" in repo_id else repo_id
                checkbox = QCheckBox(name)
                checkbox.setChecked(False)
                checkbox.stateChanged.connect(
                    lambda state, k=key: self._on_checkbox_changed(k, state)
                )
                self._selected_models[key] = False
                group_layout.addWidget(checkbox)
                
                setattr(checkbox, "_model_info", {"repo_id": repo_id, "type": "tts"})
        
        # Add BERT models (for language support)
        if bert_models:
            bert_label = QLabel("Language Support (BERT):")
            bert_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
            group_layout.addWidget(bert_label)
            
            for repo_id in bert_models:
                key = f"tts_{repo_id}"
                name = repo_id.split("/")[-1] if "/" in repo_id else repo_id
                checkbox = QCheckBox(name)
                checkbox.setChecked(False)
                checkbox.stateChanged.connect(
                    lambda state, k=key: self._on_checkbox_changed(k, state)
                )
                self._selected_models[key] = False
                group_layout.addWidget(checkbox)
                
                setattr(checkbox, "_model_info", {"repo_id": repo_id, "type": "tts"})
        
        layout.addWidget(group)
        
    def _on_checkbox_changed(self, key: str, state: int) -> None:
        """Handle checkbox state change."""
        self._selected_models[key] = state == Qt.CheckState.Checked.value
        
    def _start_downloads(self) -> None:
        """Start downloading selected models."""
        # Check if HuggingFace downloads are allowed
        from airunner.components.application.gui.dialogs.privacy_consent_dialog import (
            is_huggingface_allowed,
        )
        if not is_huggingface_allowed():
            QMessageBox.warning(
                self,
                "Downloads Disabled",
                "HuggingFace downloads are disabled in privacy settings.\n\n"
                "You can enable them in Preferences → Privacy & Security → External Services."
            )
            return
            
        # Build download queue from selected models
        self._download_queue = []
        
        for key, selected in self._selected_models.items():
            if not selected:
                continue
                
            # Parse the key to determine model type
            if key.startswith("sd_"):
                repo_id = key[3:]  # Remove "sd_" prefix
                model = next(
                    (m for m in model_bootstrap_data if m["path"] == repo_id),
                    None
                )
                if model:
                    self._download_queue.append({
                        "repo_id": repo_id,
                        "model_type": model["model_type"],
                        "model_name": model["name"],
                        "output_dir": os.path.join(
                            self.path_settings.base_path,
                            model["model_type"],
                            "models",
                            model["version"],
                            model["pipeline_action"],
                        ),
                    })
                    
            elif key.startswith("controlnet_"):
                cn_name = key[11:]  # Remove "controlnet_" prefix
                model = next(
                    (m for m in controlnet_bootstrap_data if m["name"] == cn_name),
                    None
                )
                if model:
                    self._download_queue.append({
                        "repo_id": model["path"],
                        "model_type": "controlnet",
                        "model_name": model["display_name"],
                        "output_dir": os.path.join(
                            self.path_settings.base_path,
                            "art",
                            "models",
                            model["version"],
                            "controlnet",
                            model["path"],
                        ),
                    })
                    
            elif key.startswith("llm_"):
                repo_id = key[4:]  # Remove "llm_" prefix
                model = next(
                    (m for m in model_bootstrap_data if m["path"] == repo_id and m["category"] == "llm"),
                    None
                )
                if model:
                    self._download_queue.append({
                        "repo_id": repo_id,
                        "model_type": "llm",
                        "model_name": model["name"],
                        "output_dir": os.path.join(
                            self.path_settings.base_path,
                            "text",
                            "models",
                            model["category"],
                            model["pipeline_action"],
                            model["path"],
                        ),
                    })
                    
            elif key.startswith("stt_"):
                repo_id = key[4:]  # Remove "stt_" prefix
                self._download_queue.append({
                    "repo_id": repo_id,
                    "model_type": "stt",
                    "model_name": repo_id.split("/")[-1],
                    "output_dir": os.path.join(
                        self.path_settings.base_path,
                        "text",
                        "models",
                        "stt",
                        repo_id,
                    ),
                })
                
            elif key.startswith("tts_"):
                repo_id = key[4:]  # Remove "tts_" prefix
                self._download_queue.append({
                    "repo_id": repo_id,
                    "model_type": "tts",
                    "model_name": repo_id.split("/")[-1],
                    "output_dir": os.path.join(
                        self.path_settings.base_path,
                        "text",
                        "models",
                        "tts",
                        repo_id,
                    ),
                })
        
        if not self._download_queue:
            QMessageBox.information(
                self,
                "No Models Selected",
                "Please select at least one model to download."
            )
            return
            
        # Start the download process
        self._current_download_index = 0
        self._is_downloading = True
        self._download_button.setEnabled(False)
        self._download_next()
        
    def _download_next(self) -> None:
        """Download the next model in the queue."""
        if self._current_download_index >= len(self._download_queue):
            # All downloads complete
            self._on_all_downloads_complete()
            return
            
        download = self._download_queue[self._current_download_index]
        
        # Update progress
        progress = int((self._current_download_index / len(self._download_queue)) * 100)
        self._progress_bar.setValue(progress)
        self._progress_label.setText(
            f"Downloading {self._current_download_index + 1}/{len(self._download_queue)}: "
            f"{download['model_name']}"
        )
        self._progress_widget.show()
        
        # Emit signal to start download using the standard infrastructure
        self.emit_signal(
            SignalCode.START_HUGGINGFACE_DOWNLOAD,
            {
                "repo_id": download["repo_id"],
                "model_path": download["output_dir"],
                "model_type": download["model_type"],
                "callback": self._on_single_download_complete,
            }
        )
        
    def _on_single_download_complete(self) -> None:
        """Handle completion of a single download."""
        self._current_download_index += 1
        # Small delay before starting next download
        QTimer.singleShot(500, self._download_next)
        
    def _on_all_downloads_complete(self) -> None:
        """Handle completion of all downloads."""
        self._is_downloading = False
        self._progress_bar.setValue(100)
        self._progress_label.setText("All downloads complete!")
        
        QMessageBox.information(
            self,
            "Downloads Complete",
            f"Successfully queued {len(self._download_queue)} model(s) for download.\n\n"
            "Downloads are processed in the background. Check the status bar for progress."
        )
        
        self.accept()
        
    def reject(self) -> None:
        """Handle dialog rejection (cancel)."""
        if self._is_downloading:
            reply = QMessageBox.question(
                self,
                "Cancel Downloads?",
                "Downloads are in progress. Are you sure you want to cancel?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
                
        super().reject()


def show_download_models_dialog(parent: QWidget) -> None:
    """Show the download models dialog.
    
    Args:
        parent: Parent widget (main window).
    """
    dialog = DownloadModelsDialog(parent)
    dialog.exec()
