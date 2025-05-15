# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'espeak_preferences.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QGroupBox,
    QLabel, QSizePolicy, QSpacerItem, QWidget)

from airunner.gui.widgets.slider.slider_widget import SliderWidget

class Ui_espeak_preferences(object):
    def setupUi(self, espeak_preferences):
        if not espeak_preferences.objectName():
            espeak_preferences.setObjectName(u"espeak_preferences")
        espeak_preferences.resize(512, 807)
        self.gridLayout_7 = QGridLayout(espeak_preferences)
        self.gridLayout_7.setSpacing(0)
        self.gridLayout_7.setObjectName(u"gridLayout_7")
        self.gridLayout_7.setContentsMargins(0, 0, 0, 0)
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_7.addItem(self.verticalSpacer, 10, 0, 1, 1)

        self.espeak = QGroupBox(espeak_preferences)
        self.espeak.setObjectName(u"espeak")
        self.espeak.setCheckable(False)
        self.gridLayout_8 = QGridLayout(self.espeak)
        self.gridLayout_8.setObjectName(u"gridLayout_8")
        self.gridLayout_8.setHorizontalSpacing(0)
        self.gridLayout_8.setVerticalSpacing(10)
        self.gridLayout_8.setContentsMargins(10, 10, 10, 10)
        self.pitch = SliderWidget(self.espeak)
        self.pitch.setObjectName(u"pitch")
        self.pitch.setProperty(u"slider_minimum", 1)
        self.pitch.setProperty(u"slider_maximum", 100)
        self.pitch.setProperty(u"spinbox_minimum", 0.000000000000000)
        self.pitch.setProperty(u"spinbox_maximum", 1.000000000000000)
        self.pitch.setProperty(u"display_as_float", True)
        self.pitch.setProperty(u"slider_single_step", 1)
        self.pitch.setProperty(u"slider_page_step", 10)
        self.pitch.setProperty(u"spinbox_single_step", 0.010000000000000)
        self.pitch.setProperty(u"spinbox_page_step", 0.100000000000000)

        self.gridLayout_8.addWidget(self.pitch, 4, 0, 1, 1)

        self.groupBox_2 = QGroupBox(self.espeak)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.gridLayout_3 = QGridLayout(self.groupBox_2)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gender_combobox = QComboBox(self.groupBox_2)
        self.gender_combobox.addItem("")
        self.gender_combobox.addItem("")
        self.gender_combobox.setObjectName(u"gender_combobox")

        self.gridLayout_3.addWidget(self.gender_combobox, 0, 0, 1, 1)


        self.gridLayout_8.addWidget(self.groupBox_2, 1, 0, 1, 1)

        self.label_3 = QLabel(self.espeak)
        self.label_3.setObjectName(u"label_3")
        font = QFont()
        font.setPointSize(9)
        self.label_3.setFont(font)

        self.gridLayout_8.addWidget(self.label_3, 0, 0, 1, 1)

        self.groupBox = QGroupBox(self.espeak)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout = QGridLayout(self.groupBox)
        self.gridLayout.setObjectName(u"gridLayout")
        self.voice_combobox = QComboBox(self.groupBox)
        self.voice_combobox.setObjectName(u"voice_combobox")

        self.gridLayout.addWidget(self.voice_combobox, 0, 0, 1, 1)


        self.gridLayout_8.addWidget(self.groupBox, 2, 0, 1, 1)

        self.volume = SliderWidget(self.espeak)
        self.volume.setObjectName(u"volume")
        self.volume.setProperty(u"slider_minimum", 1)
        self.volume.setProperty(u"slider_maximum", 100)
        self.volume.setProperty(u"spinbox_minimum", 0.000000000000000)
        self.volume.setProperty(u"spinbox_maximum", 1.000000000000000)
        self.volume.setProperty(u"display_as_float", True)
        self.volume.setProperty(u"slider_single_step", 1)
        self.volume.setProperty(u"slider_page_step", 10)
        self.volume.setProperty(u"spinbox_single_step", 0.010000000000000)
        self.volume.setProperty(u"spinbox_page_step", 0.100000000000000)

        self.gridLayout_8.addWidget(self.volume, 5, 0, 1, 1)

        self.rate = SliderWidget(self.espeak)
        self.rate.setObjectName(u"rate")
        self.rate.setProperty(u"slider_minimum", 0)
        self.rate.setProperty(u"slider_maximum", 300)
        self.rate.setProperty(u"spinbox_minimum", 0.000000000000000)
        self.rate.setProperty(u"spinbox_maximum", 3.000000000000000)
        self.rate.setProperty(u"display_as_float", True)
        self.rate.setProperty(u"slider_single_step", 1)
        self.rate.setProperty(u"slider_page_step", 10)
        self.rate.setProperty(u"spinbox_single_step", 0.010000000000000)
        self.rate.setProperty(u"spinbox_page_step", 0.100000000000000)

        self.gridLayout_8.addWidget(self.rate, 3, 0, 1, 1)


        self.gridLayout_7.addWidget(self.espeak, 0, 0, 1, 1)


        self.retranslateUi(espeak_preferences)
        self.voice_combobox.currentTextChanged.connect(espeak_preferences.voice_changed)
        self.gender_combobox.currentTextChanged.connect(espeak_preferences.gender_changed)

        QMetaObject.connectSlotsByName(espeak_preferences)
    # setupUi

    def retranslateUi(self, espeak_preferences):
        espeak_preferences.setWindowTitle(QCoreApplication.translate("espeak_preferences", u"Form", None))
        self.espeak.setTitle(QCoreApplication.translate("espeak_preferences", u"Espeak", None))
        self.pitch.setProperty(u"settings_property", QCoreApplication.translate("espeak_preferences", u"espeak_settings.pitch", None))
        self.pitch.setProperty(u"label_text", QCoreApplication.translate("espeak_preferences", u"Pitch", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("espeak_preferences", u"Gender", None))
        self.gender_combobox.setItemText(0, QCoreApplication.translate("espeak_preferences", u"Male", None))
        self.gender_combobox.setItemText(1, QCoreApplication.translate("espeak_preferences", u"Female", None))

        self.label_3.setText(QCoreApplication.translate("espeak_preferences", u"Robotic, fast, no VRAM usage", None))
        self.groupBox.setTitle(QCoreApplication.translate("espeak_preferences", u"Language", None))
        self.volume.setProperty(u"settings_property", QCoreApplication.translate("espeak_preferences", u"espeak_settings.volume", None))
        self.volume.setProperty(u"label_text", QCoreApplication.translate("espeak_preferences", u"Volume", None))
        self.rate.setProperty(u"settings_property", QCoreApplication.translate("espeak_preferences", u"espeak_settings.rate", None))
        self.rate.setProperty(u"label_text", QCoreApplication.translate("espeak_preferences", u"Rate", None))
    # retranslateUi

