# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'brushes_container.ui'
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

class Ui_brushes_container(object):
    def setupUi(self, brushes_container):
        if not brushes_container.objectName():
            brushes_container.setObjectName(u"brushes_container")
        brushes_container.resize(400, 300)
        self.gridLayout = QGridLayout(brushes_container)
        self.gridLayout.setObjectName(u"gridLayout")
        self.scrollArea = QScrollArea(brushes_container)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 380, 280))
        self.gridLayout_2 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout.addWidget(self.scrollArea, 0, 0, 1, 1)


        self.retranslateUi(brushes_container)

        QMetaObject.connectSlotsByName(brushes_container)
    # setupUi

    def retranslateUi(self, brushes_container):
        brushes_container.setWindowTitle(QCoreApplication.translate("brushes_container", u"Form", None))
    # retranslateUi

