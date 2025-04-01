# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'api_token.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QSizePolicy, QSpacerItem,
    QWidget)

class Ui_api_token(object):
    def setupUi(self, api_token):
        if not api_token.objectName():
            api_token.setObjectName(u"api_token")
        api_token.resize(400, 409)
        self.gridLayout = QGridLayout(api_token)
        self.gridLayout.setObjectName(u"gridLayout")
        self.verticalSpacer = QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 9, 0, 1, 1)

        self.groupBox_2 = QGroupBox(api_token)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.gridLayout_3 = QGridLayout(self.groupBox_2)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.hf_api_key_writetoken = QLineEdit(self.groupBox_2)
        self.hf_api_key_writetoken.setObjectName(u"hf_api_key_writetoken")

        self.gridLayout_3.addWidget(self.hf_api_key_writetoken, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_2, 6, 0, 1, 1)

        self.label_3 = QLabel(api_token)
        self.label_3.setObjectName(u"label_3")
        font = QFont()
        font.setBold(True)
        self.label_3.setFont(font)

        self.gridLayout.addWidget(self.label_3, 0, 0, 1, 1)

        self.line = QFrame(api_token)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 4, 0, 1, 1)

        self.label_2 = QLabel(api_token)
        self.label_2.setObjectName(u"label_2")
        font1 = QFont()
        font1.setPointSize(9)
        self.label_2.setFont(font1)
        self.label_2.setWordWrap(True)

        self.gridLayout.addWidget(self.label_2, 3, 0, 1, 1)

        self.groupBox = QGroupBox(api_token)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout_2 = QGridLayout(self.groupBox)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.hf_api_key_text_generation = QLineEdit(self.groupBox)
        self.hf_api_key_text_generation.setObjectName(u"hf_api_key_text_generation")

        self.gridLayout_2.addWidget(self.hf_api_key_text_generation, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox, 5, 0, 1, 1)

        self.label = QLabel(api_token)
        self.label.setObjectName(u"label")
        self.label.setFont(font1)
        self.label.setWordWrap(True)

        self.gridLayout.addWidget(self.label, 2, 0, 1, 1)

        self.line_2 = QFrame(api_token)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line_2, 1, 0, 1, 1)


        self.retranslateUi(api_token)
        self.hf_api_key_text_generation.textEdited.connect(api_token.action_text_edited_api_key)
        self.hf_api_key_writetoken.textEdited.connect(api_token.action_text_edited_writekey)

        QMetaObject.connectSlotsByName(api_token)
    # setupUi

    def retranslateUi(self, api_token):
        api_token.setWindowTitle(QCoreApplication.translate("api_token", u"Form", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("api_token", u"Write token", None))
        self.label_3.setText(QCoreApplication.translate("api_token", u"Huggingface Access Tokens", None))
        self.label_2.setText(QCoreApplication.translate("api_token", u"https://huggingface.co/settings/tokens", None))
        self.groupBox.setTitle(QCoreApplication.translate("api_token", u"Read token", None))
        self.label.setText(QCoreApplication.translate("api_token", u"Get your Huggingface read API token by creating an account on huggingface.co then navigating to", None))
    # retranslateUi

