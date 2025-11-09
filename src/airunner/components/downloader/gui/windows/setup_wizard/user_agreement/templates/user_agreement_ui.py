# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'user_agreement.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QGridLayout, QLabel,
    QScrollArea, QSizePolicy, QWidget)

class Ui_user_agreement(object):
    def setupUi(self, user_agreement):
        if not user_agreement.objectName():
            user_agreement.setObjectName(u"user_agreement")
        user_agreement.resize(400, 526)
        self.gridLayout_2 = QGridLayout(user_agreement)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.scrollArea = QScrollArea(user_agreement)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 366, 1565))
        self.gridLayout = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_2 = QLabel(self.scrollAreaWidgetContents)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setWordWrap(True)

        self.gridLayout.addWidget(self.label_2, 0, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_2.addWidget(self.scrollArea, 1, 0, 1, 1)

        self.label = QLabel(user_agreement)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)

        self.checkBox = QCheckBox(user_agreement)
        self.checkBox.setObjectName(u"checkBox")

        self.gridLayout_2.addWidget(self.checkBox, 2, 0, 1, 1)


        self.retranslateUi(user_agreement)
        self.checkBox.clicked["bool"].connect(user_agreement.agreement_clicked)

        QMetaObject.connectSlotsByName(user_agreement)
    # setupUi

    def retranslateUi(self, user_agreement):
        user_agreement.setWindowTitle(QCoreApplication.translate("user_agreement", u"Form", None))
        self.label_2.setText(QCoreApplication.translate("user_agreement", u"Loading user agreement...", None))
        self.label.setText(QCoreApplication.translate("user_agreement", u"User Agreement", None))
        self.checkBox.setText(QCoreApplication.translate("user_agreement", u"I have read and agree to the terms of the User Agreement", None))
    # retranslateUi

