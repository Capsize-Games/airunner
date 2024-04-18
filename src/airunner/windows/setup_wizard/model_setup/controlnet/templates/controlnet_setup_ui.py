# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'controlnet_setup.ui'
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
    QRadioButton, QSizePolicy, QSpacerItem, QWidget)

class Ui_controlnet_setup(object):
    def setupUi(self, controlnet_setup):
        if not controlnet_setup.objectName():
            controlnet_setup.setObjectName(u"controlnet_setup")
        controlnet_setup.resize(566, 375)
        self.gridLayout = QGridLayout(controlnet_setup)
        self.gridLayout.setObjectName(u"gridLayout")
        self.radioButton = QRadioButton(controlnet_setup)
        self.radioButton.setObjectName(u"radioButton")
        self.radioButton.setChecked(True)

        self.gridLayout.addWidget(self.radioButton, 4, 0, 1, 1)

        self.label = QLabel(controlnet_setup)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.label_3 = QLabel(controlnet_setup)
        self.label_3.setObjectName(u"label_3")

        self.gridLayout.addWidget(self.label_3, 3, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 6, 0, 1, 1)

        self.line = QFrame(controlnet_setup)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 2, 0, 1, 1)

        self.label_2 = QLabel(controlnet_setup)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setWordWrap(True)

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.radioButton_2 = QRadioButton(controlnet_setup)
        self.radioButton_2.setObjectName(u"radioButton_2")

        self.gridLayout.addWidget(self.radioButton_2, 5, 0, 1, 1)


        self.retranslateUi(controlnet_setup)
        self.radioButton.toggled.connect(controlnet_setup.yes_toggled)
        self.radioButton_2.toggled.connect(controlnet_setup.no_toggled)

        QMetaObject.connectSlotsByName(controlnet_setup)
    # setupUi

    def retranslateUi(self, controlnet_setup):
        controlnet_setup.setWindowTitle(QCoreApplication.translate("controlnet_setup", u"Form", None))
        self.radioButton.setText(QCoreApplication.translate("controlnet_setup", u"Yes", None))
        self.label.setText(QCoreApplication.translate("controlnet_setup", u"Stable Diffusion: Controlnet", None))
        self.label_3.setText(QCoreApplication.translate("controlnet_setup", u"Would you like to use Controlnet with Stable Diffusion", None))
        self.label_2.setText(QCoreApplication.translate("controlnet_setup", u"These models allow for greater control over the output of your AI Art and are required for AI Runner to function properly", None))
        self.radioButton_2.setText(QCoreApplication.translate("controlnet_setup", u"No", None))
    # retranslateUi

