import os
import pickle
import random
import sys
import webbrowser
import cv2
import numpy as np
from PIL import Image
from PyQt6 import uic, QtCore
from PyQt6.QtWidgets import QApplication, QColorDialog, QFileDialog
from PyQt6.QtCore import QPoint, pyqtSlot, QRect
from PyQt6.QtGui import QPainter, QColor, QGuiApplication
from aihandler.qtvar import TQDMVar, ImageVar, MessageHandlerVar, ErrorHandlerVar
from aihandler.settings import MAX_SEED, AVAILABLE_SCHEDULERS_BY_ACTION, MODELS, LOG_LEVEL
from airunner.mixins.embedding_mixin import EmbeddingMixin
from airunner.mixins.extension_mixin import ExtensionMixin
from airunner.mixins.history_mixin import HistoryMixin
from airunner.mixins.layer_mixin import LayerMixin
from airunner.mixins.menubar_mixin import MenubarMixin
from airunner.mixins.model_mixin import ModelMixin
from airunner.mixins.toolbar_mixin import ToolbarMixin
from airunner.windows.about import AboutWindow
from airunner.windows.advanced_settings import AdvancedSettings
from airunner.windows.extensions import ExtensionsWindow
from airunner.windows.grid_settings import GridSettings
from airunner.windows.preferences import PreferencesWindow
from airunner.windows.video import VideoPopup
from airunner.qtcanvas import Canvas
from aihandler.settings_manager import SettingsManager
from airunner.runai_client import OfflineClient
from airunner.filters import FilterGaussianBlur, FilterBoxBlur, FilterUnsharpMask, FilterSaturation, \
    FilterColorBalance, FilterPixelArt
import qdarktheme


class CanvasMixin:
    window = None
    settings_manager = None

    def initialize(self):
        self.canvas = Canvas(self)
        self.settings_manager.settings.show_grid.my_signal.connect(self.canvas.update)
        self.settings_manager.settings.snap_to_grid.my_signal.connect(self.canvas.update)
        self.settings_manager.settings.line_color.my_signal.connect(self.canvas.update_grid_pen)

    def update_canvas_color(self, color):
        self.window.canvas_container.setStyleSheet(f"background-color: {color};")
        self.window.canvas_container.setAutoFillBackground(True)
