# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tts_preferences.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame,
    QGridLayout, QGroupBox, QScrollArea, QSizePolicy,
    QSpacerItem, QWidget)

from airunner.widgets.tts.espeak_preferences_widget import ESpeakPreferencesWidget
from airunner.widgets.tts.speecht5_preferences_widget import SpeechT5PreferencesWidget

class Ui_tts_preferences(object):
    def setupUi(self, tts_preferences):
        if not tts_preferences.objectName():
            tts_preferences.setObjectName(u"tts_preferences")
        tts_preferences.resize(512, 576)
        self.gridLayout_2 = QGridLayout(tts_preferences)
        self.gridLayout_2.setSpacing(0)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.scrollArea = QScrollArea(tts_preferences)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 510, 574))
        self.gridLayout = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout.setObjectName(u"gridLayout")
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 5, 0, 1, 1)

        self.espeak_preferences = ESpeakPreferencesWidget(self.scrollAreaWidgetContents)
        self.espeak_preferences.setObjectName(u"espeak_preferences")

        self.gridLayout.addWidget(self.espeak_preferences, 3, 0, 1, 1)

        self.speecht5_preferences = SpeechT5PreferencesWidget(self.scrollAreaWidgetContents)
        self.speecht5_preferences.setObjectName(u"speecht5_preferences")

        self.gridLayout.addWidget(self.speecht5_preferences, 4, 0, 1, 1)

        self.enable_tts = QCheckBox(self.scrollAreaWidgetContents)
        self.enable_tts.setObjectName(u"enable_tts")

        self.gridLayout.addWidget(self.enable_tts, 0, 0, 1, 1)

        self.groupBox_7 = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_7.setObjectName(u"groupBox_7")
        self.gridLayout_9 = QGridLayout(self.groupBox_7)
        self.gridLayout_9.setObjectName(u"gridLayout_9")
        self.model_combobox = QComboBox(self.groupBox_7)
        self.model_combobox.setObjectName(u"model_combobox")

        self.gridLayout_9.addWidget(self.model_combobox, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_7, 2, 0, 1, 1)

        self.line = QFrame(self.scrollAreaWidgetContents)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 1, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_2.addWidget(self.scrollArea, 0, 0, 1, 1)


        self.retranslateUi(tts_preferences)
        self.enable_tts.toggled.connect(tts_preferences.enable_tts_changed)
        self.model_combobox.currentTextChanged.connect(tts_preferences.model_changed)

        QMetaObject.connectSlotsByName(tts_preferences)
    # setupUi

    def retranslateUi(self, tts_preferences):
        tts_preferences.setWindowTitle(QCoreApplication.translate("tts_preferences", u"Form", None))
        self.enable_tts.setText(QCoreApplication.translate("tts_preferences", u"Enable Text to Speech", None))
        self.groupBox_7.setTitle(QCoreApplication.translate("tts_preferences", u"Model", None))
    # retranslateUi

