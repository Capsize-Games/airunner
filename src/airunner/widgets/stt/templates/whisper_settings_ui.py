# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'whisper_settings.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGridLayout,
    QLabel, QPushButton, QSizePolicy, QVBoxLayout,
    QWidget)

from airunner.widgets.slider.slider_widget import SliderWidget

class Ui_whisper_settings(object):
    def setupUi(self, whisper_settings):
        if not whisper_settings.objectName():
            whisper_settings.setObjectName(u"whisper_settings")
        whisper_settings.resize(400, 300)
        self.gridLayout_2 = QGridLayout(whisper_settings)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setHorizontalSpacing(0)
        self.gridLayout_2.setVerticalSpacing(10)
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.whisper_settings_container = QWidget(whisper_settings)
        self.whisper_settings_container.setObjectName(u"whisper_settings_container")
        self.gridLayout = QGridLayout(self.whisper_settings_container)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(0)
        self.gridLayout.setVerticalSpacing(10)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.is_multilingual = QCheckBox(self.whisper_settings_container)
        self.is_multilingual.setObjectName(u"is_multilingual")

        self.gridLayout.addWidget(self.is_multilingual, 0, 0, 1, 1)

        self.temperature = SliderWidget(self.whisper_settings_container)
        self.temperature.setObjectName(u"temperature")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.temperature.sizePolicy().hasHeightForWidth())
        self.temperature.setSizePolicy(sizePolicy)
        self.temperature.setMinimumSize(QSize(0, 10))
        self.temperature.setProperty("slider_minimum", 1)
        self.temperature.setProperty("slider_maximum", 1000)
        self.temperature.setProperty("spinbox_minimum", 0.000000000000000)
        self.temperature.setProperty("spinbox_maximum", 1.000000000000000)
        self.temperature.setProperty("display_as_float", True)
        self.temperature.setProperty("slider_single_step", 1)
        self.temperature.setProperty("slider_page_step", 10)
        self.temperature.setProperty("spinbox_single_step", 0.010000000000000)
        self.temperature.setProperty("spinbox_page_step", 0.100000000000000)

        self.gridLayout.addWidget(self.temperature, 1, 0, 1, 1)

        self.compression_ratio_threshold = SliderWidget(self.whisper_settings_container)
        self.compression_ratio_threshold.setObjectName(u"compression_ratio_threshold")
        sizePolicy.setHeightForWidth(self.compression_ratio_threshold.sizePolicy().hasHeightForWidth())
        self.compression_ratio_threshold.setSizePolicy(sizePolicy)
        self.compression_ratio_threshold.setMinimumSize(QSize(0, 10))
        self.compression_ratio_threshold.setProperty("slider_minimum", 1)
        self.compression_ratio_threshold.setProperty("slider_maximum", 5000)
        self.compression_ratio_threshold.setProperty("spinbox_minimum", 0.000000000000000)
        self.compression_ratio_threshold.setProperty("spinbox_maximum", 5.000000000000000)
        self.compression_ratio_threshold.setProperty("display_as_float", True)
        self.compression_ratio_threshold.setProperty("slider_single_step", 1)
        self.compression_ratio_threshold.setProperty("slider_page_step", 10)
        self.compression_ratio_threshold.setProperty("spinbox_single_step", 0.010000000000000)
        self.compression_ratio_threshold.setProperty("spinbox_page_step", 0.100000000000000)

        self.gridLayout.addWidget(self.compression_ratio_threshold, 2, 0, 1, 1)

        self.logprob_threshold = SliderWidget(self.whisper_settings_container)
        self.logprob_threshold.setObjectName(u"logprob_threshold")
        sizePolicy.setHeightForWidth(self.logprob_threshold.sizePolicy().hasHeightForWidth())
        self.logprob_threshold.setSizePolicy(sizePolicy)
        self.logprob_threshold.setMinimumSize(QSize(0, 10))
        self.logprob_threshold.setProperty("slider_minimum", -1000)
        self.logprob_threshold.setProperty("slider_maximum", 1000)
        self.logprob_threshold.setProperty("spinbox_minimum", -1.000000000000000)
        self.logprob_threshold.setProperty("spinbox_maximum", 1.000000000000000)
        self.logprob_threshold.setProperty("display_as_float", True)
        self.logprob_threshold.setProperty("slider_single_step", 1)
        self.logprob_threshold.setProperty("slider_page_step", 10)
        self.logprob_threshold.setProperty("spinbox_single_step", 0.010000000000000)
        self.logprob_threshold.setProperty("spinbox_page_step", 0.100000000000000)

        self.gridLayout.addWidget(self.logprob_threshold, 3, 0, 1, 1)

        self.no_speech_threshold = SliderWidget(self.whisper_settings_container)
        self.no_speech_threshold.setObjectName(u"no_speech_threshold")
        sizePolicy.setHeightForWidth(self.no_speech_threshold.sizePolicy().hasHeightForWidth())
        self.no_speech_threshold.setSizePolicy(sizePolicy)
        self.no_speech_threshold.setMinimumSize(QSize(0, 10))
        self.no_speech_threshold.setProperty("slider_minimum", 0)
        self.no_speech_threshold.setProperty("slider_maximum", 1000)
        self.no_speech_threshold.setProperty("spinbox_minimum", 0.000000000000000)
        self.no_speech_threshold.setProperty("spinbox_maximum", 1.000000000000000)
        self.no_speech_threshold.setProperty("display_as_float", True)
        self.no_speech_threshold.setProperty("slider_single_step", 1)
        self.no_speech_threshold.setProperty("slider_page_step", 10)
        self.no_speech_threshold.setProperty("spinbox_single_step", 0.010000000000000)
        self.no_speech_threshold.setProperty("spinbox_page_step", 0.100000000000000)

        self.gridLayout.addWidget(self.no_speech_threshold, 4, 0, 1, 1)

        self.time_precision = SliderWidget(self.whisper_settings_container)
        self.time_precision.setObjectName(u"time_precision")
        sizePolicy.setHeightForWidth(self.time_precision.sizePolicy().hasHeightForWidth())
        self.time_precision.setSizePolicy(sizePolicy)
        self.time_precision.setMinimumSize(QSize(0, 10))
        self.time_precision.setProperty("slider_minimum", 0)
        self.time_precision.setProperty("slider_maximum", 1000)
        self.time_precision.setProperty("spinbox_minimum", 0.000000000000000)
        self.time_precision.setProperty("spinbox_maximum", 1.000000000000000)
        self.time_precision.setProperty("display_as_float", True)
        self.time_precision.setProperty("slider_single_step", 1)
        self.time_precision.setProperty("slider_page_step", 10)
        self.time_precision.setProperty("spinbox_single_step", 0.010000000000000)
        self.time_precision.setProperty("spinbox_page_step", 0.100000000000000)

        self.gridLayout.addWidget(self.time_precision, 5, 0, 1, 1)

        self.widget = QWidget(self.whisper_settings_container)
        self.widget.setObjectName(u"widget")
        self.verticalLayout_2 = QVBoxLayout(self.widget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.label = QLabel(self.widget)
        self.label.setObjectName(u"label")

        self.verticalLayout_2.addWidget(self.label)

        self.language = QComboBox(self.widget)
        self.language.setObjectName(u"language")

        self.verticalLayout_2.addWidget(self.language)


        self.gridLayout.addWidget(self.widget, 6, 0, 1, 1)

        self.widget_2 = QWidget(self.whisper_settings_container)
        self.widget_2.setObjectName(u"widget_2")
        self.verticalLayout = QVBoxLayout(self.widget_2)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label_3 = QLabel(self.widget_2)
        self.label_3.setObjectName(u"label_3")

        self.verticalLayout.addWidget(self.label_3)

        self.task = QComboBox(self.widget_2)
        self.task.setObjectName(u"task")

        self.verticalLayout.addWidget(self.task)

        self.pushButton = QPushButton(self.widget_2)
        self.pushButton.setObjectName(u"pushButton")

        self.verticalLayout.addWidget(self.pushButton)


        self.gridLayout.addWidget(self.widget_2, 7, 0, 1, 1)


        self.gridLayout_2.addWidget(self.whisper_settings_container, 0, 0, 1, 1)


        self.retranslateUi(whisper_settings)
        self.language.currentTextChanged.connect(whisper_settings.on_language_changed)
        self.task.currentTextChanged.connect(whisper_settings.on_task_changed)
        self.is_multilingual.toggled.connect(whisper_settings.is_multilingual_changed)
        self.pushButton.clicked.connect(whisper_settings.on_reset_default_clicked)

        QMetaObject.connectSlotsByName(whisper_settings)
    # setupUi

    def retranslateUi(self, whisper_settings):
        whisper_settings.setWindowTitle(QCoreApplication.translate("whisper_settings", u"Form", None))
        self.is_multilingual.setText(QCoreApplication.translate("whisper_settings", u"Is Multilingual", None))
        self.temperature.setProperty("settings_property", QCoreApplication.translate("whisper_settings", u"whisper_settings.temperature", None))
        self.temperature.setProperty("label_text", QCoreApplication.translate("whisper_settings", u"Temperature", None))
        self.compression_ratio_threshold.setProperty("settings_property", QCoreApplication.translate("whisper_settings", u"whisper_settings.compression_ratio_threshold", None))
        self.compression_ratio_threshold.setProperty("label_text", QCoreApplication.translate("whisper_settings", u"Compression ratio threshold", None))
        self.logprob_threshold.setProperty("settings_property", QCoreApplication.translate("whisper_settings", u"whisper_settings.logprob_threshold", None))
        self.logprob_threshold.setProperty("label_text", QCoreApplication.translate("whisper_settings", u"Logprob threshold", None))
        self.no_speech_threshold.setProperty("settings_property", QCoreApplication.translate("whisper_settings", u"whisper_settings.no_speech_threshold", None))
        self.no_speech_threshold.setProperty("label_text", QCoreApplication.translate("whisper_settings", u"No speech threshold", None))
        self.time_precision.setProperty("settings_property", QCoreApplication.translate("whisper_settings", u"whisper_settings.time_precision", None))
        self.time_precision.setProperty("label_text", QCoreApplication.translate("whisper_settings", u"Time precision", None))
        self.label.setText(QCoreApplication.translate("whisper_settings", u"Language", None))
        self.label_3.setText(QCoreApplication.translate("whisper_settings", u"Task", None))
        self.pushButton.setText(QCoreApplication.translate("whisper_settings", u"Reset to Default", None))
    # retranslateUi

