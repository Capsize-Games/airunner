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

from airunner.widgets.slider.slider_widget import SliderWidget

class Ui_speecht5_preferences(object):
    def setupUi(self, speecht5_preferences):
        if not speecht5_preferences.objectName():
            speecht5_preferences.setObjectName(u"speecht5_preferences")
        speecht5_preferences.resize(512, 787)
        self.gridLayout_7 = QGridLayout(speecht5_preferences)
        self.gridLayout_7.setObjectName(u"gridLayout_7")
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_7.addItem(self.verticalSpacer, 10, 0, 1, 1)

        self.preferences_groupbox = QGroupBox(speecht5_preferences)
        self.preferences_groupbox.setObjectName(u"preferences_groupbox")
        self.preferences_groupbox.setCheckable(False)
        self.gridLayout_8 = QGridLayout(self.preferences_groupbox)
        self.gridLayout_8.setObjectName(u"gridLayout_8")
        self.groupBox_2 = QGroupBox(self.preferences_groupbox)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.gridLayout_3 = QGridLayout(self.groupBox_2)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gender_combobox = QComboBox(self.groupBox_2)
        self.gender_combobox.addItem("")
        self.gender_combobox.addItem("")
        self.gender_combobox.setObjectName(u"gender_combobox")

        self.gridLayout_3.addWidget(self.gender_combobox, 0, 0, 1, 1)


        self.gridLayout_8.addWidget(self.groupBox_2, 1, 0, 1, 1)

        self.groupBox_6 = QGroupBox(self.preferences_groupbox)
        self.groupBox_6.setObjectName(u"groupBox_6")
        self.gridLayout_2 = QGridLayout(self.groupBox_6)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.semantic_temperature = SliderWidget(self.groupBox_6)
        self.semantic_temperature.setObjectName(u"semantic_temperature")
        self.semantic_temperature.setProperty("slider_minimum", 1)
        self.semantic_temperature.setProperty("slider_maximum", 100)
        self.semantic_temperature.setProperty("spinbox_minimum", 0.000000000000000)
        self.semantic_temperature.setProperty("spinbox_maximum", 1.000000000000000)
        self.semantic_temperature.setProperty("display_as_float", True)
        self.semantic_temperature.setProperty("slider_single_step", 1)
        self.semantic_temperature.setProperty("slider_page_step", 10)
        self.semantic_temperature.setProperty("spinbox_single_step", 0.010000000000000)
        self.semantic_temperature.setProperty("spinbox_page_step", 0.100000000000000)

        self.gridLayout_2.addWidget(self.semantic_temperature, 0, 0, 1, 1)


        self.gridLayout_8.addWidget(self.groupBox_6, 4, 0, 1, 1)

        self.groupBox = QGroupBox(self.preferences_groupbox)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout = QGridLayout(self.groupBox)
        self.gridLayout.setObjectName(u"gridLayout")
        self.voice_combobox = QComboBox(self.groupBox)
        self.voice_combobox.setObjectName(u"voice_combobox")

        self.gridLayout.addWidget(self.voice_combobox, 0, 0, 1, 1)


        self.gridLayout_8.addWidget(self.groupBox, 2, 0, 1, 1)

        self.label_3 = QLabel(self.preferences_groupbox)
        self.label_3.setObjectName(u"label_3")
        font = QFont()
        font.setPointSize(9)
        self.label_3.setFont(font)

        self.gridLayout_8.addWidget(self.label_3, 0, 0, 1, 1)

        self.groupBox_5 = QGroupBox(self.preferences_groupbox)
        self.groupBox_5.setObjectName(u"groupBox_5")
        self.gridLayout_6 = QGridLayout(self.groupBox_5)
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.semantic_temperature_3 = SliderWidget(self.groupBox_5)
        self.semantic_temperature_3.setObjectName(u"semantic_temperature_3")
        self.semantic_temperature_3.setProperty("slider_minimum", 1)
        self.semantic_temperature_3.setProperty("slider_maximum", 100)
        self.semantic_temperature_3.setProperty("spinbox_minimum", 0.000000000000000)
        self.semantic_temperature_3.setProperty("spinbox_maximum", 1.000000000000000)
        self.semantic_temperature_3.setProperty("display_as_float", True)
        self.semantic_temperature_3.setProperty("slider_single_step", 1)
        self.semantic_temperature_3.setProperty("slider_page_step", 10)
        self.semantic_temperature_3.setProperty("spinbox_single_step", 0.010000000000000)
        self.semantic_temperature_3.setProperty("spinbox_page_step", 0.100000000000000)

        self.gridLayout_6.addWidget(self.semantic_temperature_3, 0, 0, 1, 1)


        self.gridLayout_8.addWidget(self.groupBox_5, 5, 0, 1, 1)

        self.groupBox_4 = QGroupBox(self.preferences_groupbox)
        self.groupBox_4.setObjectName(u"groupBox_4")
        self.gridLayout_5 = QGridLayout(self.groupBox_4)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.semantic_temperature_2 = SliderWidget(self.groupBox_4)
        self.semantic_temperature_2.setObjectName(u"semantic_temperature_2")
        self.semantic_temperature_2.setProperty("slider_minimum", 1)
        self.semantic_temperature_2.setProperty("slider_maximum", 100)
        self.semantic_temperature_2.setProperty("spinbox_minimum", 0.000000000000000)
        self.semantic_temperature_2.setProperty("spinbox_maximum", 1.000000000000000)
        self.semantic_temperature_2.setProperty("display_as_float", True)
        self.semantic_temperature_2.setProperty("slider_single_step", 1)
        self.semantic_temperature_2.setProperty("slider_page_step", 10)
        self.semantic_temperature_2.setProperty("spinbox_single_step", 0.010000000000000)
        self.semantic_temperature_2.setProperty("spinbox_page_step", 0.100000000000000)

        self.gridLayout_5.addWidget(self.semantic_temperature_2, 0, 0, 1, 1)


        self.gridLayout_8.addWidget(self.groupBox_4, 3, 0, 1, 1)


        self.gridLayout_7.addWidget(self.preferences_groupbox, 0, 0, 1, 1)


        self.retranslateUi(speecht5_preferences)
        self.voice_combobox.currentTextChanged.connect(speecht5_preferences.voice_changed)
        self.gender_combobox.currentTextChanged.connect(speecht5_preferences.gender_changed)

        QMetaObject.connectSlotsByName(speecht5_preferences)
    # setupUi

    def retranslateUi(self, speecht5_preferences):
        speecht5_preferences.setWindowTitle(QCoreApplication.translate("speecht5_preferences", u"Form", None))
        self.preferences_groupbox.setTitle(QCoreApplication.translate("speecht5_preferences", u"SpeechT5", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("speecht5_preferences", u"Gender", None))
        self.gender_combobox.setItemText(0, QCoreApplication.translate("speecht5_preferences", u"Male", None))
        self.gender_combobox.setItemText(1, QCoreApplication.translate("speecht5_preferences", u"Female", None))

        self.groupBox_6.setTitle(QCoreApplication.translate("speecht5_preferences", u"Pitch", None))
        self.semantic_temperature.setProperty("settings_property", QCoreApplication.translate("speecht5_preferences", u"tts_settings.spd.pitch", None))
        self.semantic_temperature.setProperty("slider_callback", QCoreApplication.translate("speecht5_preferences", u"handle_value_change", None))
        self.groupBox.setTitle(QCoreApplication.translate("speecht5_preferences", u"Voice", None))
        self.label_3.setText(QCoreApplication.translate("speecht5_preferences", u"Robotic, fast, no VRAM usage", None))
        self.groupBox_5.setTitle(QCoreApplication.translate("speecht5_preferences", u"Volume", None))
        self.semantic_temperature_3.setProperty("settings_property", QCoreApplication.translate("speecht5_preferences", u"tts_settings.spd.volume", None))
        self.semantic_temperature_3.setProperty("slider_callback", QCoreApplication.translate("speecht5_preferences", u"handle_value_change", None))
        self.groupBox_4.setTitle(QCoreApplication.translate("speecht5_preferences", u"Rate", None))
        self.semantic_temperature_2.setProperty("settings_property", QCoreApplication.translate("speecht5_preferences", u"tts_settings.spd.rate", None))
        self.semantic_temperature_2.setProperty("slider_callback", QCoreApplication.translate("speecht5_preferences", u"handle_value_change", None))
    # retranslateUi

