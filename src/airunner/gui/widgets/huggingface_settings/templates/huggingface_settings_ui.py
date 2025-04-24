# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'huggingface_settings.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QGridLayout, QGroupBox,
    QLineEdit, QSizePolicy, QSpacerItem, QWidget)

class Ui_huggingface_settings_widget(object):
    def setupUi(self, huggingface_settings_widget):
        if not huggingface_settings_widget.objectName():
            huggingface_settings_widget.setObjectName(u"huggingface_settings_widget")
        huggingface_settings_widget.resize(400, 300)
        self.gridLayout_2 = QGridLayout(huggingface_settings_widget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.checkBox = QCheckBox(huggingface_settings_widget)
        self.checkBox.setObjectName(u"checkBox")

        self.gridLayout_2.addWidget(self.checkBox, 0, 0, 1, 1)

        self.groupBox = QGroupBox(huggingface_settings_widget)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout = QGridLayout(self.groupBox)
        self.gridLayout.setObjectName(u"gridLayout")
        self.lineEdit = QLineEdit(self.groupBox)
        self.lineEdit.setObjectName(u"lineEdit")

        self.gridLayout.addWidget(self.lineEdit, 0, 0, 1, 1)


        self.gridLayout_2.addWidget(self.groupBox, 1, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer, 2, 0, 1, 1)


        self.retranslateUi(huggingface_settings_widget)
        self.checkBox.toggled.connect(huggingface_settings_widget.on_toggle_allow_huggingface)
        self.lineEdit.textChanged.connect(huggingface_settings_widget.on_huggingface_api_change)

        QMetaObject.connectSlotsByName(huggingface_settings_widget)
    # setupUi

    def retranslateUi(self, huggingface_settings_widget):
        huggingface_settings_widget.setWindowTitle(QCoreApplication.translate("huggingface_settings_widget", u"Form", None))
        self.checkBox.setText(QCoreApplication.translate("huggingface_settings_widget", u"Allow Huggingface connection", None))
        self.groupBox.setTitle(QCoreApplication.translate("huggingface_settings_widget", u"Huggingface Read API key", None))
    # retranslateUi

