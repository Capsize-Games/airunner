# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'choose_model.ui'
##
## Created by: Qt User Interface Compiler version 6.6.2
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
    QLabel, QPushButton, QSizePolicy, QSpacerItem,
    QWidget)

class Ui_choose_model(object):
    def setupUi(self, choose_model):
        if not choose_model.objectName():
            choose_model.setObjectName(u"choose_model")
        choose_model.resize(530, 533)
        self.gridLayout = QGridLayout(choose_model)
        self.gridLayout.setObjectName(u"gridLayout")
        self.line = QFrame(choose_model)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.gridLayout.addWidget(self.line, 2, 0, 1, 1)

        self.frame = QFrame(choose_model)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)
        self.gridLayout_2 = QGridLayout(self.frame)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.comboBox_3 = QComboBox(self.frame)
        self.comboBox_3.setObjectName(u"comboBox_3")

        self.gridLayout_2.addWidget(self.comboBox_3, 2, 0, 1, 1)

        self.label_6 = QLabel(self.frame)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setWordWrap(True)

        self.gridLayout_2.addWidget(self.label_6, 1, 0, 1, 1)

        self.label_5 = QLabel(self.frame)
        self.label_5.setObjectName(u"label_5")
        font = QFont()
        font.setBold(True)
        self.label_5.setFont(font)

        self.gridLayout_2.addWidget(self.label_5, 0, 0, 1, 1)

        self.pushButton = QPushButton(self.frame)
        self.pushButton.setObjectName(u"pushButton")

        self.gridLayout_2.addWidget(self.pushButton, 3, 0, 1, 1)


        self.gridLayout.addWidget(self.frame, 6, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 10, 0, 1, 1)

        self.label = QLabel(choose_model)
        self.label.setObjectName(u"label")
        font1 = QFont()
        font1.setPointSize(11)
        font1.setBold(True)
        self.label.setFont(font1)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.label_2 = QLabel(choose_model)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setWordWrap(True)

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)


        self.retranslateUi(choose_model)

        QMetaObject.connectSlotsByName(choose_model)
    # setupUi

    def retranslateUi(self, choose_model):
        choose_model.setWindowTitle(QCoreApplication.translate("choose_model", u"Form", None))
        self.label_6.setText(QCoreApplication.translate("choose_model", u"Optional model download - you can provide your own models later.", None))
        self.label_5.setText(QCoreApplication.translate("choose_model", u"Default Model", None))
        self.pushButton.setText(QCoreApplication.translate("choose_model", u"Download", None))
        self.label.setText(QCoreApplication.translate("choose_model", u"Stable Diffusion Model Setup", None))
        self.label_2.setText(QCoreApplication.translate("choose_model", u"Choose your default model settings. These can be overriden at any time.", None))
    # retranslateUi

