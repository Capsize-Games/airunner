"""
Fara Settings Widget.

GUI widget for configuring Fara-7B computer use agent settings.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QSpinBox,
    QDoubleSpinBox,
    QLineEdit,
    QGroupBox,
    QFormLayout,
    QPushButton,
    QComboBox,
)
from PySide6.QtCore import Signal, Slot

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


# Default Fara model
DEFAULT_FARA_MODEL = "microsoft/Fara-7B"


class FaraSettingsWidget(QWidget):
    """
    Widget for configuring Fara-7B computer use agent.

    Provides settings for:
    - Enable/disable Fara
    - Model path and quantization
    - Screen resolution
    - Safety settings
    - Integration options
    """

    # Signals
    settings_changed = Signal()
    fara_enabled_changed = Signal(bool)

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the Fara settings widget."""
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Set up the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # Header
        header = QLabel("<h2>🤖 Fara Computer Use Agent</h2>")
        layout.addWidget(header)

        description = QLabel(
            "Fara-7B is Microsoft's agentic model for computer use. "
            "It can automate web tasks like shopping, booking, and form filling "
            "by taking screenshots and predicting mouse/keyboard actions."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        # Enable/Disable
        self._enable_group = self._create_enable_group()
        layout.addWidget(self._enable_group)

        # Model Settings
        self._model_group = self._create_model_group()
        layout.addWidget(self._model_group)

        # Screen Settings
        self._screen_group = self._create_screen_group()
        layout.addWidget(self._screen_group)

        # Safety Settings
        self._safety_group = self._create_safety_group()
        layout.addWidget(self._safety_group)

        # Integration Settings
        self._integration_group = self._create_integration_group()
        layout.addWidget(self._integration_group)

        # Spacer
        layout.addStretch()

    def _create_enable_group(self) -> QGroupBox:
        """Create the enable/disable group."""
        group = QGroupBox("Enable Fara")
        layout = QVBoxLayout(group)

        self.enable_checkbox = QCheckBox("Enable Fara-7B for computer use tasks")
        self.enable_checkbox.setToolTip(
            "When enabled, Fara can be used for automated web tasks"
        )
        layout.addWidget(self.enable_checkbox)

        warning = QLabel(
            "⚠️ <i>Fara will perform actions on your computer. "
            "Always review tasks before execution.</i>"
        )
        warning.setWordWrap(True)
        layout.addWidget(warning)

        return group

    def _create_model_group(self) -> QGroupBox:
        """Create the model settings group."""
        group = QGroupBox("Model Settings")
        layout = QFormLayout(group)

        # Model path
        self.model_path_edit = QLineEdit(DEFAULT_FARA_MODEL)
        self.model_path_edit.setPlaceholderText("Model path or HuggingFace ID")
        layout.addRow("Model:", self.model_path_edit)

        # Quantization
        quant_layout = QHBoxLayout()
        self.quantization_checkbox = QCheckBox("Use quantization")
        self.quantization_checkbox.setChecked(True)
        quant_layout.addWidget(self.quantization_checkbox)

        self.quantization_bits = QComboBox()
        self.quantization_bits.addItems(["4-bit", "8-bit"])
        self.quantization_bits.setCurrentIndex(0)
        quant_layout.addWidget(self.quantization_bits)
        quant_layout.addStretch()

        layout.addRow("Quantization:", quant_layout)

        # Download button
        self.download_button = QPushButton("Download Model")
        self.download_button.setToolTip("Download Fara-7B from HuggingFace")
        layout.addRow("", self.download_button)

        return group

    def _create_screen_group(self) -> QGroupBox:
        """Create the screen settings group."""
        group = QGroupBox("Screen Settings")
        layout = QFormLayout(group)

        # Auto-detect
        self.auto_detect_checkbox = QCheckBox("Auto-detect screen resolution")
        self.auto_detect_checkbox.setChecked(True)
        layout.addRow("", self.auto_detect_checkbox)

        # Manual resolution
        res_layout = QHBoxLayout()
        self.screen_width = QSpinBox()
        self.screen_width.setRange(800, 7680)
        self.screen_width.setValue(1428)
        res_layout.addWidget(self.screen_width)

        res_layout.addWidget(QLabel("x"))

        self.screen_height = QSpinBox()
        self.screen_height.setRange(600, 4320)
        self.screen_height.setValue(896)
        res_layout.addWidget(self.screen_height)
        res_layout.addStretch()

        layout.addRow("Resolution:", res_layout)

        return group

    def _create_safety_group(self) -> QGroupBox:
        """Create the safety settings group."""
        group = QGroupBox("Safety Settings")
        layout = QFormLayout(group)

        # Max steps
        self.max_steps = QSpinBox()
        self.max_steps.setRange(1, 200)
        self.max_steps.setValue(50)
        self.max_steps.setToolTip("Maximum actions before forced termination")
        layout.addRow("Max Steps:", self.max_steps)

        # Step delay
        self.step_delay = QDoubleSpinBox()
        self.step_delay.setRange(0.1, 5.0)
        self.step_delay.setValue(0.5)
        self.step_delay.setSingleStep(0.1)
        self.step_delay.setToolTip("Delay between actions in seconds")
        layout.addRow("Step Delay (s):", self.step_delay)

        # Critical points
        self.critical_points_checkbox = QCheckBox(
            "Stop at critical points (checkout, payment, login)"
        )
        self.critical_points_checkbox.setChecked(True)
        layout.addRow("", self.critical_points_checkbox)

        # Require confirmation
        self.require_confirmation_checkbox = QCheckBox(
            "Require confirmation before executing tasks"
        )
        self.require_confirmation_checkbox.setChecked(True)
        layout.addRow("", self.require_confirmation_checkbox)

        return group

    def _create_integration_group(self) -> QGroupBox:
        """Create the integration settings group."""
        group = QGroupBox("Integration")
        layout = QVBoxLayout(group)

        self.use_for_tools_checkbox = QCheckBox(
            "Use Fara for all tool execution"
        )
        self.use_for_tools_checkbox.setToolTip(
            "When enabled, Fara handles all tool calls from the dialogue LLM"
        )
        layout.addWidget(self.use_for_tools_checkbox)

        self.use_for_web_search_checkbox = QCheckBox(
            "Use Fara for web searches"
        )
        self.use_for_web_search_checkbox.setChecked(True)
        layout.addWidget(self.use_for_web_search_checkbox)

        self.use_for_automation_checkbox = QCheckBox(
            "Use Fara for browser automation"
        )
        self.use_for_automation_checkbox.setChecked(True)
        layout.addWidget(self.use_for_automation_checkbox)

        # Backend selection
        backend_layout = QHBoxLayout()
        backend_layout.addWidget(QLabel("Automation backend:"))
        self.backend_combo = QComboBox()
        self.backend_combo.addItems(["PyAutoGUI (Desktop)", "Playwright (Web)"])
        backend_layout.addWidget(self.backend_combo)
        backend_layout.addStretch()
        layout.addLayout(backend_layout)

        return group

    def _connect_signals(self):
        """Connect internal signals."""
        self.enable_checkbox.toggled.connect(self._on_enable_changed)
        self.auto_detect_checkbox.toggled.connect(self._on_auto_detect_changed)
        self.quantization_checkbox.toggled.connect(self._on_settings_changed)

        # Connect all other widgets to settings_changed
        for widget in [
            self.model_path_edit,
            self.max_steps,
            self.step_delay,
            self.screen_width,
            self.screen_height,
        ]:
            if hasattr(widget, "textChanged"):
                widget.textChanged.connect(self._on_settings_changed)
            elif hasattr(widget, "valueChanged"):
                widget.valueChanged.connect(self._on_settings_changed)

        for checkbox in [
            self.critical_points_checkbox,
            self.require_confirmation_checkbox,
            self.use_for_tools_checkbox,
            self.use_for_web_search_checkbox,
            self.use_for_automation_checkbox,
        ]:
            checkbox.toggled.connect(self._on_settings_changed)

    @Slot(bool)
    def _on_enable_changed(self, enabled: bool):
        """Handle enable checkbox change."""
        # Enable/disable other settings based on main toggle
        self._model_group.setEnabled(enabled)
        self._screen_group.setEnabled(enabled)
        self._safety_group.setEnabled(enabled)
        self._integration_group.setEnabled(enabled)

        self.fara_enabled_changed.emit(enabled)
        self.settings_changed.emit()

    @Slot(bool)
    def _on_auto_detect_changed(self, auto_detect: bool):
        """Handle auto-detect checkbox change."""
        self.screen_width.setEnabled(not auto_detect)
        self.screen_height.setEnabled(not auto_detect)
        self._on_settings_changed()

    @Slot()
    def _on_settings_changed(self):
        """Handle any settings change."""
        self.settings_changed.emit()

    def get_settings(self) -> dict:
        """Get current settings as a dictionary."""
        return {
            "enabled": self.enable_checkbox.isChecked(),
            "model_path": self.model_path_edit.text(),
            "use_quantization": self.quantization_checkbox.isChecked(),
            "quantization_bits": 4 if self.quantization_bits.currentIndex() == 0 else 8,
            "auto_detect_resolution": self.auto_detect_checkbox.isChecked(),
            "screen_width": self.screen_width.value(),
            "screen_height": self.screen_height.value(),
            "max_steps": self.max_steps.value(),
            "step_delay": self.step_delay.value(),
            "enable_critical_points": self.critical_points_checkbox.isChecked(),
            "require_confirmation": self.require_confirmation_checkbox.isChecked(),
            "use_for_all_tools": self.use_for_tools_checkbox.isChecked(),
            "use_for_web_search": self.use_for_web_search_checkbox.isChecked(),
            "use_for_browser_automation": self.use_for_automation_checkbox.isChecked(),
            "use_pyautogui": self.backend_combo.currentIndex() == 0,
            "use_playwright": self.backend_combo.currentIndex() == 1,
        }

    def set_settings(self, settings: dict):
        """Set settings from a dictionary."""
        self.enable_checkbox.setChecked(settings.get("enabled", False))
        self.model_path_edit.setText(settings.get("model_path", DEFAULT_FARA_MODEL))
        self.quantization_checkbox.setChecked(settings.get("use_quantization", True))

        bits = settings.get("quantization_bits", 4)
        self.quantization_bits.setCurrentIndex(0 if bits == 4 else 1)

        self.auto_detect_checkbox.setChecked(
            settings.get("auto_detect_resolution", True)
        )
        self.screen_width.setValue(settings.get("screen_width", 1428))
        self.screen_height.setValue(settings.get("screen_height", 896))
        self.max_steps.setValue(settings.get("max_steps", 50))
        self.step_delay.setValue(settings.get("step_delay", 0.5))
        self.critical_points_checkbox.setChecked(
            settings.get("enable_critical_points", True)
        )
        self.require_confirmation_checkbox.setChecked(
            settings.get("require_confirmation", True)
        )
        self.use_for_tools_checkbox.setChecked(
            settings.get("use_for_all_tools", False)
        )
        self.use_for_web_search_checkbox.setChecked(
            settings.get("use_for_web_search", True)
        )
        self.use_for_automation_checkbox.setChecked(
            settings.get("use_for_browser_automation", True)
        )

        if settings.get("use_playwright", False):
            self.backend_combo.setCurrentIndex(1)
        else:
            self.backend_combo.setCurrentIndex(0)
