# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'stt_settings.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QLabel,
    QScrollArea, QSizePolicy, QSpacerItem, QWidget)

from airunner.widgets.slider.slider_widget import SliderWidget
from airunner.widgets.stt.whisper_settings_widget import WhisperSettingsWidget

class Ui_stt_settings(object):
    def setupUi(self, stt_settings):
        if not stt_settings.objectName():
            stt_settings.setObjectName(u"stt_settings")
        stt_settings.resize(400, 809)
        self.gridLayout_3 = QGridLayout(stt_settings)
        self.gridLayout_3.setSpacing(0)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.label_2 = QLabel(stt_settings)
        self.label_2.setObjectName(u"label_2")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label_2.setFont(font)

        self.gridLayout_3.addWidget(self.label_2, 0, 0, 1, 1)

        self.line = QFrame(stt_settings)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_3.addWidget(self.line, 1, 0, 1, 1)

        self.scrollArea = QScrollArea(stt_settings)
        self.scrollArea.setObjectName(u"scrollArea")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrollArea.sizePolicy().hasHeightForWidth())
        self.scrollArea.setSizePolicy(sizePolicy)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 398, 787))
        self.gridLayout = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(0)
        self.gridLayout.setVerticalSpacing(10)
        self.gridLayout.setContentsMargins(0, 0, 10, 0)
        self.volume_input_threshold_slider = SliderWidget(self.scrollAreaWidgetContents)
        self.volume_input_threshold_slider.setObjectName(u"volume_input_threshold_slider")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.volume_input_threshold_slider.sizePolicy().hasHeightForWidth())
        self.volume_input_threshold_slider.setSizePolicy(sizePolicy1)
        self.volume_input_threshold_slider.setMinimumSize(QSize(0, 10))
        self.volume_input_threshold_slider.setProperty("slider_minimum", 1)
        self.volume_input_threshold_slider.setProperty("slider_maximum", 2000)
        self.volume_input_threshold_slider.setProperty("spinbox_minimum", 0.000000000000000)
        self.volume_input_threshold_slider.setProperty("spinbox_maximum", 2.000000000000000)
        self.volume_input_threshold_slider.setProperty("display_as_float", True)
        self.volume_input_threshold_slider.setProperty("slider_single_step", 1)
        self.volume_input_threshold_slider.setProperty("slider_page_step", 10)
        self.volume_input_threshold_slider.setProperty("spinbox_single_step", 0.010000000000000)
        self.volume_input_threshold_slider.setProperty("spinbox_page_step", 0.100000000000000)

        self.gridLayout.addWidget(self.volume_input_threshold_slider, 0, 0, 1, 1)

        self.silence_buffer_seconds = SliderWidget(self.scrollAreaWidgetContents)
        self.silence_buffer_seconds.setObjectName(u"silence_buffer_seconds")
        sizePolicy1.setHeightForWidth(self.silence_buffer_seconds.sizePolicy().hasHeightForWidth())
        self.silence_buffer_seconds.setSizePolicy(sizePolicy1)
        self.silence_buffer_seconds.setMinimumSize(QSize(0, 10))
        self.silence_buffer_seconds.setProperty("slider_minimum", 1)
        self.silence_buffer_seconds.setProperty("slider_maximum", 5000)
        self.silence_buffer_seconds.setProperty("spinbox_minimum", 0.000000000000000)
        self.silence_buffer_seconds.setProperty("spinbox_maximum", 5.000000000000000)
        self.silence_buffer_seconds.setProperty("display_as_float", True)
        self.silence_buffer_seconds.setProperty("slider_single_step", 1)
        self.silence_buffer_seconds.setProperty("slider_page_step", 10)
        self.silence_buffer_seconds.setProperty("spinbox_single_step", 0.010000000000000)
        self.silence_buffer_seconds.setProperty("spinbox_page_step", 0.100000000000000)

        self.gridLayout.addWidget(self.silence_buffer_seconds, 1, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 724, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 3, 0, 1, 1)

        self.widget = WhisperSettingsWidget(self.scrollAreaWidgetContents)
        self.widget.setObjectName(u"widget")
        sizePolicy1.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy1)

        self.gridLayout.addWidget(self.widget, 2, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_3.addWidget(self.scrollArea, 2, 0, 1, 1)


        self.retranslateUi(stt_settings)

        QMetaObject.connectSlotsByName(stt_settings)
    # setupUi

    def retranslateUi(self, stt_settings):
        stt_settings.setWindowTitle(QCoreApplication.translate("stt_settings", u"Form", None))
        self.label_2.setText(QCoreApplication.translate("stt_settings", u"LLM Settings", None))
        self.volume_input_threshold_slider.setProperty("settings_property", QCoreApplication.translate("stt_settings", u"stt_settings.volume_input_threshold", None))
        self.volume_input_threshold_slider.setProperty("label_text", QCoreApplication.translate("stt_settings", u"Input Volume", None))
        self.silence_buffer_seconds.setProperty("settings_property", QCoreApplication.translate("stt_settings", u"stt_settings.silence_buffer_seconds", None))
        self.silence_buffer_seconds.setProperty("label_text", QCoreApplication.translate("stt_settings", u"Silence Buffer", None))
    # retranslateUi

