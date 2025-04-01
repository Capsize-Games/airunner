# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'input_image_container.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QLabel,
    QSizePolicy, QTabWidget, QWidget)

class Ui_input_image_container(object):
    def setupUi(self, input_image_container):
        if not input_image_container.objectName():
            input_image_container.setObjectName(u"input_image_container")
        input_image_container.resize(365, 452)
        self.gridLayout = QGridLayout(input_image_container)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.tabWidget = QTabWidget(input_image_container)
        self.tabWidget.setObjectName(u"tabWidget")

        self.gridLayout.addWidget(self.tabWidget, 2, 0, 1, 1)

        self.label = QLabel(input_image_container)
        self.label.setObjectName(u"label")
        self.label.setMargin(10)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.line = QFrame(input_image_container)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 1, 0, 1, 1)


        self.retranslateUi(input_image_container)

        self.tabWidget.setCurrentIndex(-1)


        QMetaObject.connectSlotsByName(input_image_container)
    # setupUi

    def retranslateUi(self, input_image_container):
        input_image_container.setWindowTitle(QCoreApplication.translate("input_image_container", u"Form", None))
        self.label.setText(QCoreApplication.translate("input_image_container", u"TextLabel", None))
    # retranslateUi

