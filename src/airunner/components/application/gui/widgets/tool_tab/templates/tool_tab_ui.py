# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tool_tab.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QSizePolicy, QTabWidget,
    QWidget)

from airunner.components.llm.gui.widgets.llm_settings_widget import LLMSettingsWidget

class Ui_tool_tab_widget(object):
    def setupUi(self, tool_tab_widget):
        if not tool_tab_widget.objectName():
            tool_tab_widget.setObjectName(u"tool_tab_widget")
        tool_tab_widget.resize(696, 867)
        self.gridLayout_3 = QGridLayout(tool_tab_widget)
        self.gridLayout_3.setSpacing(0)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.tool_tab_widget_container = QTabWidget(tool_tab_widget)
        self.tool_tab_widget_container.setObjectName(u"tool_tab_widget_container")
        self.tool_tab_widget_container.setMinimumSize(QSize(0, 0))
        self.tool_tab_widget_container.setMaximumSize(QSize(16777215, 16777215))
        font = QFont()
        font.setPointSize(8)
        self.tool_tab_widget_container.setFont(font)
        self.tool_tab_widget_container.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.tool_tab_widget_container.setAcceptDrops(False)
        self.tool_tab_widget_container.setTabPosition(QTabWidget.TabPosition.North)
        self.tool_tab_widget_container.setTabsClosable(False)
        self.tool_tab_widget_container.setMovable(False)
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.gridLayout_2 = QGridLayout(self.tab)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(10, 10, 10, 10)
        self.llm_settings = LLMSettingsWidget(self.tab)
        self.llm_settings.setObjectName(u"llm_settings")

        self.gridLayout_2.addWidget(self.llm_settings, 0, 0, 1, 1)

        self.tool_tab_widget_container.addTab(self.tab, "")

        self.gridLayout_3.addWidget(self.tool_tab_widget_container, 0, 0, 1, 1)


        self.retranslateUi(tool_tab_widget)

        self.tool_tab_widget_container.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(tool_tab_widget)
    # setupUi

    def retranslateUi(self, tool_tab_widget):
        tool_tab_widget.setWindowTitle(QCoreApplication.translate("tool_tab_widget", u"Form", None))
        self.tool_tab_widget_container.setTabText(self.tool_tab_widget_container.indexOf(self.tab), QCoreApplication.translate("tool_tab_widget", u"LLM", None))
    # retranslateUi

