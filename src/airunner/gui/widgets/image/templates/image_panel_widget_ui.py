# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'image_panel_widget.ui'
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
    QWidget)

class Ui_image_panel_widget(object):
    def setupUi(self, image_panel_widget):
        if not image_panel_widget.objectName():
            image_panel_widget.setObjectName(u"image_panel_widget")
        image_panel_widget.resize(558, 286)
        self.gridLayout = QGridLayout(image_panel_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.scrollArea = QScrollArea(image_panel_widget)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 556, 284))
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout.addWidget(self.scrollArea, 0, 0, 1, 1)


        self.retranslateUi(image_panel_widget)

        QMetaObject.connectSlotsByName(image_panel_widget)
    # setupUi

    def retranslateUi(self, image_panel_widget):
        image_panel_widget.setWindowTitle(QCoreApplication.translate("image_panel_widget", u"Form", None))
    # retranslateUi

