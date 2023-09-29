import unittest
from airunner.canvas import Canvas
from airunner.windows.main.main_window import MainWindow
WINDOW = None


class TestCanvas(unittest.TestCase):
    def setUp(self):
        global WINDOW
        if not WINDOW:
            WINDOW = MainWindow([], testing=True)
        self.canvas = Canvas(WINDOW)

    def test_set_current_layer(self):
        self.canvas.set_current_layer(1)
        self.assertEqual(self.canvas.current_layer_index, 1)

    def test_move_layer_up(self):
        self.canvas.add_layer()
        self.canvas.move_layer_up(self.canvas.layers[1])
        self.assertEqual(self.canvas.current_layer_index, 0)

    def test_move_layer_down(self):
        self.canvas.add_layer()
        self.canvas.add_layer()
        self.canvas.move_layer_down(self.canvas.layers[0])
        self.assertEqual(self.canvas.current_layer_index, 1)

    def test_add_layer(self):
        self.canvas.add_layer()
        self.assertEqual(len(self.canvas.layers), 2)
