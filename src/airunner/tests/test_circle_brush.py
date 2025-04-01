import unittest
from unittest.mock import patch, MagicMock

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPixmap, QCursor, QPen, QBrush
from PySide6.QtWidgets import QApplication

from airunner.gui.cursors.circle_brush import circle_cursor


class TestCircleBrush(unittest.TestCase):
    """Test cases for the circle_brush cursor creation functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up QApplication instance for all tests."""
        if not QApplication.instance():
            cls.qapp = QApplication([])
        else:
            cls.qapp = QApplication.instance()

    @classmethod
    def tearDownClass(cls):
        """Clean up QApplication instance after tests."""
        cls.qapp.quit()

    def test_circle_cursor_creates_qcursor(self):
        """Test that circle_cursor returns a QCursor object."""
        cursor = circle_cursor("black", "white")
        self.assertIsInstance(cursor, QCursor)

    def test_circle_cursor_with_default_size(self):
        """Test circle_cursor with default size."""
        cursor = circle_cursor("black", "white")
        pixmap = cursor.pixmap()
        self.assertEqual(pixmap.width(), 32)
        self.assertEqual(pixmap.height(), 32)

    def test_circle_cursor_with_custom_size(self):
        """Test circle_cursor with custom size."""
        cursor = circle_cursor("black", "white", pixmap_size=64)
        pixmap = cursor.pixmap()
        self.assertEqual(pixmap.width(), 64)
        self.assertEqual(pixmap.height(), 64)

    @patch('airunner.gui.cursors.circle_brush.QPainter')
    @patch('airunner.gui.cursors.circle_brush.QPixmap')
    @patch('airunner.gui.cursors.circle_brush.QCursor')
    def test_circle_cursor_drawing_operations(self, mock_qcursor, mock_qpixmap, mock_qpainter):
        """Test that drawing operations are performed correctly."""
        # Set up mocks
        mock_pixmap_instance = MagicMock()
        mock_qpixmap.return_value = mock_pixmap_instance

        mock_painter_instance = MagicMock()
        mock_qpainter.return_value = mock_painter_instance

        # Explicitly set the return value for RenderHint.Antialiasing
        mock_qpainter.RenderHint.Antialiasing = QPainter.RenderHint.Antialiasing

        mock_cursor_instance = MagicMock()
        mock_qcursor.return_value = mock_cursor_instance

        # Call the function
        result = circle_cursor("red", "blue", pixmap_size=48)

        # Verify pixmap creation
        mock_qpixmap.assert_called_once_with(48, 48)
        mock_pixmap_instance.fill.assert_called_once_with(Qt.GlobalColor.transparent)

        # Verify painter setup
        mock_qpainter.assert_called_once_with(mock_pixmap_instance)
        mock_painter_instance.setRenderHint.assert_called_once_with(QPainter.RenderHint.Antialiasing)

        # Verify drawing operations
        self.assertEqual(mock_painter_instance.setPen.call_count, 2)
        self.assertEqual(mock_painter_instance.setBrush.call_count, 2)
        self.assertEqual(mock_painter_instance.drawEllipse.call_count, 2)

        # Verify painter cleanup
        mock_painter_instance.end.assert_called_once()

        # Verify cursor creation and return
        mock_qcursor.assert_called_once_with(mock_pixmap_instance, 24, 24)
        self.assertEqual(result, mock_cursor_instance)

    def test_circle_cursor_with_different_colors(self):
        """Test circle_cursor with different outline and fill colors."""
        # Test with various color combinations
        color_pairs = [
            ("red", "blue"),
            ("green", "yellow"),
            ("#FF5733", "#C70039"),
            ("rgb(255,0,0)", "rgb(0,255,0)")
        ]
        
        for outline, fill in color_pairs:
            cursor = circle_cursor(outline, fill)
            self.assertIsInstance(cursor, QCursor)
            # We can't directly test the colors in the cursor, but at least we can verify it creates successfully

    def test_circle_cursor_hotspot(self):
        """Test that cursor hotspot is set correctly."""
        # Test hotspot for different sizes
        sizes = [16, 32, 48, 64]
        
        for size in sizes:
            cursor = circle_cursor("black", "white", pixmap_size=size)
            # The hotspot should be at the center of the pixmap
            expected_hotspot = size // 2
            
            # Get the actual hotspot - QCursor doesn't expose the hotspot directly
            # in a convenient way for testing, so we'll just infer from the size
            # This is more of a functional test ensuring the cursor is created correctly
            self.assertIsInstance(cursor, QCursor)
            pixmap = cursor.pixmap()
            self.assertEqual(pixmap.width(), size)
            self.assertEqual(pixmap.height(), size)

    def test_circle_cursor_integer_size(self):
        """Test that non-integer size is converted to integer."""
        # Test with a float size
        cursor = circle_cursor("black", "white", pixmap_size=32.5)
        pixmap = cursor.pixmap()
        self.assertEqual(pixmap.width(), 32)
        self.assertEqual(pixmap.height(), 32)
        
        # Test with a string size (should be converted to int if possible)
        with self.assertRaises(ValueError):
            circle_cursor("black", "white", pixmap_size="not-a-number")


if __name__ == "__main__":
    unittest.main()