# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'image_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QSizePolicy,
    QWidget)

class Ui_image_widget(object):
    def setupUi(self, image_widget):
        if not image_widget.objectName():
            image_widget.setObjectName(u"image_widget")
        image_widget.resize(128, 128)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(image_widget.sizePolicy().hasHeightForWidth())
        image_widget.setSizePolicy(sizePolicy)
        image_widget.setMinimumSize(QSize(0, 0))
        image_widget.setMaximumSize(QSize(128, 128))
        self.gridLayout = QGridLayout(image_widget)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.image_frame = QFrame(image_widget)
        self.image_frame.setObjectName(u"image_frame")
        self.image_frame.setMinimumSize(QSize(128, 128))
        self.image_frame.setMaximumSize(QSize(128, 128))
        self.image_frame.setFrameShape(QFrame.StyledPanel)
        self.image_frame.setFrameShadow(QFrame.Raised)

        self.gridLayout.addWidget(self.image_frame, 0, 0, 1, 1)


        self.retranslateUi(image_widget)

        QMetaObject.connectSlotsByName(image_widget)
    # setupUi

    def retranslateUi(self, image_widget):
        image_widget.setWindowTitle(QCoreApplication.translate("image_widget", u"Form", None))
    # retranslateUi

