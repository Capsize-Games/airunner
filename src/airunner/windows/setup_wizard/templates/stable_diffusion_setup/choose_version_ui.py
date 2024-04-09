# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'choose_version.ui'
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
    QLabel, QSizePolicy, QSpacerItem, QWidget)

class Ui_choose_model_version(object):
    def setupUi(self, choose_model_version):
        if not choose_model_version.objectName():
            choose_model_version.setObjectName(u"choose_model_version")
        choose_model_version.resize(530, 533)
        self.gridLayout = QGridLayout(choose_model_version)
        self.gridLayout.setObjectName(u"gridLayout")
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 10, 0, 1, 1)

        self.label_2 = QLabel(choose_model_version)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setWordWrap(True)

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.label = QLabel(choose_model_version)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.frame_2 = QFrame(choose_model_version)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setFrameShape(QFrame.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Raised)
        self.gridLayout_3 = QGridLayout(self.frame_2)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.label_4 = QLabel(self.frame_2)
        self.label_4.setObjectName(u"label_4")
        font1 = QFont()
        font1.setBold(True)
        self.label_4.setFont(font1)

        self.gridLayout_3.addWidget(self.label_4, 0, 0, 1, 1)

        self.comboBox_2 = QComboBox(self.frame_2)
        self.comboBox_2.setObjectName(u"comboBox_2")

        self.gridLayout_3.addWidget(self.comboBox_2, 1, 0, 1, 1)


        self.gridLayout.addWidget(self.frame_2, 5, 0, 1, 1)

        self.line = QFrame(choose_model_version)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.gridLayout.addWidget(self.line, 2, 0, 1, 1)


        self.retranslateUi(choose_model_version)

        QMetaObject.connectSlotsByName(choose_model_version)
    # setupUi

    def retranslateUi(self, choose_model_version):
        choose_model_version.setWindowTitle(QCoreApplication.translate("choose_model_version", u"Form", None))
        self.label_2.setText(QCoreApplication.translate("choose_model_version", u"Choose your default model settings. These can be overriden at any time.", None))
        self.label.setText(QCoreApplication.translate("choose_model_version", u"Stable Diffusion Model Setup", None))
        self.label_4.setText(QCoreApplication.translate("choose_model_version", u"Model Version", None))
    # retranslateUi

