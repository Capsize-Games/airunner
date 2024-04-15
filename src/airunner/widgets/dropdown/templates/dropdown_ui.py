# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dropdown.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QSizePolicy, QSpacerItem,
    QWidget)

from qfluentwidgets import (CaptionLabel, DropDownPushButton, PushButton)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(228, 74)
        self.gridLayout = QGridLayout(Form)
        self.gridLayout.setObjectName(u"gridLayout")
        self.CaptionLabel = CaptionLabel(Form)
        self.CaptionLabel.setObjectName(u"CaptionLabel")
        font = QFont()
        font.setFamilies([u"Segoe UI"])
        font.setBold(True)
        self.CaptionLabel.setFont(font)

        self.gridLayout.addWidget(self.CaptionLabel, 0, 0, 1, 1)

        self.DropDownPushButton = DropDownPushButton(Form)
        self.DropDownPushButton.setObjectName(u"DropDownPushButton")

        self.gridLayout.addWidget(self.DropDownPushButton, 1, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 2, 0, 1, 1)


        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.CaptionLabel.setText(QCoreApplication.translate("Form", u"Caption label", None))
        self.DropDownPushButton.setText(QCoreApplication.translate("Form", u"Drop down push button", None))
    # retranslateUi

