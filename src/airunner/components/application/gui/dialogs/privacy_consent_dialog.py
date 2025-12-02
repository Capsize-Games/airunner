"""Privacy consent dialog for AI Runner.

Shows on first launch to let users opt out of external services.
Services are controlled via QSettings for persistent storage.
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QCheckBox,
    QGroupBox,
    QWidget,
    QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from airunner.utils.settings import get_qsettings


# QSettings keys for external service toggles
PRIVACY_CONSENT_SHOWN_KEY = "privacy/consent_shown"
SERVICE_HUGGINGFACE_KEY = "privacy/allow_huggingface"
SERVICE_CIVITAI_KEY = "privacy/allow_civitai"
SERVICE_DUCKDUCKGO_KEY = "privacy/allow_duckduckgo"
SERVICE_OPENMETEO_KEY = "privacy/allow_openmeteo"
SERVICE_OPENROUTER_KEY = "privacy/allow_openrouter"
SERVICE_OPENAI_KEY = "privacy/allow_openai"


class PrivacyConsentDialog(QDialog):
    """Dialog for users to opt in/out of external services on first launch."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the privacy consent dialog.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Privacy Settings")
        self.setMinimumSize(600, 550)
        self.setMaximumSize(700, 700)
        self.setModal(True)
        
        self._checkboxes = {}
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self) -> None:
        """Set up the dialog UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        # Header
        header = QLabel("🔒 Privacy & External Services")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header.setFont(header_font)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Introduction
        intro = QLabel(
            "AI Runner is designed to run locally with maximum privacy. "
            "However, some features require connecting to external services. "
            "Please review and select which services you want to enable.\n\n"
            "You can change these settings at any time in Preferences → Privacy Settings."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        # Scroll area for service checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(10)

        # Model Downloads Group
        self._add_downloads_group(scroll_layout)
        
        # Search & Research Group
        self._add_search_group(scroll_layout)
        
        # Weather Group
        self._add_weather_group(scroll_layout)
        
        # External LLM Providers Group
        self._add_llm_providers_group(scroll_layout)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll, 1)

        # VPN recommendation
        vpn_label = QLabel(
            "💡 <b>Tip:</b> We recommend using a VPN when connecting to external services "
            "for additional privacy protection."
        )
        vpn_label.setWordWrap(True)
        vpn_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(vpn_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        enable_all_btn = QPushButton("Enable All")
        enable_all_btn.clicked.connect(self._enable_all)
        button_layout.addWidget(enable_all_btn)

        disable_all_btn = QPushButton("Disable All")
        disable_all_btn.clicked.connect(self._disable_all)
        button_layout.addWidget(disable_all_btn)

        button_layout.addStretch()

        save_btn = QPushButton("Save && Continue")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save_and_close)
        save_btn.setMinimumWidth(120)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _add_downloads_group(self, layout: QVBoxLayout) -> None:
        """Add model downloads service group."""
        group = QGroupBox("Model Downloads")
        group_layout = QVBoxLayout(group)

        # HuggingFace
        hf_checkbox = QCheckBox("HuggingFace")
        hf_checkbox.setChecked(True)
        hf_desc = QLabel(
            "Download LLM, STT, TTS, and Stable Diffusion models from HuggingFace.\n"
            "Your IP address may be logged by HuggingFace."
        )
        hf_desc.setWordWrap(True)
        hf_desc.setStyleSheet("color: #888; margin-left: 20px; font-size: 11px;")
        group_layout.addWidget(hf_checkbox)
        group_layout.addWidget(hf_desc)
        self._checkboxes[SERVICE_HUGGINGFACE_KEY] = hf_checkbox

        # CivitAI
        civitai_checkbox = QCheckBox("CivitAI")
        civitai_checkbox.setChecked(True)
        civitai_desc = QLabel(
            "Download community models, LoRAs, and embeddings from CivitAI.\n"
            "Your IP address and download requests may be logged."
        )
        civitai_desc.setWordWrap(True)
        civitai_desc.setStyleSheet("color: #888; margin-left: 20px; font-size: 11px;")
        group_layout.addWidget(civitai_checkbox)
        group_layout.addWidget(civitai_desc)
        self._checkboxes[SERVICE_CIVITAI_KEY] = civitai_checkbox

        layout.addWidget(group)

    def _add_search_group(self, layout: QVBoxLayout) -> None:
        """Add search and research service group."""
        group = QGroupBox("Search & Research")
        group_layout = QVBoxLayout(group)

        # DuckDuckGo
        ddg_checkbox = QCheckBox("DuckDuckGo Web Search")
        ddg_checkbox.setChecked(True)
        ddg_desc = QLabel(
            "Enable web search and Deep Research features using DuckDuckGo.\n"
            "Search queries are sent to DuckDuckGo servers. Disabling this will "
            "prevent the AI from searching the internet."
        )
        ddg_desc.setWordWrap(True)
        ddg_desc.setStyleSheet("color: #888; margin-left: 20px; font-size: 11px;")
        group_layout.addWidget(ddg_checkbox)
        group_layout.addWidget(ddg_desc)
        self._checkboxes[SERVICE_DUCKDUCKGO_KEY] = ddg_checkbox

        layout.addWidget(group)

    def _add_weather_group(self, layout: QVBoxLayout) -> None:
        """Add weather service group."""
        group = QGroupBox("Weather Information")
        group_layout = QVBoxLayout(group)

        # Open-Meteo
        weather_checkbox = QCheckBox("Open-Meteo Weather API")
        weather_checkbox.setChecked(False)  # Disabled by default
        weather_desc = QLabel(
            "Allow the AI to access current weather information for your location.\n"
            "Your latitude/longitude coordinates are sent to api.open-meteo.com."
        )
        weather_desc.setWordWrap(True)
        weather_desc.setStyleSheet("color: #888; margin-left: 20px; font-size: 11px;")
        group_layout.addWidget(weather_checkbox)
        group_layout.addWidget(weather_desc)
        self._checkboxes[SERVICE_OPENMETEO_KEY] = weather_checkbox

        layout.addWidget(group)

    def _add_llm_providers_group(self, layout: QVBoxLayout) -> None:
        """Add external LLM providers group."""
        group = QGroupBox("External LLM Providers")
        group_layout = QVBoxLayout(group)

        # OpenRouter
        openrouter_checkbox = QCheckBox("OpenRouter")
        openrouter_checkbox.setChecked(True)
        openrouter_desc = QLabel(
            "Allow using OpenRouter API for cloud-based LLM inference.\n"
            "Your prompts and conversations are sent to OpenRouter servers."
        )
        openrouter_desc.setWordWrap(True)
        openrouter_desc.setStyleSheet("color: #888; margin-left: 20px; font-size: 11px;")
        group_layout.addWidget(openrouter_checkbox)
        group_layout.addWidget(openrouter_desc)
        self._checkboxes[SERVICE_OPENROUTER_KEY] = openrouter_checkbox

        # OpenAI
        openai_checkbox = QCheckBox("OpenAI")
        openai_checkbox.setChecked(True)
        openai_desc = QLabel(
            "Allow using OpenAI API for cloud-based LLM inference.\n"
            "Your prompts and conversations are sent to OpenAI servers."
        )
        openai_desc.setWordWrap(True)
        openai_desc.setStyleSheet("color: #888; margin-left: 20px; font-size: 11px;")
        group_layout.addWidget(openai_checkbox)
        group_layout.addWidget(openai_desc)
        self._checkboxes[SERVICE_OPENAI_KEY] = openai_checkbox

        layout.addWidget(group)

    def _load_settings(self) -> None:
        """Load existing settings from QSettings."""
        settings = get_qsettings()
        
        for key, checkbox in self._checkboxes.items():
            # Default to True for most services, False for weather
            default = key != SERVICE_OPENMETEO_KEY
            value = settings.value(key, default, type=bool)
            checkbox.setChecked(value)

    def _enable_all(self) -> None:
        """Enable all services."""
        for checkbox in self._checkboxes.values():
            checkbox.setChecked(True)

    def _disable_all(self) -> None:
        """Disable all services."""
        for checkbox in self._checkboxes.values():
            checkbox.setChecked(False)

    def _save_and_close(self) -> None:
        """Save settings and close the dialog."""
        settings = get_qsettings()
        
        for key, checkbox in self._checkboxes.items():
            settings.setValue(key, checkbox.isChecked())
        
        # Mark consent as shown
        settings.setValue(PRIVACY_CONSENT_SHOWN_KEY, True)
        settings.sync()
        
        self.accept()

    @classmethod
    def should_show(cls) -> bool:
        """Check if the privacy consent dialog should be shown.

        Returns:
            True if dialog should be shown (first launch), False otherwise.
        """
        settings = get_qsettings()
        shown = settings.value(PRIVACY_CONSENT_SHOWN_KEY, False, type=bool)
        return not shown

    @classmethod
    def show_if_needed(cls, parent: QWidget | None = None) -> None:
        """Show the privacy consent dialog if it hasn't been shown before.

        Args:
            parent: Optional parent widget for the dialog.
        """
        if cls.should_show():
            dialog = cls(parent)
            dialog.exec()


# Utility functions to check service availability
def is_huggingface_allowed() -> bool:
    """Check if HuggingFace downloads are allowed."""
    settings = get_qsettings()
    return settings.value(SERVICE_HUGGINGFACE_KEY, True, type=bool)


def is_civitai_allowed() -> bool:
    """Check if CivitAI downloads are allowed."""
    settings = get_qsettings()
    return settings.value(SERVICE_CIVITAI_KEY, True, type=bool)


def is_duckduckgo_allowed() -> bool:
    """Check if DuckDuckGo search is allowed."""
    settings = get_qsettings()
    return settings.value(SERVICE_DUCKDUCKGO_KEY, True, type=bool)


def is_openmeteo_allowed() -> bool:
    """Check if Open-Meteo weather API is allowed."""
    settings = get_qsettings()
    return settings.value(SERVICE_OPENMETEO_KEY, False, type=bool)


def is_openrouter_allowed() -> bool:
    """Check if OpenRouter API is allowed."""
    settings = get_qsettings()
    return settings.value(SERVICE_OPENROUTER_KEY, True, type=bool)


def is_openai_allowed() -> bool:
    """Check if OpenAI API is allowed."""
    settings = get_qsettings()
    return settings.value(SERVICE_OPENAI_KEY, True, type=bool)
