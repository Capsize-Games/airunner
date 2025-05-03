# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'stablediffusion_tool_tab.ui'
##
## Created by: Qt User Interface Compiler version 6.7.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QGridLayout, QSizePolicy, QSplitter,
    QTabWidget, QWidget)

from airunner.gui.widgets.active_grid_settings.active_grid_settings_widget import ActiveGridSettingsWidget
from airunner.gui.widgets.brush.brush_container_widget import BrushContainerWidget
from airunner.gui.widgets.canvas.input_image_container import InputImageContainer
from airunner.gui.widgets.embeddings.embeddings_container_widget import EmbeddingsContainerWidget
from airunner.gui.widgets.grid_preferences.grid_preferences_widget import GridPreferencesWidget
from airunner.gui.widgets.lora.lora_container_widget import LoraContainerWidget
from airunner.gui.widgets.stablediffusion.stable_diffusion_settings_widget import StableDiffusionSettingsWidget

class Ui_stablediffusion_tool_tab_widget(object):
    def setupUi(self, stablediffusion_tool_tab_widget):
        if not stablediffusion_tool_tab_widget.objectName():
            stablediffusion_tool_tab_widget.setObjectName(u"stablediffusion_tool_tab_widget")
        stablediffusion_tool_tab_widget.resize(654, 785)
        self.gridLayout_3 = QGridLayout(stablediffusion_tool_tab_widget)
        self.gridLayout_3.setSpacing(0)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.tool_tab_widget_container = QTabWidget(stablediffusion_tool_tab_widget)
        self.tool_tab_widget_container.setObjectName(u"tool_tab_widget_container")
        self.tool_tab_widget_container.setMinimumSize(QSize(0, 0))
        self.tool_tab_widget_container.setMaximumSize(QSize(16777215, 16777215))
        font = QFont()
        font.setPointSize(8)
        self.tool_tab_widget_container.setFont(font)
        self.tool_tab_widget_container.setCursor(QCursor(Qt.ArrowCursor))
        self.tool_tab_widget_container.setAcceptDrops(False)
        self.tool_tab_widget_container.setTabPosition(QTabWidget.TabPosition.North)
        self.tab_3 = QWidget()
        self.tab_3.setObjectName(u"tab_3")
        self.gridLayout_4 = QGridLayout(self.tab_3)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.gridLayout_4.setHorizontalSpacing(0)
        self.gridLayout_4.setVerticalSpacing(10)
        self.gridLayout_4.setContentsMargins(10, 10, 0, 0)
        self.stable_diffusion_widget = StableDiffusionSettingsWidget(self.tab_3)
        self.stable_diffusion_widget.setObjectName(u"stable_diffusion_widget")

        self.gridLayout_4.addWidget(self.stable_diffusion_widget, 0, 0, 2, 2)

        self.tool_tab_widget_container.addTab(self.tab_3, "")
        self.tab_5 = QWidget()
        self.tab_5.setObjectName(u"tab_5")
        self.gridLayout_6 = QGridLayout(self.tab_5)
        self.gridLayout_6.setSpacing(0)
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.gridLayout_6.setContentsMargins(0, 0, 0, 0)
        self.image_to_image = InputImageContainer(self.tab_5)
        self.image_to_image.setObjectName(u"image_to_image")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.image_to_image.sizePolicy().hasHeightForWidth())
        self.image_to_image.setSizePolicy(sizePolicy)

        self.gridLayout_6.addWidget(self.image_to_image, 0, 0, 1, 1)

        self.tool_tab_widget_container.addTab(self.tab_5, "")
        self.tab_8 = QWidget()
        self.tab_8.setObjectName(u"tab_8")
        self.gridLayout_11 = QGridLayout(self.tab_8)
        self.gridLayout_11.setSpacing(0)
        self.gridLayout_11.setObjectName(u"gridLayout_11")
        self.gridLayout_11.setContentsMargins(0, 0, 0, 0)
        self.controlnet_image = InputImageContainer(self.tab_8)
        self.controlnet_image.setObjectName(u"controlnet_image")
        sizePolicy.setHeightForWidth(self.controlnet_image.sizePolicy().hasHeightForWidth())
        self.controlnet_image.setSizePolicy(sizePolicy)

        self.gridLayout_11.addWidget(self.controlnet_image, 0, 0, 1, 1)

        self.tool_tab_widget_container.addTab(self.tab_8, "")
        self.tab_9 = QWidget()
        self.tab_9.setObjectName(u"tab_9")
        self.gridLayout_12 = QGridLayout(self.tab_9)
        self.gridLayout_12.setSpacing(0)
        self.gridLayout_12.setObjectName(u"gridLayout_12")
        self.gridLayout_12.setContentsMargins(0, 0, 0, 0)
        self.widget_2 = InputImageContainer(self.tab_9)
        self.widget_2.setObjectName(u"widget_2")

        self.gridLayout_12.addWidget(self.widget_2, 0, 0, 1, 1)

        self.tool_tab_widget_container.addTab(self.tab_9, "")
        self.tab_6 = QWidget()
        self.tab_6.setObjectName(u"tab_6")
        self.gridLayout_7 = QGridLayout(self.tab_6)
        self.gridLayout_7.setObjectName(u"gridLayout_7")
        self.gridLayout_7.setHorizontalSpacing(0)
        self.gridLayout_7.setVerticalSpacing(10)
        self.gridLayout_7.setContentsMargins(0, 0, 0, 0)
        self.lora_container_widget = LoraContainerWidget(self.tab_6)
        self.lora_container_widget.setObjectName(u"lora_container_widget")

        self.gridLayout_7.addWidget(self.lora_container_widget, 0, 0, 1, 1)

        self.tool_tab_widget_container.addTab(self.tab_6, "")
        self.tab_7 = QWidget()
        self.tab_7.setObjectName(u"tab_7")
        self.gridLayout_8 = QGridLayout(self.tab_7)
        self.gridLayout_8.setObjectName(u"gridLayout_8")
        self.gridLayout_8.setHorizontalSpacing(0)
        self.gridLayout_8.setVerticalSpacing(10)
        self.gridLayout_8.setContentsMargins(0, 0, 0, 0)
        self.embeddings_container_widget = EmbeddingsContainerWidget(self.tab_7)
        self.embeddings_container_widget.setObjectName(u"embeddings_container_widget")

        self.gridLayout_8.addWidget(self.embeddings_container_widget, 0, 0, 1, 1)

        self.tool_tab_widget_container.addTab(self.tab_7, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        self.gridLayout_5 = QGridLayout(self.tab_2)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.gridLayout_5.setHorizontalSpacing(0)
        self.gridLayout_5.setVerticalSpacing(10)
        self.gridLayout_5.setContentsMargins(10, 10, 0, 0)
        self.brush_container_widget = BrushContainerWidget(self.tab_2)
        self.brush_container_widget.setObjectName(u"brush_container_widget")

        self.gridLayout_5.addWidget(self.brush_container_widget, 0, 0, 1, 1)

        self.tool_tab_widget_container.addTab(self.tab_2, "")
        self.tab_4 = QWidget()
        self.tab_4.setObjectName(u"tab_4")
        self.gridLayout = QGridLayout(self.tab_4)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(10, 10, 0, 0)
        self.grid_settings_splitter = QSplitter(self.tab_4)
        self.grid_settings_splitter.setObjectName(u"grid_settings_splitter")
        self.grid_settings_splitter.setOrientation(Qt.Orientation.Vertical)
        self.widget = GridPreferencesWidget(self.grid_settings_splitter)
        self.widget.setObjectName(u"widget")
        self.grid_settings_splitter.addWidget(self.widget)
        self.active_grid_settings_widget = ActiveGridSettingsWidget(self.grid_settings_splitter)
        self.active_grid_settings_widget.setObjectName(u"active_grid_settings_widget")
        self.grid_settings_splitter.addWidget(self.active_grid_settings_widget)

        self.gridLayout.addWidget(self.grid_settings_splitter, 0, 0, 1, 1)

        self.tool_tab_widget_container.addTab(self.tab_4, "")

        self.gridLayout_3.addWidget(self.tool_tab_widget_container, 0, 0, 1, 1)


        self.retranslateUi(stablediffusion_tool_tab_widget)

        self.tool_tab_widget_container.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(stablediffusion_tool_tab_widget)
    # setupUi

    def retranslateUi(self, stablediffusion_tool_tab_widget):
        stablediffusion_tool_tab_widget.setWindowTitle(QCoreApplication.translate("stablediffusion_tool_tab_widget", u"Form", None))
        self.tool_tab_widget_container.setTabText(self.tool_tab_widget_container.indexOf(self.tab_3), QCoreApplication.translate("stablediffusion_tool_tab_widget", u"Stable Diffusion", None))
        self.image_to_image.setProperty("settings_key", QCoreApplication.translate("stablediffusion_tool_tab_widget", u"image_to_image_settings", None))
        self.tool_tab_widget_container.setTabText(self.tool_tab_widget_container.indexOf(self.tab_5), QCoreApplication.translate("stablediffusion_tool_tab_widget", u"Input image", None))
        self.controlnet_image.setProperty("settings_key", QCoreApplication.translate("stablediffusion_tool_tab_widget", u"controlnet_settings", None))
        self.tool_tab_widget_container.setTabText(self.tool_tab_widget_container.indexOf(self.tab_8), QCoreApplication.translate("stablediffusion_tool_tab_widget", u"Controlnet", None))
        self.widget_2.setProperty("settings_key", QCoreApplication.translate("stablediffusion_tool_tab_widget", u"outpaint_settings", None))
        self.tool_tab_widget_container.setTabText(self.tool_tab_widget_container.indexOf(self.tab_9), QCoreApplication.translate("stablediffusion_tool_tab_widget", u"Inpaint", None))
        self.tool_tab_widget_container.setTabText(self.tool_tab_widget_container.indexOf(self.tab_6), QCoreApplication.translate("stablediffusion_tool_tab_widget", u"LoRA", None))
        self.tool_tab_widget_container.setTabText(self.tool_tab_widget_container.indexOf(self.tab_7), QCoreApplication.translate("stablediffusion_tool_tab_widget", u"Embeddings", None))
        self.tool_tab_widget_container.setTabText(self.tool_tab_widget_container.indexOf(self.tab_2), QCoreApplication.translate("stablediffusion_tool_tab_widget", u"Brush", None))
        self.tool_tab_widget_container.setTabText(self.tool_tab_widget_container.indexOf(self.tab_4), QCoreApplication.translate("stablediffusion_tool_tab_widget", u"Grid", None))
    # retranslateUi

