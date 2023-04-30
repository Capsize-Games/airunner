import unittest

from PyQt6.QtWidgets import QApplication

from airunner.main import MainWindow


class TestMain(unittest.TestCase):
    def setUp(self):
        self.main_window = MainWindow([], testing=True)

    def test_main(self):
        self.assertEqual(self.main_window.window.windowTitle(), "AI Runner Untitled")

