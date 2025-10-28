"""Service Settings Widget for background service and API server configuration.

Provides UI for:
- Run in Background toggle
- Start at Login toggle (platform-specific)
- HTTP server enable/disable
- HTTP server host and port configuration
- LNA (Local Network Access) toggle for CORS
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QCheckBox,
    QLabel,
    QLineEdit,
    QSpinBox,
    QFormLayout,
    QPushButton,
    QMessageBox,
)
from PySide6.QtCore import Signal, Slot
import platform


class ServiceSettingsWidget(QWidget):
    """Widget for configuring background services and API server.

    Features:
    - Run in background toggle
    - Start at login toggle (platform-aware)
    - HTTP server configuration
    - LNA/CORS settings
    - Settings validation and apply/reset buttons
    """

    # Signals
    settings_changed = Signal(dict)  # Emits dict of changed settings

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize service settings widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._initial_values = {}
        self._setup_ui()

    def _setup_ui(self):
        """Set up the widget UI."""
        layout = QVBoxLayout(self)

        # Service Settings Group
        service_group = QGroupBox("Service Settings")
        service_layout = QVBoxLayout()

        # Run in Background
        self.run_background_cb = QCheckBox("Run in Background")
        self.run_background_cb.setToolTip(
            "Keep AI Runner running in background when window is closed"
        )
        service_layout.addWidget(self.run_background_cb)

        # Start at Login
        self.start_login_cb = QCheckBox("Start at Login")
        self.start_login_cb.setToolTip(
            "Automatically start AI Runner when you log in"
        )

        # Disable on unsupported platforms
        current_platform = platform.system()
        if current_platform not in ["Linux", "Windows", "Darwin"]:
            self.start_login_cb.setEnabled(False)
            self.start_login_cb.setToolTip(
                f"Start at login not supported on {current_platform}"
            )

        service_layout.addWidget(self.start_login_cb)

        service_group.setLayout(service_layout)
        layout.addWidget(service_group)

        # HTTP Server Settings Group
        server_group = QGroupBox("HTTP Server Settings")
        server_layout = QFormLayout()

        # Enable/Disable Server
        self.server_enabled_cb = QCheckBox("Enable HTTP Server")
        self.server_enabled_cb.setToolTip(
            "Enable local HTTP server for static assets and API endpoints"
        )
        self.server_enabled_cb.toggled.connect(self._on_server_enabled_changed)
        server_layout.addRow("", self.server_enabled_cb)

        # Host
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("127.0.0.1")
        self.host_input.setToolTip(
            "Host address for HTTP server (use 0.0.0.0 to allow external access)"
        )
        server_layout.addRow("Host:", self.host_input)

        # Port
        self.port_input = QSpinBox()
        self.port_input.setMinimum(1024)
        self.port_input.setMaximum(65535)
        self.port_input.setValue(5005)
        self.port_input.setToolTip("Port for HTTP server")
        server_layout.addRow("Port:", self.port_input)

        # LNA Enabled
        self.lna_enabled_cb = QCheckBox("Enable LNA/CORS")
        self.lna_enabled_cb.setToolTip(
            "Enable Local Network Access headers and permissive CORS "
            "(required for external network access)"
        )
        server_layout.addRow("", self.lna_enabled_cb)

        server_group.setLayout(server_layout)
        layout.addWidget(server_group)

        # Info Label
        info_label = QLabel(
            "<i>Note: Changing server settings requires restarting "
            "the application to take effect.</i>"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Action Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.reset_button = QPushButton("Reset")
        self.reset_button.setToolTip("Reset to last saved values")
        self.reset_button.clicked.connect(self._on_reset)
        button_layout.addWidget(self.reset_button)

        self.apply_button = QPushButton("Apply")
        self.apply_button.setToolTip("Apply and save settings")
        self.apply_button.clicked.connect(self._on_apply)
        button_layout.addWidget(self.apply_button)

        layout.addLayout(button_layout)
        layout.addStretch()

    @Slot(bool)
    def _on_server_enabled_changed(self, enabled: bool):
        """Handle server enabled checkbox state change.

        Args:
            enabled: Whether server is enabled
        """
        self.host_input.setEnabled(enabled)
        self.port_input.setEnabled(enabled)
        self.lna_enabled_cb.setEnabled(enabled)

    @Slot()
    def _on_reset(self):
        """Reset all settings to initial values."""
        if self._initial_values:
            self.set_settings(self._initial_values)

    @Slot()
    def _on_apply(self):
        """Apply and emit settings changes."""
        # Validate settings
        host = self.host_input.text().strip()
        if not host:
            QMessageBox.warning(
                self,
                "Invalid Settings",
                "Host address cannot be empty. Using default: 127.0.0.1",
            )
            self.host_input.setText("127.0.0.1")
            host = "127.0.0.1"

        # Gather settings
        settings = self.get_settings()

        # Check if server settings changed before updating initial values
        server_settings_changed = (
            settings.get("http_server_enabled")
            != self._initial_values.get("http_server_enabled")
            or settings.get("http_server_host")
            != self._initial_values.get("http_server_host")
            or settings.get("http_server_port")
            != self._initial_values.get("http_server_port")
        )

        # Emit signal
        self.settings_changed.emit(settings)

        # Update initial values
        self._initial_values = settings.copy()

        # Show confirmation if server settings changed
        if server_settings_changed:
            QMessageBox.information(
                self,
                "Settings Applied",
                "Server settings will take effect after restarting the application.",
            )

    def get_settings(self) -> dict:
        """Get current settings as dictionary.

        Returns:
            Dictionary with current settings values
        """
        return {
            "run_in_background": self.run_background_cb.isChecked(),
            "start_at_login": self.start_login_cb.isChecked(),
            "http_server_enabled": self.server_enabled_cb.isChecked(),
            "http_server_host": self.host_input.text().strip(),
            "http_server_port": self.port_input.value(),
            "lna_enabled": self.lna_enabled_cb.isChecked(),
        }

    def set_settings(self, settings: dict):
        """Set settings from dictionary.

        Args:
            settings: Dictionary with settings values
        """
        # Store initial values if not already set
        if not self._initial_values:
            self._initial_values = settings.copy()

        # Update UI
        self.run_background_cb.setChecked(
            settings.get("run_in_background", False)
        )
        self.start_login_cb.setChecked(settings.get("start_at_login", False))
        self.server_enabled_cb.setChecked(
            settings.get("http_server_enabled", True)
        )
        self.host_input.setText(settings.get("http_server_host", "127.0.0.1"))
        self.port_input.setValue(settings.get("http_server_port", 5005))
        self.lna_enabled_cb.setChecked(settings.get("lna_enabled", False))
