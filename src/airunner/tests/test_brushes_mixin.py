import unittest
from airunner.main import MainWindow
WINDOW = None


class TestBrushesMixin(unittest.TestCase):
    def setUp(self):
        global WINDOW
        if not WINDOW:
            WINDOW = MainWindow([], testing=True)
        self.app = WINDOW

    def test_set_button_colors(self):
        self.app.settings_manager.settings.primary_color.set("#00ff00")
        self.app.set_button_colors()
        self.assertEqual(self.app.window.primary_color_button.styleSheet(), "background-color: #00ff00;")
