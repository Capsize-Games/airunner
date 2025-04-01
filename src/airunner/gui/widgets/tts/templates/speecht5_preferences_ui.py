# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'speecht5_preferences.ui'
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
    QLabel, QSizePolicy, QSpacerItem, QWidget)

from airunner.gui.widgets.slider.slider_widget import SliderWidget

class Ui_speecht5_preferences(object):
    def setupUi(self, speecht5_preferences):
        if not speecht5_preferences.objectName():
            speecht5_preferences.setObjectName(u"speecht5_preferences")
        speecht5_preferences.resize(512, 787)
        self.gridLayout_7 = QGridLayout(speecht5_preferences)
        self.gridLayout_7.setSpacing(0)
        self.gridLayout_7.setObjectName(u"gridLayout_7")
        self.gridLayout_7.setContentsMargins(0, 0, 0, 0)
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_7.addItem(self.verticalSpacer, 10, 0, 1, 1)

        self.preferences_groupbox = QGroupBox(speecht5_preferences)
        self.preferences_groupbox.setObjectName(u"preferences_groupbox")
        self.preferences_groupbox.setCheckable(False)
        self.gridLayout_8 = QGridLayout(self.preferences_groupbox)
        self.gridLayout_8.setObjectName(u"gridLayout_8")
        self.gridLayout_8.setHorizontalSpacing(0)
        self.gridLayout_8.setVerticalSpacing(10)
        self.gridLayout_8.setContentsMargins(10, 10, 10, 10)
        self.label_3 = QLabel(self.preferences_groupbox)
        self.label_3.setObjectName(u"label_3")
        font = QFont()
        font.setPointSize(9)
        self.label_3.setFont(font)

        self.gridLayout_8.addWidget(self.label_3, 0, 0, 1, 1)

        self.pitch = SliderWidget(self.preferences_groupbox)
        self.pitch.setObjectName(u"pitch")
        self.pitch.setProperty("slider_minimum", 1)
        self.pitch.setProperty("slider_maximum", 100)
        self.pitch.setProperty("spinbox_minimum", 0.000000000000000)
        self.pitch.setProperty("spinbox_maximum", 1.000000000000000)
        self.pitch.setProperty("display_as_float", True)
        self.pitch.setProperty("slider_single_step", 1)
        self.pitch.setProperty("slider_page_step", 10)
        self.pitch.setProperty("spinbox_single_step", 0.010000000000000)
        self.pitch.setProperty("spinbox_page_step", 0.100000000000000)

        self.gridLayout_8.addWidget(self.pitch, 2, 0, 1, 1)

        self.groupBox = QGroupBox(self.preferences_groupbox)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout = QGridLayout(self.groupBox)
        self.gridLayout.setObjectName(u"gridLayout")
        self.voice = QComboBox(self.groupBox)
        self.voice.addItem("")
        self.voice.addItem("")
        self.voice.addItem("")
        self.voice.addItem("")
        self.voice.addItem("")
        self.voice.addItem("")
        self.voice.addItem("")
        self.voice.setObjectName(u"voice")

        self.gridLayout.addWidget(self.voice, 0, 0, 1, 1)


        self.gridLayout_8.addWidget(self.groupBox, 1, 0, 1, 1)


        self.gridLayout_7.addWidget(self.preferences_groupbox, 0, 0, 1, 1)


        self.retranslateUi(speecht5_preferences)
        self.voice.currentTextChanged.connect(speecht5_preferences.voice_changed)

        QMetaObject.connectSlotsByName(speecht5_preferences)
    # setupUi

    def retranslateUi(self, speecht5_preferences):
        speecht5_preferences.setWindowTitle(QCoreApplication.translate("speecht5_preferences", u"Form", None))
        self.preferences_groupbox.setTitle(QCoreApplication.translate("speecht5_preferences", u"SpeechT5", None))
        self.label_3.setText(QCoreApplication.translate("speecht5_preferences", u"More realistic. Slower. Uses VRAM", None))
        self.pitch.setProperty("settings_property", QCoreApplication.translate("speecht5_preferences", u"speech_t5_settings.pitch", None))
        self.pitch.setProperty("label_text", QCoreApplication.translate("speecht5_preferences", u"Pitch", None))
        self.groupBox.setTitle(QCoreApplication.translate("speecht5_preferences", u"Voice Style", None))
        self.voice.setItemText(0, QCoreApplication.translate("speecht5_preferences", u"US Male", None))
        self.voice.setItemText(1, QCoreApplication.translate("speecht5_preferences", u"US Male 2", None))
        self.voice.setItemText(2, QCoreApplication.translate("speecht5_preferences", u"US Female", None))
        self.voice.setItemText(3, QCoreApplication.translate("speecht5_preferences", u"US Female 2", None))
        self.voice.setItemText(4, QCoreApplication.translate("speecht5_preferences", u"Canadian Male", None))
        self.voice.setItemText(5, QCoreApplication.translate("speecht5_preferences", u"Scottish Male", None))
        self.voice.setItemText(6, QCoreApplication.translate("speecht5_preferences", u"Indian Male", None))

    # retranslateUi

