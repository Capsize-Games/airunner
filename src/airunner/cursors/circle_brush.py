from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPen,
    QBrush,
    QPixmap,
    QCursor
)


def circle_cursor(outline_color, fill_color, pixmap_size=32):
    pixmap_size = int(pixmap_size)
    # create a pixmap with the desired size for the cursor shape
    pixmap = QPixmap(pixmap_size, pixmap_size)
    pixmap.fill(Qt.GlobalColor.transparent)  # make the background of the pixmap transparent

    # draw a circle in the pixmap
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)  # make the edges of the circle smoother
    pen = QPen(QColor(outline_color))
    pen.setWidth(2)
    brush = QBrush(QColor(fill_color))
    painter.setPen(pen)
    painter.setBrush(brush)
    painter.drawEllipse(1, 1, pixmap_size - 2, pixmap_size - 2)

    # draw an inner circle in the pixmap
    pen = QPen(QColor(Qt.GlobalColor.black))
    pen.setWidth(2)
    brush = QBrush(QColor(fill_color))
    painter.setPen(pen)
    painter.setBrush(brush)
    painter.drawEllipse(2, 2, pixmap_size - 4, pixmap_size - 4)

    painter.end()

    # create a cursor from the pixmap
    return QCursor(pixmap, pixmap_size // 2, pixmap_size // 2)
