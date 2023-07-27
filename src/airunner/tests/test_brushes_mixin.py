import unittest
from airunner.main_window import MainWindow
WINDOW = None


class TestBrushesMixin(unittest.TestCase):
    def setUp(self):
        global WINDOW
        if not WINDOW:
            WINDOW = MainWindow([], testing=True)
        self.app = WINDOW
