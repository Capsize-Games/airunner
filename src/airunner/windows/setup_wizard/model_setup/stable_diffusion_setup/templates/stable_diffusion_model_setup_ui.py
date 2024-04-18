# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'stable_diffusion_model_setup.ui'
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
    QLabel, QPushButton, QSizePolicy, QSpacerItem,
    QWidget)

class Ui_stable_diffusion_model_setup(object):
    def setupUi(self, stable_diffusion_model_setup):
        if not stable_diffusion_model_setup.objectName():
            stable_diffusion_model_setup.setObjectName(u"stable_diffusion_model_setup")
        stable_diffusion_model_setup.resize(447, 533)
        self.gridLayout = QGridLayout(stable_diffusion_model_setup)
        self.gridLayout.setObjectName(u"gridLayout")
        self.frame = QFrame(stable_diffusion_model_setup)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
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


        self.gridLayout.addWidget(self.frame, 9, 0, 1, 1)

        self.line_3 = QFrame(stable_diffusion_model_setup)
        self.line_3.setObjectName(u"line_3")
        self.line_3.setFrameShape(QFrame.Shape.HLine)
        self.line_3.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line_3, 8, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 13, 0, 1, 1)

        self.label_2 = QLabel(stable_diffusion_model_setup)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setWordWrap(True)

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.label = QLabel(stable_diffusion_model_setup)
        self.label.setObjectName(u"label")
        font1 = QFont()
        font1.setPointSize(11)
        font1.setBold(True)
        self.label.setFont(font1)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.comboBox_2 = QComboBox(stable_diffusion_model_setup)
        self.comboBox_2.setObjectName(u"comboBox_2")

        self.gridLayout.addWidget(self.comboBox_2, 7, 0, 1, 1)

        self.comboBox = QComboBox(stable_diffusion_model_setup)
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.setObjectName(u"comboBox")

        self.gridLayout.addWidget(self.comboBox, 4, 0, 1, 1)

        self.line = QFrame(stable_diffusion_model_setup)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 2, 0, 1, 1)

        self.label_3 = QLabel(stable_diffusion_model_setup)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setFont(font)

        self.gridLayout.addWidget(self.label_3, 3, 0, 1, 1)

        self.line_2 = QFrame(stable_diffusion_model_setup)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line_2, 5, 0, 1, 1)

        self.label_4 = QLabel(stable_diffusion_model_setup)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setFont(font)

        self.gridLayout.addWidget(self.label_4, 6, 0, 1, 1)


        self.retranslateUi(stable_diffusion_model_setup)

        QMetaObject.connectSlotsByName(stable_diffusion_model_setup)
    # setupUi

    def retranslateUi(self, stable_diffusion_model_setup):
        stable_diffusion_model_setup.setWindowTitle(QCoreApplication.translate("stable_diffusion_model_setup", u"Form", None))
        self.label_6.setText(QCoreApplication.translate("stable_diffusion_model_setup", u"Optional model download - you can provide your own models later.", None))
        self.label_5.setText(QCoreApplication.translate("stable_diffusion_model_setup", u"Default Model", None))
        self.pushButton.setText(QCoreApplication.translate("stable_diffusion_model_setup", u"Download", None))
        self.label_2.setText(QCoreApplication.translate("stable_diffusion_model_setup", u"Choose your default model settings. These can be overriden at any time.", None))
        self.label.setText(QCoreApplication.translate("stable_diffusion_model_setup", u"Stable Diffusion Model Setup", None))
        self.comboBox.setItemText(0, QCoreApplication.translate("stable_diffusion_model_setup", u"Photography", None))
        self.comboBox.setItemText(1, QCoreApplication.translate("stable_diffusion_model_setup", u"Illustration", None))

        self.label_3.setText(QCoreApplication.translate("stable_diffusion_model_setup", u"Style", None))
        self.label_4.setText(QCoreApplication.translate("stable_diffusion_model_setup", u"Model Version", None))
    # retranslateUi

