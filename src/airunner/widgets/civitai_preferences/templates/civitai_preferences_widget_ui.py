# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'civitai_preferences_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QGroupBox, QLineEdit,
    QSizePolicy, QSpacerItem, QWidget)

class Ui_civitai_preferences(object):
    def setupUi(self, civitai_preferences):
        if not civitai_preferences.objectName():
            civitai_preferences.setObjectName(u"civitai_preferences")
        civitai_preferences.resize(400, 275)
        self.gridLayout_2 = QGridLayout(civitai_preferences)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.groupBox = QGroupBox(civitai_preferences)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout = QGridLayout(self.groupBox)
        self.gridLayout.setObjectName(u"gridLayout")
        self.api_key = QLineEdit(self.groupBox)
        self.api_key.setObjectName(u"api_key")

        self.gridLayout.addWidget(self.api_key, 0, 0, 1, 1)


        self.gridLayout_2.addWidget(self.groupBox, 0, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer, 1, 0, 1, 1)


        self.retranslateUi(civitai_preferences)
        self.api_key.textChanged.connect(civitai_preferences.on_text_changed)

        QMetaObject.connectSlotsByName(civitai_preferences)
    # setupUi

    def retranslateUi(self, civitai_preferences):
        civitai_preferences.setWindowTitle(QCoreApplication.translate("civitai_preferences", u"Form", None))
        self.groupBox.setTitle(QCoreApplication.translate("civitai_preferences", u"API Key", None))
    # retranslateUi

