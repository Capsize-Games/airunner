# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'batch_container.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QScrollArea,
    QSizePolicy, QWidget)

class Ui_batch_conatiner(object):
    def setupUi(self, batch_conatiner):
        if not batch_conatiner.objectName():
            batch_conatiner.setObjectName(u"batch_conatiner")
        batch_conatiner.resize(480, 176)
        self.gridLayout = QGridLayout(batch_conatiner)
        self.gridLayout.setObjectName(u"gridLayout")
        self.scrollArea = QScrollArea(batch_conatiner)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 460, 124))
        self.gridLayout_2 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout.addWidget(self.scrollArea, 1, 0, 1, 1)

        self.image_folders = QComboBox(batch_conatiner)
        self.image_folders.setObjectName(u"image_folders")

        self.gridLayout.addWidget(self.image_folders, 0, 0, 1, 1)


        self.retranslateUi(batch_conatiner)

        QMetaObject.connectSlotsByName(batch_conatiner)
    # setupUi

    def retranslateUi(self, batch_conatiner):
        batch_conatiner.setWindowTitle(QCoreApplication.translate("batch_conatiner", u"Form", None))
    # retranslateUi

