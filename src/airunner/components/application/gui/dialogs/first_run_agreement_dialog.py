"""First-run agreement dialogs for AI Runner.

Shows Age Agreement, Privacy Policy, and Terms of Service on first application launch.
User must accept all three to proceed.
"""

from pathlib import Path
from typing import ClassVar

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QCheckBox,
    QPushButton,
    QWidget,
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QFont

from airunner.settings import AIRUNNER_VERSION


# Document directory path
AGREEMENTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "downloader"
    / "gui"
    / "windows"
    / "setup_wizard"
    / "user_agreement"
)


class BaseAgreementDialog(QDialog):
    """Base class for agreement dialogs that require user acceptance."""

    SETTINGS_KEY: ClassVar[str] = ""
    SETTINGS_VERSION_KEY: ClassVar[str] = ""
    CURRENT_VERSION: ClassVar[str] = "1.0"
    DIALOG_TITLE: ClassVar[str] = "Agreement"
    HEADER_TEXT: ClassVar[str] = "Please Review"
    INSTRUCTION_TEXT: ClassVar[str] = "Please read and accept."
    CHECKBOX_TEXT: ClassVar[str] = "I accept"
    DOCUMENT_FILENAME: ClassVar[str] = ""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the agreement dialog.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle(self.DIALOG_TITLE)
        self.setMinimumSize(700, 600)
        self.setModal(True)
        self.accepted_terms = False

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        title = QLabel(self.HEADER_TEXT)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Instruction label
        instruction_label = QLabel(self.INSTRUCTION_TEXT)
        instruction_label.setWordWrap(True)
        instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(instruction_label)

        # Document content area
        document_content = self._load_document_content()
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setMarkdown(document_content)
        text_edit.setMinimumHeight(350)
        layout.addWidget(text_edit)

        # Agreement checkbox
        self.accept_checkbox = QCheckBox(self.CHECKBOX_TEXT)
        self.accept_checkbox.stateChanged.connect(self._on_checkbox_changed)
        layout.addWidget(self.accept_checkbox)

        # Button row
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.decline_button = QPushButton("Decline and Exit")
        self.decline_button.clicked.connect(self.reject)
        button_layout.addWidget(self.decline_button)

        self.accept_button = QPushButton("Accept and Continue")
        self.accept_button.setEnabled(False)
        self.accept_button.setDefault(True)
        self.accept_button.clicked.connect(self._on_accept)
        button_layout.addWidget(self.accept_button)

        layout.addLayout(button_layout)

    def _load_document_content(self) -> str:
        """Load document content from the markdown file.

        Returns:
            The document content as a string, or an error message if loading fails.
        """
        doc_path = AGREEMENTS_DIR / self.DOCUMENT_FILENAME

        try:
            if doc_path.exists():
                return doc_path.read_text(encoding="utf-8")
            else:
                return (
                    f"# {self.DIALOG_TITLE}\n\n"
                    "**Error:** Could not load document file.\n\n"
                    f"Expected location: `{doc_path}`\n\n"
                    "Please reinstall the application or contact support."
                )
        except Exception as e:
            return (
                f"# {self.DIALOG_TITLE}\n\n"
                f"**Error loading document:** {e}\n\n"
                "Please reinstall the application or contact support."
            )

    def _on_checkbox_changed(self, state: int) -> None:
        """Handle checkbox state change.

        Args:
            state: The new checkbox state.
        """
        self.accept_button.setEnabled(state == Qt.CheckState.Checked.value)

    def _on_accept(self) -> None:
        """Handle accept button click."""
        self.accepted_terms = True
        self.accept()

    @classmethod
    def check_and_show_if_needed(cls, qsettings: QSettings) -> bool:
        """Check if acceptance is needed and show dialog if so.

        Args:
            qsettings: QSettings instance to check/store acceptance.

        Returns:
            True if user accepted (or already accepted), False if declined.
        """
        # Check if already accepted - use full key path to avoid group conflicts
        full_key = f"legal/{cls.SETTINGS_KEY}"
        full_version_key = f"legal/{cls.SETTINGS_VERSION_KEY}"
        
        accepted = qsettings.value(full_key, False, type=bool)
        accepted_version = qsettings.value(full_version_key, "", type=str)

        # If already accepted current version, no need to show
        if accepted and accepted_version == cls.CURRENT_VERSION:
            return True

        # Show dialog
        dialog = cls()
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted and dialog.accepted_terms:
            # Save acceptance
            qsettings.setValue(full_key, True)
            qsettings.setValue(full_version_key, cls.CURRENT_VERSION)
            qsettings.sync()
            return True

        return False


class AgeAgreementDialog(BaseAgreementDialog):
    """Dialog for age verification agreement."""

    SETTINGS_KEY = "age_accepted"
    SETTINGS_VERSION_KEY = "age_accepted_version"
    CURRENT_VERSION = "1.0"
    DIALOG_TITLE = "Age Verification - AI Runner"
    HEADER_TEXT = "Age Restriction Notice"
    INSTRUCTION_TEXT = (
        "AI Runner may generate mature content. "
        "You must confirm that you meet the age requirements to continue."
    )
    CHECKBOX_TEXT = "I confirm that I am 18 years of age or older"
    DOCUMENT_FILENAME = "age_agreement.md"


class PrivacyPolicyDialog(BaseAgreementDialog):
    """Dialog for privacy policy agreement."""

    SETTINGS_KEY = "privacy_accepted"
    SETTINGS_VERSION_KEY = "privacy_accepted_version"
    CURRENT_VERSION = "1.0"
    DIALOG_TITLE = "Privacy Policy - AI Runner"
    HEADER_TEXT = "Privacy Policy"
    INSTRUCTION_TEXT = (
        "Please review our Privacy Policy to understand how AI Runner "
        "handles your data and protects your privacy."
    )
    CHECKBOX_TEXT = "I have read and accept the Privacy Policy"
    DOCUMENT_FILENAME = "privacy_policy.md"


class TermsOfServiceDialog(BaseAgreementDialog):
    """Dialog for Terms of Service agreement."""

    SETTINGS_KEY = "tos_accepted"
    SETTINGS_VERSION_KEY = "tos_accepted_version"
    CURRENT_VERSION = "1.1"  # Updated with expanded Acceptable Use Policy
    DIALOG_TITLE = "Terms of Service - AI Runner"
    HEADER_TEXT = f"Welcome to AI Runner v{AIRUNNER_VERSION}"
    INSTRUCTION_TEXT = (
        "Before using AI Runner, you must read and accept the Terms of Service below."
    )
    CHECKBOX_TEXT = "I have read and agree to the Terms of Service"
    DOCUMENT_FILENAME = "user_agreement_text.md"


# Backwards compatibility alias
FirstRunAgreementDialog = TermsOfServiceDialog


def check_all_agreements(qsettings: QSettings) -> bool:
    """Check and show all required agreement dialogs.

    Shows Age Agreement, Privacy Policy, and Terms of Service dialogs
    in sequence. All must be accepted to return True.

    Args:
        qsettings: QSettings instance to check/store acceptance.

    Returns:
        True if all agreements were accepted, False if any was declined.
    """
    # Order: Age first (to filter out minors), then Privacy, then TOS
    dialogs = [
        AgeAgreementDialog,
        PrivacyPolicyDialog,
        TermsOfServiceDialog,
    ]

    for dialog_class in dialogs:
        if not dialog_class.check_and_show_if_needed(qsettings):
            return False

    return True
