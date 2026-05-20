"""Compact attachment pill widget for chat prompt attachments."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)


class ChatAttachmentPillWidget(QFrame):
    """Display one compact removable chat attachment pill."""

    removed = Signal()

    def __init__(
        self,
        label: str,
        *,
        tooltip: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._label_text = str(label or "Attachment").strip()
        self._tooltip = tooltip or self._label_text
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName("chatAttachmentPill")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setToolTip(self._tooltip)
        self.setFixedHeight(28)
        self.setSizePolicy(
            QSizePolicy.Policy.Maximum,
            QSizePolicy.Policy.Fixed,
        )
        self.setStyleSheet(
            """
            QFrame#chatAttachmentPill {
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 14px;
                background-color: rgba(255, 255, 255, 0.05);
            }
            QPushButton#chatAttachmentRemoveButton {
                border: none;
                background: transparent;
                color: #d0d0d0;
                font-size: 14px;
                font-weight: bold;
                padding: 0;
            }
            QPushButton#chatAttachmentRemoveButton:hover {
                color: #ffffff;
            }
            QLabel#chatAttachmentLabel {
                color: #d9d9d9;
            }
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 10, 2)
        layout.setSpacing(6)

        remove_button = QPushButton("×", self)
        remove_button.setObjectName("chatAttachmentRemoveButton")
        remove_button.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_button.setFixedSize(16, 16)
        remove_button.setToolTip("Remove attachment")
        remove_button.clicked.connect(self._on_remove_clicked)
        layout.addWidget(remove_button)

        label = QLabel(self._label_text, self)
        label.setObjectName("chatAttachmentLabel")
        label.setToolTip(self._tooltip)
        label.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        layout.addWidget(label)

    def _on_remove_clicked(self) -> None:
        """Emit the remove signal for the owning chat widget."""
        self.removed.emit()