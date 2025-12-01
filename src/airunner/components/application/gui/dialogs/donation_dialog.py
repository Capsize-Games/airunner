"""Donation dialog for AI Runner.

Shows a banner encouraging users to donate via cryptocurrency after application startup.
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QCheckBox,
    QWidget,
    QApplication,
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QFont, QClipboard

from airunner.settings import AIRUNNER_DONATION_WALLET


class DonationDialog(QDialog):
    """Dialog encouraging users to donate to support AI Runner development."""

    SETTINGS_KEY = "donation_dialog_dismissed"
    SETTINGS_DONT_SHOW_KEY = "donation_dialog_dont_show"

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the donation dialog.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Support AI Runner Development")
        self.setMinimumSize(550, 400)
        self.setMaximumSize(650, 500)
        self.setModal(True)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Heart emoji header
        header = QLabel("❤️ Support Open Source AI ❤️")
        header_font = QFont()
        header_font.setPointSize(18)
        header_font.setBold(True)
        header.setFont(header_font)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Main message
        message = QLabel(
            "AI Runner is free, open-source software developed with passion "
            "and dedication to bringing powerful AI tools to everyone.\n\n"
            "Building and maintaining this project requires countless hours of work, "
            "expensive GPU hardware for testing, and ongoing costs for infrastructure. "
            "Your donation—no matter the size—helps keep this project alive and growing.\n\n"
            "If AI Runner has been useful to you, please consider making a contribution. "
            "Every donation directly supports new features, bug fixes, and keeping AI "
            "accessible to all."
        )
        message.setWordWrap(True)
        message.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(message)

        # Wallet section
        wallet_label = QLabel("Bitcoin (BTC) Donation Address:")
        wallet_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        wallet_font = QFont()
        wallet_font.setBold(True)
        wallet_label.setFont(wallet_font)
        layout.addWidget(wallet_label)

        # Wallet address with copy button
        wallet_row = QHBoxLayout()
        wallet_row.addStretch()

        self._wallet_address = QLabel(AIRUNNER_DONATION_WALLET)
        self._wallet_address.setStyleSheet(
            "background-color: #2d2d2d; "
            "color: #f0a500; "
            "padding: 10px 15px; "
            "border-radius: 5px; "
            "font-family: monospace; "
            "font-size: 11px;"
        )
        self._wallet_address.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        wallet_row.addWidget(self._wallet_address)

        copy_button = QPushButton("📋 Copy")
        copy_button.setFixedWidth(80)
        copy_button.clicked.connect(self._copy_wallet_address)
        wallet_row.addWidget(copy_button)

        wallet_row.addStretch()
        layout.addLayout(wallet_row)

        # Copy confirmation label (hidden initially)
        self._copy_confirm = QLabel("✓ Copied to clipboard!")
        self._copy_confirm.setStyleSheet("color: #4CAF50;")
        self._copy_confirm.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._copy_confirm.hide()
        layout.addWidget(self._copy_confirm)

        # Thank you note
        thanks = QLabel("Thank you for supporting open-source AI! 🙏")
        thanks.setAlignment(Qt.AlignmentFlag.AlignLeft)
        thanks_font = QFont()
        thanks_font.setItalic(True)
        thanks.setFont(thanks_font)
        layout.addWidget(thanks)

        layout.addStretch()

        # Don't show again checkbox
        self._dont_show_checkbox = QCheckBox("Don't show this again")
        layout.addWidget(self._dont_show_checkbox)

        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_button = QPushButton("Close")
        close_button.setDefault(True)
        close_button.clicked.connect(self._on_close)
        close_button.setMinimumWidth(100)
        button_layout.addWidget(close_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

    def _copy_wallet_address(self) -> None:
        """Copy the wallet address to clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(AIRUNNER_DONATION_WALLET)
        self._copy_confirm.show()

    def _on_close(self) -> None:
        """Handle close button click."""
        if self._dont_show_checkbox.isChecked():
            settings = QSettings("Capsize LLC", "AI Runner")
            settings.setValue(self.SETTINGS_DONT_SHOW_KEY, True)
            settings.sync()
        self.accept()

    @classmethod
    def should_show(cls) -> bool:
        """Check if the donation dialog should be shown.

        Returns:
            True if dialog should be shown, False if user opted out.
        """
        settings = QSettings("Capsize LLC", "AI Runner")
        dont_show = settings.value(cls.SETTINGS_DONT_SHOW_KEY, False, type=bool)
        return not dont_show

    @classmethod
    def show_if_appropriate(cls, parent: QWidget | None = None) -> None:
        """Show the donation dialog if the user hasn't opted out.

        Args:
            parent: Optional parent widget for the dialog.
        """
        if cls.should_show():
            dialog = cls(parent)
            dialog.exec()
