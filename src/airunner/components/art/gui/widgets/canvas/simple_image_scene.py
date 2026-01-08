"""Simple image scene for displaying preview images.

This is a lightweight scene specifically for input image previews.
It does NOT inherit from the complex BrushScene hierarchy - it's
just a simple QGraphicsScene that displays a single image.
"""

from typing import Optional
from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QGraphicsScene, QGraphicsPixmapItem
from PySide6.QtGui import QPixmap


class SimpleImageScene(QGraphicsScene):
    """A simple scene for displaying a single preview image.
    
    This scene is designed to be simple and reliable:
    - No complex inheritance
    - No deferred updates
    - No position persistence
    - Just displays an image at (0, 0)
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._current_image: Optional[Image.Image] = None
    
    def set_image(self, pil_image: Optional[Image.Image]) -> None:
        """Set the image to display.
        
        Args:
            pil_image: PIL Image to display, or None to clear.
        """
        # Store reference
        self._current_image = pil_image
        
        # Clear any existing item
        if self._pixmap_item is not None:
            self.removeItem(self._pixmap_item)
            self._pixmap_item = None
        
        if pil_image is None:
            self.setSceneRect(QRectF())
            return
        
        # Convert PIL image to QPixmap
        # Ensure RGBA mode for consistent display
        if pil_image.mode != 'RGBA':
            pil_image = pil_image.convert('RGBA')
        
        # Convert to QImage then QPixmap
        qimage = ImageQt(pil_image)
        pixmap = QPixmap.fromImage(QImage(qimage))
        
        # Create pixmap item and add to scene
        self._pixmap_item = QGraphicsPixmapItem(pixmap)
        self._pixmap_item.setPos(0, 0)
        self.addItem(self._pixmap_item)
        
        # Set scene rect to match image
        self.setSceneRect(0, 0, pixmap.width(), pixmap.height())
    
    def get_image(self) -> Optional[Image.Image]:
        """Get the current PIL image.
        
        Returns:
            The current PIL image or None.
        """
        return self._current_image
    
    def clear_image(self) -> None:
        """Clear the current image."""
        self.set_image(None)
    
    def has_image(self) -> bool:
        """Check if scene has an image.
        
        Returns:
            True if scene has an image displayed.
        """
        return self._pixmap_item is not None
