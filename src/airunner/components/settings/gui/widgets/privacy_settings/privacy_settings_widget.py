"""Privacy settings widget for the settings window.

Allows users to modify external service permissions after initial setup.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QGroupBox,
    QPushButton,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.application.gui.dialogs.privacy_consent_dialog import (
    SERVICE_HUGGINGFACE_KEY,
    SERVICE_CIVITAI_KEY,
    SERVICE_DUCKDUCKGO_KEY,
    SERVICE_OPENMETEO_KEY,
    SERVICE_OPENROUTER_KEY,
    SERVICE_OPENAI_KEY,
)
from airunner.utils.settings import get_qsettings


class PrivacySettingsWidget(BaseWidget):
    """Widget for managing external service permissions."""

    def __init__(self, *args, **kwargs):
        """Initialize the privacy settings widget."""
        super().__init__(*args, **kwargs)
        self._checkboxes = {}
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self) -> None:
        """Set up the widget UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)

        # Introduction
        intro = QLabel(
            "Control which external services AI Runner can connect to. "
            "Disabling a service will prevent that functionality from working."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        # Model Downloads Group
        downloads_group = QGroupBox("Model Downloads")
        downloads_layout = QVBoxLayout(downloads_group)

        self._add_checkbox(
            downloads_layout,
            SERVICE_HUGGINGFACE_KEY,
            "Allow HuggingFace downloads",
            "Download models from HuggingFace (LLM, STT, TTS, Stable Diffusion)",
            True,
        )
        self._add_checkbox(
            downloads_layout,
            SERVICE_CIVITAI_KEY,
            "Allow CivitAI downloads",
            "Download community models, LoRAs, and embeddings from CivitAI",
            True,
        )
        layout.addWidget(downloads_group)

        # Search & Research Group
        search_group = QGroupBox("Search & Research")
        search_layout = QVBoxLayout(search_group)

        self._add_checkbox(
            search_layout,
            SERVICE_DUCKDUCKGO_KEY,
            "Allow DuckDuckGo web search",
            "Enable web search and Deep Research features",
            True,
        )
        layout.addWidget(search_group)

        # Weather Group
        weather_group = QGroupBox("Weather Information")
        weather_layout = QVBoxLayout(weather_group)

        self._add_checkbox(
            weather_layout,
            SERVICE_OPENMETEO_KEY,
            "Allow Open-Meteo weather API",
            "Send your location coordinates to get weather information",
            False,
        )
        layout.addWidget(weather_group)

        # External LLM Providers Group
        llm_group = QGroupBox("External LLM Providers")
        llm_layout = QVBoxLayout(llm_group)

        self._add_checkbox(
            llm_layout,
            SERVICE_OPENROUTER_KEY,
            "Allow OpenRouter API",
            "Use OpenRouter for cloud-based LLM inference",
            True,
        )
        self._add_checkbox(
            llm_layout,
            SERVICE_OPENAI_KEY,
            "Allow OpenAI API",
            "Use OpenAI for cloud-based LLM inference",
            True,
        )
        layout.addWidget(llm_group)

        # Action buttons
        button_layout = QHBoxLayout()
        
        enable_all_btn = QPushButton("Enable All")
        enable_all_btn.clicked.connect(self._enable_all)
        button_layout.addWidget(enable_all_btn)

        disable_all_btn = QPushButton("Disable All")
        disable_all_btn.clicked.connect(self._disable_all)
        button_layout.addWidget(disable_all_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        layout.addStretch()

    def _add_checkbox(
        self,
        layout: QVBoxLayout,
        key: str,
        label: str,
        description: str,
        default: bool,
    ) -> None:
        """Add a checkbox with description.

        Args:
            layout: Parent layout to add to.
            key: QSettings key for this setting.
            label: Checkbox label text.
            description: Description text below checkbox.
            default: Default value if not set.
        """
        checkbox = QCheckBox(label)
        checkbox.setChecked(default)
        checkbox.stateChanged.connect(lambda state: self._on_checkbox_changed(key, state))
        layout.addWidget(checkbox)

        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #888; margin-left: 20px; font-size: 11px;")
        layout.addWidget(desc_label)

        self._checkboxes[key] = checkbox

    def _load_settings(self) -> None:
        """Load current settings from QSettings."""
        settings = get_qsettings()

        defaults = {
            SERVICE_HUGGINGFACE_KEY: True,
            SERVICE_CIVITAI_KEY: True,
            SERVICE_DUCKDUCKGO_KEY: True,
            SERVICE_OPENMETEO_KEY: False,
            SERVICE_OPENROUTER_KEY: True,
            SERVICE_OPENAI_KEY: True,
        }

        for key, checkbox in self._checkboxes.items():
            default = defaults.get(key, True)
            value = settings.value(key, default, type=bool)
            checkbox.blockSignals(True)
            checkbox.setChecked(value)
            checkbox.blockSignals(False)

    def _on_checkbox_changed(self, key: str, state: int) -> None:
        """Handle checkbox state change.

        Args:
            key: QSettings key for the setting.
            state: New checkbox state (Qt.CheckState).
        """
        settings = get_qsettings()
        checked = state == Qt.CheckState.Checked.value
        settings.setValue(key, checked)
        settings.sync()

    def _enable_all(self) -> None:
        """Enable all services."""
        for checkbox in self._checkboxes.values():
            checkbox.setChecked(True)

    def _disable_all(self) -> None:
        """Disable all services."""
        for checkbox in self._checkboxes.values():
            checkbox.setChecked(False)
