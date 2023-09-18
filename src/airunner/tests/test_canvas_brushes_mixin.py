import unittest

from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QPen

from airunner.mixins.canvas_brushes_mixin import CanvasBrushesMixin
from airunner.aihandler.settings_manager import SettingsManager
from airunner.models.layerdata import LayerData
from airunner.models.linedata import LineData


class TestCanvasBrushesMixin(unittest.TestCase):
    def setUp(self):
        self.cbm = CanvasBrushesMixin()
        self.cbm.pos_x = 0
        self.cbm.pos_y = 0
        self.cbm.settings_manager = SettingsManager()
        self.cbm.settings_manager.set_value("mask_brush_size", 10)
        self.cbm.current_layer = LayerData(0, "Untitled", True, 1.0, QPoint(0, 0))

    def test_get_line_extremities(self):
        self.cbm.current_layer.lines = [LineData(QPoint(-10, -10), QPoint(10, 10), QPen(), 0, 255)]
        top, left, bottom, right = self.cbm.get_line_extremities()
        self.assertEqual(top, -20)
        self.assertEqual(left, -20)
        self.assertEqual(bottom, 20)
        self.assertEqual(right, 20)

    # write another test for get_line_extremities with multiple lines
    def test_get_line_extremities_multiple_lines(self):
        self.cbm.current_layer.lines = [
            LineData(QPoint(-10, -10), QPoint(10, 10), QPen(), 0, 255),
            LineData(QPoint(-20, -20), QPoint(20, 20), QPen(), 0, 255)
        ]
        top, left, bottom, right = self.cbm.get_line_extremities()
        self.assertEqual(top, -30)
        self.assertEqual(left, -30)
        self.assertEqual(bottom, 30)
        self.assertEqual(right, 30)

    # def test_get_line_extremities_multiple_lines_with_offset(self):
    #     self.cbm.current_layer.lines = [
    #         LineData(QPoint(-10, -10), QPoint(10, 10), QPen(), 0, 255),
    #         LineData(QPoint(-20, -20), QPoint(20, 20), QPen(), 0, 255)
    #     ]
    #     self.cbm.current_layer.offset = QPoint(10, 10)
    #     top, left, bottom, right = self.cbm.get_line_extremities()
    #     self.assertEqual(top, -20)
    #     self.assertEqual(left, -20)
    #     self.assertEqual(bottom, 40)
    #     self.assertEqual(right, 40)