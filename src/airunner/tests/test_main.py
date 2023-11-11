import unittest
from airunner.windows.main.main_window import MainWindow
WINDOW = None

class TestMain(unittest.TestCase):
    def setUp(self):
        global WINDOW
        if not WINDOW:
            WINDOW = MainWindow([], testing=True)
        self.main_window = WINDOW

    def test_main(self):
        self.assertEqual(self.main_window.window.windowTitle(), "AI Runner Untitled")
