# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'slider_spinbox.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QLabel, QSizePolicy,
    QSlider, QSpinBox, QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(157, 67)
        self.gridLayout = QGridLayout(Form)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label = QLabel(Form)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(8)
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.slider = QSlider(Form)
        self.slider.setObjectName(u"slider")
        font1 = QFont()
        font1.setPointSize(8)
        self.slider.setFont(font1)
        self.slider.setMaximum(100)
        self.slider.setOrientation(Qt.Horizontal)

        self.gridLayout.addWidget(self.slider, 1, 0, 1, 1)

        self.spinbox = QSpinBox(Form)
        self.spinbox.setObjectName(u"spinbox")
        self.spinbox.setFont(font1)

        self.gridLayout.addWidget(self.spinbox, 1, 1, 1, 1)


        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.label.setText(QCoreApplication.translate("Form", u"Label", None))
    # retranslateUi

