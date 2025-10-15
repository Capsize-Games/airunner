# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'system_resources_panel.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QLabel, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_system_resources_panel(object):
    def setupUi(self, system_resources_panel):
        if not system_resources_panel.objectName():
            system_resources_panel.setObjectName(u"system_resources_panel")
        system_resources_panel.resize(400, 400)
        self.verticalLayout = QVBoxLayout(system_resources_panel)
        self.verticalLayout.setSpacing(10)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel(system_resources_panel)
        self.title_label.setObjectName(u"title_label")
        self.title_label.setStyleSheet(u"font-size: 18px; font-weight: bold;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)

        self.verticalLayout.addWidget(self.title_label)

        self.devices_scroll_area = QScrollArea(system_resources_panel)
        self.devices_scroll_area.setObjectName(u"devices_scroll_area")
        self.devices_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.devices_scroll_area.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 400, 368))
        self.devices_scroll_area.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout.addWidget(self.devices_scroll_area)


        self.retranslateUi(system_resources_panel)

        QMetaObject.connectSlotsByName(system_resources_panel)
    # setupUi

    def retranslateUi(self, system_resources_panel):
        system_resources_panel.setWindowTitle(QCoreApplication.translate("system_resources_panel", u"Form", None))
        self.title_label.setText(QCoreApplication.translate("system_resources_panel", u"System Resources", None))
    # retranslateUi

