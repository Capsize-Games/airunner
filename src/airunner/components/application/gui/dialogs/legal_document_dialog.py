"""Legal document dialog for displaying Terms of Service, Privacy Policy, and Age Agreement."""

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTextEdit,
    QPushButton,
    QHBoxLayout,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


# Document directory path
AGREEMENTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "downloader"
    / "gui"
    / "windows"
    / "setup_wizard"
    / "user_agreement"
)


class LegalDocumentDialog(QDialog):
    """Dialog for displaying legal documents (Terms of Service, Privacy Policy, Age Agreement)."""
    
    # Map document types to filenames and fallback error messages
    DOCUMENT_MAP = {
        "terms": {
            "filename": "user_agreement_text.md",
            "error": "# Terms of Service\n\n**Error:** Could not load Terms of Service document.\n\nPlease reinstall the application or contact support.",
        },
        "privacy": {
            "filename": "privacy_policy.md",
            "error": "# Privacy Policy\n\n**Error:** Could not load Privacy Policy document.\n\nPlease reinstall the application or contact support.",
        },
        "age": {
            "filename": "age_agreement.md",
            "error": "# Age Agreement\n\n**Error:** Could not load Age Agreement document.\n\nPlease reinstall the application or contact support.",
        },
    }
    
    def __init__(self, parent=None, title: str = "Legal Document", document_type: str = "terms"):
        """
        Initialize the legal document dialog.
        
        Args:
            parent: Parent widget
            title: Dialog window title
            document_type: "terms", "privacy", or "age"
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumSize(700, 600)
        
        self._document_type = document_type
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Document text
        document_text = self._load_document()
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setMarkdown(document_text)
        text_edit.setMinimumHeight(450)
        layout.addWidget(text_edit)
        
        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        close_button.setDefault(True)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
    
    def _load_document(self) -> str:
        """Load the appropriate document based on type.
        
        Returns:
            The document content as a string.
        """
        doc_info = self.DOCUMENT_MAP.get(self._document_type)
        if not doc_info:
            return f"# Error\n\nUnknown document type: {self._document_type}"
        
        doc_path = AGREEMENTS_DIR / doc_info["filename"]
        
        try:
            if doc_path.exists():
                content = doc_path.read_text(encoding="utf-8")
                if content.strip():
                    return content
        except Exception as e:
            return f"# Error\n\n**Error loading document:** {e}\n\nPlease reinstall the application or contact support."
        
        return doc_info["error"]
