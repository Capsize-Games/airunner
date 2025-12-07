"""Image attachment thumbnail widget for chat.

This widget displays a small thumbnail preview of an attached image
with an X button to remove it, similar to VS Code's chat attachments.
"""

from typing import Optional

from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QSizePolicy,
)


class ImageAttachmentWidget(QFrame):
    """Thumbnail widget for attached images with remove button.

    Displays a small preview of an attached PIL Image with a clickable
    X button to remove it from the attachments list.

    Signals:
        removed: Emitted when the user clicks the remove button.
    """

    removed = Signal()

    # Thumbnail size in pixels
    THUMBNAIL_SIZE = 64

    def __init__(
        self,
        image: Image.Image,
        image_path: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the attachment widget.

        Args:
            image: PIL Image to display as thumbnail.
            image_path: Optional path to the image file (for tooltip).
            parent: Parent widget.
        """
        super().__init__(parent)
        self._image = image
        self._image_path = image_path

        self._setup_ui()

    @property
    def image(self) -> Image.Image:
        """Get the attached PIL Image."""
        return self._image

    @property
    def image_path(self) -> Optional[str]:
        """Get the path to the attached image file, if any."""
        return self._image_path

    def _setup_ui(self) -> None:
        """Set up the widget UI."""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setObjectName("imageAttachmentWidget")

        # Compact layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Thumbnail label
        self._thumbnail_label = QLabel()
        self._thumbnail_label.setFixedSize(
            self.THUMBNAIL_SIZE, self.THUMBNAIL_SIZE
        )
        self._thumbnail_label.setScaledContents(False)
        self._thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._set_thumbnail()

        # Set tooltip with image info
        if self._image_path:
            tooltip = f"{self._image_path}\n{self._image.width}x{self._image.height}"
        else:
            tooltip = f"Image: {self._image.width}x{self._image.height}"
        self._thumbnail_label.setToolTip(tooltip)

        layout.addWidget(self._thumbnail_label)

        # Remove button (X)
        self._remove_button = QPushButton("×")
        self._remove_button.setObjectName("attachmentRemoveButton")
        self._remove_button.setFixedSize(20, 20)
        self._remove_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._remove_button.setToolTip("Remove attachment")
        self._remove_button.clicked.connect(self._on_remove_clicked)

        # Style the remove button
        self._remove_button.setStyleSheet(
            """
            QPushButton#attachmentRemoveButton {
                background-color: rgba(255, 255, 255, 0.1);
                border: none;
                border-radius: 10px;
                color: #aaa;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#attachmentRemoveButton:hover {
                background-color: rgba(255, 0, 0, 0.3);
                color: #fff;
            }
            """
        )

        layout.addWidget(
            self._remove_button, alignment=Qt.AlignmentFlag.AlignTop
        )

        # Set fixed height for the widget
        self.setFixedHeight(self.THUMBNAIL_SIZE + 8)
        self.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )

    def _set_thumbnail(self) -> None:
        """Create and set the thumbnail from the PIL Image."""
        try:
            # Create a copy and make thumbnail
            thumb = self._image.copy()
            thumb.thumbnail(
                (self.THUMBNAIL_SIZE, self.THUMBNAIL_SIZE),
                Image.Resampling.LANCZOS,
            )

            # Convert to RGBA if needed for Qt
            if thumb.mode != "RGBA":
                thumb = thumb.convert("RGBA")

            # Convert to QPixmap
            qimage = ImageQt(thumb)
            pixmap = QPixmap.fromImage(qimage)

            self._thumbnail_label.setPixmap(pixmap)
        except Exception as e:
            # Fallback to placeholder on error
            self._thumbnail_label.setText("🖼")
            self._thumbnail_label.setStyleSheet("font-size: 24px;")

    def _on_remove_clicked(self) -> None:
        """Handle remove button click."""
        self.removed.emit()
