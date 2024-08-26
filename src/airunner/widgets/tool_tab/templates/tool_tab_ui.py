# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tool_tab.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QScrollArea, QSizePolicy,
    QSplitter, QTabWidget, QWidget)

from airunner.widgets.active_grid_settings.active_grid_settings_widget import ActiveGridSettingsWidget
from airunner.widgets.brush.brush_container_widget import BrushContainerWidget
from airunner.widgets.llm.llm_settings_widget import LLMSettingsWidget
from airunner.widgets.stablediffusion.stable_diffusion_settings_widget import StableDiffusionSettingsWidget

class Ui_tool_tab_widget(object):
    def setupUi(self, tool_tab_widget):
        if not tool_tab_widget.objectName():
            tool_tab_widget.setObjectName(u"tool_tab_widget")
        tool_tab_widget.resize(641, 537)
        self.gridLayout_3 = QGridLayout(tool_tab_widget)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.tool_tab_widget_container = QTabWidget(tool_tab_widget)
        self.tool_tab_widget_container.setObjectName(u"tool_tab_widget_container")
        self.tool_tab_widget_container.setMinimumSize(QSize(0, 0))
        self.tool_tab_widget_container.setMaximumSize(QSize(16777215, 16777215))
        self.tool_tab_widget_container.setAcceptDrops(False)
        self.tool_tab_widget_container.setTabPosition(QTabWidget.TabPosition.North)
        self.tab_3 = QWidget()
        self.tab_3.setObjectName(u"tab_3")
        self.gridLayout = QGridLayout(self.tab_3)
        self.gridLayout.setObjectName(u"gridLayout")
        self.splitter = QSplitter(self.tab_3)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Vertical)
        self.scrollArea = QScrollArea(self.splitter)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents_2 = QWidget()
        self.scrollAreaWidgetContents_2.setObjectName(u"scrollAreaWidgetContents_2")
        self.scrollAreaWidgetContents_2.setGeometry(QRect(0, 0, 617, 158))
        self.gridLayout_4 = QGridLayout(self.scrollAreaWidgetContents_2)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.gridLayout_4.setContentsMargins(0, 0, 0, 0)
        self.stable_diffusion_widget = StableDiffusionSettingsWidget(self.scrollAreaWidgetContents_2)
        self.stable_diffusion_widget.setObjectName(u"stable_diffusion_widget")

        self.gridLayout_4.addWidget(self.stable_diffusion_widget, 0, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents_2)
        self.splitter.addWidget(self.scrollArea)
        self.brush_container_widget = BrushContainerWidget(self.splitter)
        self.brush_container_widget.setObjectName(u"brush_container_widget")
        self.splitter.addWidget(self.brush_container_widget)
        self.active_grid_settings_widget = ActiveGridSettingsWidget(self.splitter)
        self.active_grid_settings_widget.setObjectName(u"active_grid_settings_widget")
        self.splitter.addWidget(self.active_grid_settings_widget)

        self.gridLayout.addWidget(self.splitter, 0, 0, 1, 1)

        self.tool_tab_widget_container.addTab(self.tab_3, "")
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.gridLayout_2 = QGridLayout(self.tab)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.llm_splitter = QSplitter(self.tab)
        self.llm_splitter.setObjectName(u"llm_splitter")
        self.llm_splitter.setOrientation(Qt.Orientation.Vertical)
        self.llm_settings = LLMSettingsWidget(self.llm_splitter)
        self.llm_settings.setObjectName(u"llm_settings")
        self.llm_splitter.addWidget(self.llm_settings)
        self.llm_preferences = QWidget(self.llm_splitter)
        self.llm_preferences.setObjectName(u"llm_preferences")
        self.llm_splitter.addWidget(self.llm_preferences)

        self.gridLayout_2.addWidget(self.llm_splitter, 0, 0, 1, 1)

        self.tool_tab_widget_container.addTab(self.tab, "")

        self.gridLayout_3.addWidget(self.tool_tab_widget_container, 0, 0, 1, 1)


        self.retranslateUi(tool_tab_widget)

        self.tool_tab_widget_container.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(tool_tab_widget)
    # setupUi

    def retranslateUi(self, tool_tab_widget):
        tool_tab_widget.setWindowTitle(QCoreApplication.translate("tool_tab_widget", u"Form", None))
        self.tool_tab_widget_container.setTabText(self.tool_tab_widget_container.indexOf(self.tab_3), QCoreApplication.translate("tool_tab_widget", u"StableDiffusion", None))
        self.tool_tab_widget_container.setTabText(self.tool_tab_widget_container.indexOf(self.tab), QCoreApplication.translate("tool_tab_widget", u"LLM", None))
    # retranslateUi

