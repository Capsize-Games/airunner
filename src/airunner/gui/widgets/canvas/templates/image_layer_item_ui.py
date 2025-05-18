# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'image_layer_item.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QLabel, QSizePolicy,
    QWidget)

class Ui_image_layer_item(object):
    def setupUi(self, image_layer_item):
        if not image_layer_item.objectName():
            image_layer_item.setObjectName(u"image_layer_item")
        image_layer_item.resize(168, 193)
        self.gridLayout = QGridLayout(image_layer_item)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.total_images = QLabel(image_layer_item)
        self.total_images.setObjectName(u"total_images")
        self.total_images.setMaximumSize(QSize(16777215, 20))
        self.total_images.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout.addWidget(self.total_images, 1, 0, 1, 1)

        self.image = QLabel(image_layer_item)
        self.image.setObjectName(u"image")
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout.addWidget(self.image, 0, 0, 1, 1)


        self.retranslateUi(image_layer_item)

        QMetaObject.connectSlotsByName(image_layer_item)
    # setupUi

    def retranslateUi(self, image_layer_item):
        image_layer_item.setWindowTitle(QCoreApplication.translate("image_layer_item", u"Form", None))
        self.total_images.setText(QCoreApplication.translate("image_layer_item", u"TextLabel", None))
        self.image.setText("")
    # retranslateUi

