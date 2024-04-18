# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'choose_style.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QGridLayout,
    QLabel, QSizePolicy, QSpacerItem, QWidget)

class Ui_choose_model_style(object):
    def setupUi(self, choose_model_style):
        if not choose_model_style.objectName():
            choose_model_style.setObjectName(u"choose_model_style")
        choose_model_style.resize(530, 533)
        self.gridLayout = QGridLayout(choose_model_style)
        self.gridLayout.setObjectName(u"gridLayout")
        self.frame_3 = QFrame(choose_model_style)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setFrameShape(QFrame.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Raised)
        self.gridLayout_4 = QGridLayout(self.frame_3)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.label_3 = QLabel(self.frame_3)
        self.label_3.setObjectName(u"label_3")
        font = QFont()
        font.setBold(True)
        self.label_3.setFont(font)

        self.gridLayout_4.addWidget(self.label_3, 0, 0, 1, 1)

        self.comboBox = QComboBox(self.frame_3)
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.setObjectName(u"comboBox")

        self.gridLayout_4.addWidget(self.comboBox, 1, 0, 1, 1)


        self.gridLayout.addWidget(self.frame_3, 5, 0, 1, 1)

        self.label_2 = QLabel(choose_model_style)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setWordWrap(True)

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.label = QLabel(choose_model_style)
        self.label.setObjectName(u"label")
        font1 = QFont()
        font1.setPointSize(11)
        font1.setBold(True)
        self.label.setFont(font1)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 10, 0, 1, 1)

        self.line = QFrame(choose_model_style)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 2, 0, 1, 1)


        self.retranslateUi(choose_model_style)

        QMetaObject.connectSlotsByName(choose_model_style)
    # setupUi

    def retranslateUi(self, choose_model_style):
        choose_model_style.setWindowTitle(QCoreApplication.translate("choose_model_style", u"Form", None))
        self.label_3.setText(QCoreApplication.translate("choose_model_style", u"Style", None))
        self.comboBox.setItemText(0, QCoreApplication.translate("choose_model_style", u"Photography", None))
        self.comboBox.setItemText(1, QCoreApplication.translate("choose_model_style", u"Illustration", None))

        self.label_2.setText(QCoreApplication.translate("choose_model_style", u"Choose your default model settings. These can be overriden at any time.", None))
        self.label.setText(QCoreApplication.translate("choose_model_style", u"Stable Diffusion Model Setup", None))
    # retranslateUi

