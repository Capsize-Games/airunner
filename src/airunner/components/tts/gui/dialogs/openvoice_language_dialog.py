"""Dialog for selecting OpenVoice languages to download."""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QPushButton,
    QGroupBox,
    QScrollArea,
    QWidget,
    QSizePolicy,
)
from PySide6.QtCore import Qt

from airunner.components.tts.data.bootstrap.openvoice_languages import (
    OPENVOICE_LANGUAGE_MODELS,
)


class OpenVoiceLanguageDialog(QDialog):
    """Dialog for selecting which OpenVoice languages to download."""

    def __init__(self, parent=None, missing_languages: list = None):
        """Initialize the language selection dialog.
        
        Args:
            parent: Parent widget
            missing_languages: List of language keys that need to be downloaded.
                              If None, all languages are shown.
        """
        super().__init__(parent)
        self.setWindowTitle("OpenVoice Language Selection")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        self._selected_languages = []
        self._checkboxes = {}
        
        # Filter to only show missing languages if provided
        self._available_languages = missing_languages or list(OPENVOICE_LANGUAGE_MODELS.keys())
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel(
            "<b>OpenVoice TTS requires model downloads.</b><br><br>"
            "English (core) models will always be downloaded.<br>"
            "Select additional languages you want to use:"
        )
        header_label.setWordWrap(True)
        layout.addWidget(header_label)
        
        # Language selection group
        lang_group = QGroupBox("Additional Languages")
        lang_layout = QVBoxLayout(lang_group)
        
        # Create checkboxes for each available language
        for lang_key in self._available_languages:
            lang_info = OPENVOICE_LANGUAGE_MODELS.get(lang_key, {})
            display_name = lang_info.get("display_name", lang_key)
            
            checkbox = QCheckBox(display_name)
            checkbox.setChecked(False)  # Default unchecked
            self._checkboxes[lang_key] = checkbox
            lang_layout.addWidget(checkbox)
        
        if not self._available_languages:
            no_lang_label = QLabel("No additional languages need to be downloaded.")
            lang_layout.addWidget(no_lang_label)
        
        layout.addWidget(lang_group)
        
        # Info label
        info_label = QLabel(
            "<i>You can download additional languages later from Settings.</i>"
        )
        info_label.setStyleSheet("color: gray;")
        layout.addWidget(info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self._download_btn = QPushButton("Download Selected")
        self._download_btn.clicked.connect(self._on_download_clicked)
        self._download_btn.setDefault(True)
        
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self._cancel_btn)
        button_layout.addWidget(self._download_btn)
        
        layout.addLayout(button_layout)
    
    def _on_download_clicked(self):
        """Handle download button click."""
        self._selected_languages = [
            lang_key 
            for lang_key, checkbox in self._checkboxes.items() 
            if checkbox.isChecked()
        ]
        self.accept()
    
    def get_selected_languages(self) -> list:
        """Get the list of selected language keys.
        
        Returns:
            List of selected language keys (e.g., ["French", "Spanish"])
        """
        return self._selected_languages
