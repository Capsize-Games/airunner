# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'bark_preferences.ui'
##
## Created by: Qt User Interface Compiler version 6.6.2
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

class Ui_bark_preferences(object):
    def setupUi(self, bark_preferences):
        if not bark_preferences.objectName():
            bark_preferences.setObjectName(u"bark_preferences")
        bark_preferences.resize(512, 787)
        self.gridLayout_7 = QGridLayout(bark_preferences)
        self.gridLayout_7.setObjectName(u"gridLayout_7")
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_7.addItem(self.verticalSpacer, 10, 0, 1, 1)

        self.use_bark = QGroupBox(bark_preferences)
        self.use_bark.setObjectName(u"use_bark")
        self.use_bark.setCheckable(False)
        self.gridLayout_8 = QGridLayout(self.use_bark)
        self.gridLayout_8.setObjectName(u"gridLayout_8")
        self.groupBox_6 = QGroupBox(self.use_bark)
        self.groupBox_6.setObjectName(u"groupBox_6")
        self.gridLayout_2 = QGridLayout(self.groupBox_6)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.coarse_temperature = SliderWidget(self.groupBox_6)
        self.coarse_temperature.setObjectName(u"coarse_temperature")
        self.coarse_temperature.setProperty("slider_minimum", 1)
        self.coarse_temperature.setProperty("slider_maximum", 100)
        self.coarse_temperature.setProperty("spinbox_minimum", 0.000000000000000)
        self.coarse_temperature.setProperty("spinbox_maximum", 1.000000000000000)
        self.coarse_temperature.setProperty("display_as_float", True)
        self.coarse_temperature.setProperty("slider_single_step", 1)
        self.coarse_temperature.setProperty("slider_page_step", 10)
        self.coarse_temperature.setProperty("spinbox_single_step", 0.010000000000000)
        self.coarse_temperature.setProperty("spinbox_page_step", 0.100000000000000)

        self.gridLayout_2.addWidget(self.coarse_temperature, 0, 0, 1, 1)


        self.gridLayout_8.addWidget(self.groupBox_6, 5, 0, 1, 1)

        self.groupBox = QGroupBox(self.use_bark)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout = QGridLayout(self.groupBox)
        self.gridLayout.setObjectName(u"gridLayout")
        self.voice_combobox = QComboBox(self.groupBox)
        self.voice_combobox.setObjectName(u"voice_combobox")

        self.gridLayout.addWidget(self.voice_combobox, 0, 0, 1, 1)


        self.gridLayout_8.addWidget(self.groupBox, 2, 0, 1, 1)

        self.groupBox_5 = QGroupBox(self.use_bark)
        self.groupBox_5.setObjectName(u"groupBox_5")
        self.gridLayout_6 = QGridLayout(self.groupBox_5)
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.semantic_temperature = SliderWidget(self.groupBox_5)
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

        self.gridLayout_6.addWidget(self.semantic_temperature, 0, 0, 1, 1)


        self.gridLayout_8.addWidget(self.groupBox_5, 6, 0, 1, 1)

        self.groupBox_2 = QGroupBox(self.use_bark)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.gridLayout_3 = QGridLayout(self.groupBox_2)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gender_combobox = QComboBox(self.groupBox_2)
        self.gender_combobox.addItem("")
        self.gender_combobox.addItem("")
        self.gender_combobox.setObjectName(u"gender_combobox")

        self.gridLayout_3.addWidget(self.gender_combobox, 0, 0, 1, 1)


        self.gridLayout_8.addWidget(self.groupBox_2, 1, 0, 1, 1)

        self.label_3 = QLabel(self.use_bark)
        self.label_3.setObjectName(u"label_3")
        font = QFont()
        font.setPointSize(9)
        self.label_3.setFont(font)

        self.gridLayout_8.addWidget(self.label_3, 0, 0, 1, 1)

        self.groupBox_4 = QGroupBox(self.use_bark)
        self.groupBox_4.setObjectName(u"groupBox_4")
        self.gridLayout_5 = QGridLayout(self.groupBox_4)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.fine_temperature = SliderWidget(self.groupBox_4)
        self.fine_temperature.setObjectName(u"fine_temperature")
        self.fine_temperature.setProperty("slider_minimum", 1)
        self.fine_temperature.setProperty("slider_maximum", 100)
        self.fine_temperature.setProperty("spinbox_minimum", 0.000000000000000)
        self.fine_temperature.setProperty("spinbox_maximum", 1.000000000000000)
        self.fine_temperature.setProperty("display_as_float", True)
        self.fine_temperature.setProperty("slider_single_step", 1)
        self.fine_temperature.setProperty("slider_page_step", 10)
        self.fine_temperature.setProperty("spinbox_single_step", 0.010000000000000)
        self.fine_temperature.setProperty("spinbox_page_step", 0.100000000000000)

        self.gridLayout_5.addWidget(self.fine_temperature, 0, 0, 1, 1)


        self.gridLayout_8.addWidget(self.groupBox_4, 4, 0, 1, 1)

        self.groupBox_3 = QGroupBox(self.use_bark)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.groupBox_3.setCheckable(True)
        self.gridLayout_4 = QGridLayout(self.groupBox_3)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.language_combobox = QComboBox(self.groupBox_3)
        self.language_combobox.setObjectName(u"language_combobox")

        self.gridLayout_4.addWidget(self.language_combobox, 1, 0, 1, 1)

        self.label = QLabel(self.groupBox_3)
        self.label.setObjectName(u"label")
        self.label.setFont(font)

        self.gridLayout_4.addWidget(self.label, 0, 0, 1, 1)


        self.gridLayout_8.addWidget(self.groupBox_3, 3, 0, 1, 1)


        self.gridLayout_7.addWidget(self.use_bark, 0, 0, 1, 1)


        self.retranslateUi(bark_preferences)
        self.language_combobox.currentTextChanged.connect(bark_preferences.language_changed)
        self.voice_combobox.currentTextChanged.connect(bark_preferences.voice_changed)
        self.gender_combobox.currentTextChanged.connect(bark_preferences.gender_changed)

        QMetaObject.connectSlotsByName(bark_preferences)
    # setupUi

    def retranslateUi(self, bark_preferences):
        bark_preferences.setWindowTitle(QCoreApplication.translate("bark_preferences", u"Form", None))
        self.use_bark.setTitle(QCoreApplication.translate("bark_preferences", u"Bark", None))
        self.groupBox_6.setTitle(QCoreApplication.translate("bark_preferences", u"Coarse Temperature", None))
        self.coarse_temperature.setProperty("settings_property", QCoreApplication.translate("bark_preferences", u"bark.coarse_temperature", None))
        self.groupBox.setTitle(QCoreApplication.translate("bark_preferences", u"Voice", None))
        self.groupBox_5.setTitle(QCoreApplication.translate("bark_preferences", u"Semantic Temperature", None))
        self.semantic_temperature.setProperty("settings_property", QCoreApplication.translate("bark_preferences", u"bark.semantic_temperature", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("bark_preferences", u"Gender", None))
        self.gender_combobox.setItemText(0, QCoreApplication.translate("bark_preferences", u"Male", None))
        self.gender_combobox.setItemText(1, QCoreApplication.translate("bark_preferences", u"Female", None))

        self.label_3.setText(QCoreApplication.translate("bark_preferences", u"Realistic, slow and higher VRAM usage.", None))
        self.groupBox_4.setTitle(QCoreApplication.translate("bark_preferences", u"Fine Temperature", None))
        self.fine_temperature.setProperty("settings_property", QCoreApplication.translate("bark_preferences", u"bark.fine_temperature", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("bark_preferences", u"Language", None))
        self.label.setText(QCoreApplication.translate("bark_preferences", u"Override the system language", None))
    # retranslateUi

