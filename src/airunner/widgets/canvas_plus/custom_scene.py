from PIL.ImageQt import QImage
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPen, QPixmap, QPainter, QCursor
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsPixmapItem
from PyQt6.QtGui import QPainterPath
from PyQt6.QtGui import QEnterEvent
from PyQt6.QtGui import QTransform

from airunner.cursors.circle_brush import CircleCursor


class CustomScene(QGraphicsScene):
    def __init__(self, parent=None):
        self.app = parent.app
        super().__init__(parent)
        
        # Get the size of the parent widget
        parent_size = parent.size()

        # Create the QImage with the size of the parent widget
        self.image = QImage(parent_size.width(), parent_size.height(), QImage.Format.Format_ARGB32)
        self.image.fill(Qt.GlobalColor.transparent)
        self.item = QGraphicsPixmapItem(QPixmap.fromImage(self.image))
        self.addItem(self.item)
        # self.item should always be on top
        self.item.setZValue(1)

        # Add a variable to store the last mouse position
        self.last_pos = None
    
    def resize(self):
        # only resize if the new size is larger than the existing image size
        if self.image.width() < self.parent().size().width() or self.image.height() < self.parent().size().height():
            new_image = QImage(self.parent().size().width(), self.parent().size().height(), QImage.Format.Format_ARGB32)
            new_image.fill(Qt.GlobalColor.transparent)
            painter = QPainter(new_image)
            painter.drawImage(0, 0, self.image)
            painter.end()
            self.image = new_image
            self.item.setPixmap(QPixmap.fromImage(self.image))

    def drawAt(self, position):
        painter = QPainter(self.image)
        painter.setPen(QPen(Qt.GlobalColor.black, self.app.brush_settings["size"], Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        
        # Draw a line from the last position to the current one
        if self.last_pos is not None:
            painter.drawLine(self.last_pos, position)
        else:
            painter.drawPoint(position)
        
        painter.end()
        self.item.setPixmap(QPixmap.fromImage(self.image))
    
    def wheelEvent(self, event):
        # Calculate the zoom factor
        zoom_in_factor = self.parent().zoom_in_step
        zoom_out_factor = -self.parent().zoom_out_step

        # Use delta instead of angleDelta
        if event.delta() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        # Update zoom level
        zoom_level = self.parent().zoom_level
        zoom_level += zoom_factor
        if zoom_level < 0.1:
            zoom_level = 0.1
        self.parent().zoom_level = zoom_level

        # Create a QTransform object and scale it
        transform = QTransform()
        transform.scale(self.parent().zoom_level, self.parent().zoom_level)

        # Set the transform
        self.parent().view.setTransform(transform)

        # Redraw lines
        self.parent().draw_lines()

    def eraseAt(self, position):
        painter = QPainter(self.image)
        painter.setPen(QPen(Qt.GlobalColor.white, self.app.brush_settings["size"], Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        
        # Create a QPainterPath
        path = QPainterPath()
        
        # Move to the last position and draw a line to the current one
        if self.last_pos is not None:
            path.moveTo(self.last_pos)
            path.lineTo(position)
        else:
            path.addEllipse(position, self.app.brush_settings["size"]/2, self.app.brush_settings["size"]/2)
        
        # Draw the path
        painter.drawPath(path)
        
        painter.end()
        self.item.setPixmap(QPixmap.fromImage(self.image))

    def mousePressEvent(self, event):
        if self.app.current_tool not in ["brush", "eraser"]:
            super(CustomScene, self).mousePressEvent(event)
            return

        self.last_pos = event.scenePos()
        if self.app.current_tool == "brush":
            self.drawAt(self.last_pos)
        elif self.app.current_tool == "eraser":
            self.eraseAt(self.last_pos)

    def handle_cursor(self, event):
        if self.app.current_tool in ['brush', 'eraser']:
            self.parent().setCursor(CircleCursor(
                Qt.GlobalColor.white,
                Qt.GlobalColor.transparent,
                self.app.brush_settings["size"],
            ))
        elif self.app.current_tool == "active_grid_area":
            if event.buttons() == Qt.MouseButton.LeftButton:
                self.parent().setCursor(Qt.CursorShape.ClosedHandCursor)
            else:
                self.parent().setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.parent().setCursor(Qt.CursorShape.ArrowCursor)
        
    def event(self, event):
        if type(event) == QEnterEvent:
            self.handle_cursor(event)
        return super(CustomScene, self).event(event)

    def mousePressEvent(self, event):
        super(CustomScene, self).mousePressEvent(event)
        self.handle_cursor(event)
    
    def mouseReleaseEvent(self, event):
        super(CustomScene, self).mouseReleaseEvent(event)
        self.handle_cursor(event)

    def mouseMoveEvent(self, event):
        self.handle_cursor(event)
        if self.app.current_tool not in ["brush", "eraser"]:
            super(CustomScene, self).mouseMoveEvent(event)
            return
        
        if self.app.current_tool == "brush":
            self.drawAt(event.scenePos())
        elif self.app.current_tool == "eraser":
            self.eraseAt(event.scenePos())
        
        # Update the last position
        self.last_pos = event.scenePos()
    
    def leaveEvent(self, event):
        self.setCursor(Qt.ArrowCursor)
        super(CustomScene, self).leaveEvent(event)

