from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QPixmap, QCursor


def circle_cursor(
    outline_color,
    fill_color,
    pixmap_size=32,
    *,
    pixmap_factory=QPixmap,
    painter_factory=QPainter,
    cursor_factory=QCursor
):
    """Create a custom circle cursor with dependency injection for testability.

    Args:
        outline_color: Color for the circle outline.
        fill_color: Color for the circle fill.
        pixmap_size: Size of the cursor pixmap.
        pixmap_factory: Factory for QPixmap (for testing).
        painter_factory: Factory for QPainter (for testing).
        cursor_factory: Factory for QCursor (for testing).
    Returns:
        QCursor: The created cursor.
    """
    pixmap_size = int(pixmap_size)
    pixmap = pixmap_factory(pixmap_size, pixmap_size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = painter_factory(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(outline_color))
    pen.setWidth(2)
    brush = QBrush(QColor(fill_color))
    painter.setPen(pen)
    painter.setBrush(brush)
    painter.drawEllipse(1, 1, pixmap_size - 2, pixmap_size - 2)
    pen = QPen(QColor(Qt.GlobalColor.black))
    pen.setWidth(2)
    brush = QBrush(QColor(fill_color))
    painter.setPen(pen)
    painter.setBrush(brush)
    painter.drawEllipse(2, 2, pixmap_size - 4, pixmap_size - 4)
    painter.end()
    return cursor_factory(pixmap, pixmap_size // 2, pixmap_size // 2)
