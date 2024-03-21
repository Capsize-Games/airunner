import unittest
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication
from src.airunner.widgets.canvas.draggables.draggable_pixmap import DraggablePixmap

app = QApplication([])

class TestDraggablePixmap(unittest.TestCase):
    def setUp(self):
        self.pixmap = QPixmap()
        self.widget = DraggablePixmap(self.pixmap)

    def test_initialization(self):
        self.assertIsNotNone(self.widget)
        self.assertEqual(self.widget.pixmap, self.pixmap)
        self.assertEqual(self.widget.last_pos.x(), 0)
        self.assertEqual(self.widget.last_pos.y(), 0)
        self.assertFalse(self.widget.save)

    def test_setPos(self):
        self.widget.setPos(10, 20)
        self.assertEqual(self.widget.pos().x(), 10)
        self.assertEqual(self.widget.pos().y(), 20)

    # Add more tests as needed for other methods

if __name__ == '__main__':
    unittest.main()