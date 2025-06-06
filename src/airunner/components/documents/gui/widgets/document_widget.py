from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QCheckBox,
    QPushButton,
)
from PySide6.QtCore import Qt, Signal


class DocumentWidget(QWidget):
    delete_requested = Signal(object)  # emits the document object

    def __init__(self, document, on_active_changed=None, parent=None):
        super().__init__(parent)
        self.document = document
        self.on_active_changed = on_active_changed
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self.document.active)
        self.checkbox.stateChanged.connect(self.handle_checkbox)
        layout.addWidget(self.checkbox)

        vbox = QVBoxLayout()
        self.title_label = QLabel(self.document_title())
        self.summary_label = QLabel(self.document_summary())
        self.summary_label.setWordWrap(True)
        vbox.addWidget(self.title_label)
        vbox.addWidget(self.summary_label)
        layout.addLayout(vbox)

        self.delete_button = QPushButton("🗑")
        self.delete_button.setToolTip("Delete document")
        self.delete_button.setFixedWidth(28)
        self.delete_button.clicked.connect(self.handle_delete)
        layout.addWidget(self.delete_button)

        self.setLayout(layout)

    def document_title(self):
        # Use filename as title
        import os

        return os.path.basename(self.document.path)

    def document_summary(self):
        # Try to read first 2 lines as summary
        try:
            with open(self.document.path, "r", encoding="utf-8") as f:
                lines = [next(f).strip() for _ in range(2)]
            return " ".join(lines)
        except Exception:
            return "(No preview available)"

    def handle_checkbox(self, state):
        if self.on_active_changed:
            self.on_active_changed(self.document, state == Qt.Checked)

    def handle_delete(self):
        self.delete_requested.emit(self.document)
