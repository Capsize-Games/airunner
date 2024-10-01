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
from PySide6.QtWidgets import (QApplication, QGridLayout, QGroupBox, QLabel,
    QSizePolicy, QSpacerItem, QWidget)

from airunner.widgets.slider.slider_widget import SliderWidget

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

        self.label_3 = QLabel(self.preferences_groupbox)
        self.label_3.setObjectName(u"label_3")
        font = QFont()
        font.setPointSize(9)
        self.label_3.setFont(font)

        self.gridLayout_8.addWidget(self.label_3, 0, 0, 1, 1)

        self.volume = SliderWidget(self.preferences_groupbox)
        self.volume.setObjectName(u"volume")
        self.volume.setProperty("slider_minimum", 1)
        self.volume.setProperty("slider_maximum", 100)
        self.volume.setProperty("spinbox_minimum", 0.000000000000000)
        self.volume.setProperty("spinbox_maximum", 1.000000000000000)
        self.volume.setProperty("display_as_float", True)
        self.volume.setProperty("slider_single_step", 1)
        self.volume.setProperty("slider_page_step", 10)
        self.volume.setProperty("spinbox_single_step", 0.010000000000000)
        self.volume.setProperty("spinbox_page_step", 0.100000000000000)

        self.gridLayout_8.addWidget(self.volume, 3, 0, 1, 1)

        self.rate = SliderWidget(self.preferences_groupbox)
        self.rate.setObjectName(u"rate")
        self.rate.setProperty("slider_minimum", 1)
        self.rate.setProperty("slider_maximum", 100)
        self.rate.setProperty("spinbox_minimum", 0.000000000000000)
        self.rate.setProperty("spinbox_maximum", 1.000000000000000)
        self.rate.setProperty("display_as_float", True)
        self.rate.setProperty("slider_single_step", 1)
        self.rate.setProperty("slider_page_step", 10)
        self.rate.setProperty("spinbox_single_step", 0.010000000000000)
        self.rate.setProperty("spinbox_page_step", 0.100000000000000)

        self.gridLayout_8.addWidget(self.rate, 1, 0, 1, 1)


        self.gridLayout_7.addWidget(self.preferences_groupbox, 0, 0, 1, 1)


        self.retranslateUi(speecht5_preferences)

        QMetaObject.connectSlotsByName(speecht5_preferences)
    # setupUi

    def retranslateUi(self, speecht5_preferences):
        speecht5_preferences.setWindowTitle(QCoreApplication.translate("speecht5_preferences", u"Form", None))
        self.preferences_groupbox.setTitle(QCoreApplication.translate("speecht5_preferences", u"SpeechT5", None))
        self.pitch.setProperty("settings_property", QCoreApplication.translate("speecht5_preferences", u"speech_t5_settings.pitch", None))
        self.pitch.setProperty("slider_callback", QCoreApplication.translate("speecht5_preferences", u"handle_value_change", None))
        self.pitch.setProperty("label_text", QCoreApplication.translate("speecht5_preferences", u"Pitch", None))
        self.label_3.setText(QCoreApplication.translate("speecht5_preferences", u"More realistic. Slower. Uses VRAM", None))
        self.volume.setProperty("settings_property", QCoreApplication.translate("speecht5_preferences", u"speech_t5_settings.volume", None))
        self.volume.setProperty("slider_callback", QCoreApplication.translate("speecht5_preferences", u"handle_value_change", None))
        self.volume.setProperty("label_text", QCoreApplication.translate("speecht5_preferences", u"Volume", None))
        self.rate.setProperty("settings_property", QCoreApplication.translate("speecht5_preferences", u"speech_t5_settings.rate", None))
        self.rate.setProperty("slider_callback", QCoreApplication.translate("speecht5_preferences", u"handle_value_change", None))
        self.rate.setProperty("label_text", QCoreApplication.translate("speecht5_preferences", u"Rate", None))
    # retranslateUi

