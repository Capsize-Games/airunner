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
from PySide6.QtWidgets import (QApplication, QComboBox, QSizePolicy, QSlider,
    QVBoxLayout, QWidget)

class Ui_open_voice_preferences(object):
    def setupUi(self, open_voice_preferences):
        if not open_voice_preferences.objectName():
            open_voice_preferences.setObjectName(u"open_voice_preferences")
        open_voice_preferences.resize(400, 300)
        self.verticalLayout = QVBoxLayout(open_voice_preferences)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.language_combobox = QComboBox(open_voice_preferences)
        self.language_combobox.setObjectName(u"language_combobox")

        self.verticalLayout.addWidget(self.language_combobox)

        self.speed_slider = QSlider(open_voice_preferences)
        self.speed_slider.setObjectName(u"speed_slider")
        self.speed_slider.setOrientation(Qt.Horizontal)
        self.speed_slider.setMinimum(50)
        self.speed_slider.setMaximum(200)
        self.speed_slider.setValue(100)

        self.verticalLayout.addWidget(self.speed_slider)

        self.tone_color_combobox = QComboBox(open_voice_preferences)
        self.tone_color_combobox.setObjectName(u"tone_color_combobox")

        self.verticalLayout.addWidget(self.tone_color_combobox)

        self.pitch_slider = QSlider(open_voice_preferences)
        self.pitch_slider.setObjectName(u"pitch_slider")
        self.pitch_slider.setOrientation(Qt.Horizontal)
        self.pitch_slider.setMinimum(50)
        self.pitch_slider.setMaximum(200)
        self.pitch_slider.setValue(100)

        self.verticalLayout.addWidget(self.pitch_slider)

        self.volume_slider = QSlider(open_voice_preferences)
        self.volume_slider.setObjectName(u"volume_slider")
        self.volume_slider.setOrientation(Qt.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(100)

        self.verticalLayout.addWidget(self.volume_slider)

        self.voice_combobox = QComboBox(open_voice_preferences)
        self.voice_combobox.setObjectName(u"voice_combobox")

        self.verticalLayout.addWidget(self.voice_combobox)


        self.retranslateUi(open_voice_preferences)

        QMetaObject.connectSlotsByName(open_voice_preferences)
    # setupUi

    def retranslateUi(self, open_voice_preferences):
        self.language_combobox.setCurrentText(QCoreApplication.translate("open_voice_preferences", u"EN_NEWEST", None))
        self.tone_color_combobox.setCurrentText(QCoreApplication.translate("open_voice_preferences", u"default", None))
        self.voice_combobox.setCurrentText(QCoreApplication.translate("open_voice_preferences", u"default", None))
        pass
    # retranslateUi

