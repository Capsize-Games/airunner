# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'openrouter_settings.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QGridLayout, QGroupBox,
    QLineEdit, QSizePolicy, QSpacerItem, QWidget)

class Ui_openrouter_settings_widget(object):
    def setupUi(self, openrouter_settings_widget):
        if not openrouter_settings_widget.objectName():
            openrouter_settings_widget.setObjectName(u"openrouter_settings_widget")
        openrouter_settings_widget.resize(400, 300)
        self.gridLayout_2 = QGridLayout(openrouter_settings_widget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.allow = QCheckBox(openrouter_settings_widget)
        self.allow.setObjectName(u"allow")

        self.gridLayout_2.addWidget(self.allow, 0, 0, 1, 1)

        self.groupBox = QGroupBox(openrouter_settings_widget)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout = QGridLayout(self.groupBox)
        self.gridLayout.setObjectName(u"gridLayout")
        self.api_key = QLineEdit(self.groupBox)
        self.api_key.setObjectName(u"api_key")

        self.gridLayout.addWidget(self.api_key, 0, 0, 1, 1)


        self.gridLayout_2.addWidget(self.groupBox, 1, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer, 2, 0, 1, 1)


        self.retranslateUi(openrouter_settings_widget)
        self.allow.toggled.connect(openrouter_settings_widget.on_allow_toggled)
        self.api_key.textChanged.connect(openrouter_settings_widget.on_api_key_textChanged)

        QMetaObject.connectSlotsByName(openrouter_settings_widget)
    # setupUi

    def retranslateUi(self, openrouter_settings_widget):
        openrouter_settings_widget.setWindowTitle(QCoreApplication.translate("openrouter_settings_widget", u"Form", None))
        self.allow.setText(QCoreApplication.translate("openrouter_settings_widget", u"Allow OpenRouter connection", None))
        self.groupBox.setTitle(QCoreApplication.translate("openrouter_settings_widget", u"OpenRouter API key", None))
    # retranslateUi

