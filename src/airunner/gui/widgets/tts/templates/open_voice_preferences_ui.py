# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'open_voice_preferences.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QGroupBox,
    QSizePolicy, QSpacerItem, QVBoxLayout, QWidget)

class Ui_open_voice_preferences(object):
    def setupUi(self, open_voice_preferences):
        if not open_voice_preferences.objectName():
            open_voice_preferences.setObjectName(u"open_voice_preferences")
        open_voice_preferences.resize(400, 300)
        self.verticalLayout = QVBoxLayout(open_voice_preferences)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.groupBox = QGroupBox(open_voice_preferences)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout = QGridLayout(self.groupBox)
        self.gridLayout.setObjectName(u"gridLayout")
        self.language_combobox = QComboBox(self.groupBox)
        self.language_combobox.setObjectName(u"language_combobox")

        self.gridLayout.addWidget(self.language_combobox, 0, 0, 1, 1)


        self.verticalLayout.addWidget(self.groupBox)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.retranslateUi(open_voice_preferences)
        self.language_combobox.currentTextChanged.connect(open_voice_preferences.language_changed)

        QMetaObject.connectSlotsByName(open_voice_preferences)
    # setupUi

    def retranslateUi(self, open_voice_preferences):
        self.groupBox.setTitle(QCoreApplication.translate("open_voice_preferences", u"Language", None))
        self.language_combobox.setCurrentText("")
        pass
    # retranslateUi

