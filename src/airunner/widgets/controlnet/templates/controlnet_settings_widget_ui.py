# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'controlnet_settings_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QGridLayout,
    QLabel, QScrollArea, QSizePolicy, QSpacerItem,
    QVBoxLayout, QWidget)

from airunner.widgets.slider.slider_widget import SliderWidget

class Ui_controlnet_settings_widget(object):
    def setupUi(self, controlnet_settings_widget):
        if not controlnet_settings_widget.objectName():
            controlnet_settings_widget.setObjectName(u"controlnet_settings_widget")
        controlnet_settings_widget.resize(1004, 622)
        self.gridLayout_2 = QGridLayout(controlnet_settings_widget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.line = QFrame(controlnet_settings_widget)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_2.addWidget(self.line, 1, 0, 1, 1)

        self.label = QLabel(controlnet_settings_widget)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)

        self.scrollArea = QScrollArea(controlnet_settings_widget)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 984, 570))
        self.gridLayout = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(9, 0, 9, 0)
        self.widget = QWidget(self.scrollAreaWidgetContents)
        self.widget.setObjectName(u"widget")
        self.widget.setMinimumSize(QSize(0, 0))
        self.verticalLayout = QVBoxLayout(self.widget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, -1)
        self.controlnet_conditioning_scale = SliderWidget(self.widget)
        self.controlnet_conditioning_scale.setObjectName(u"controlnet_conditioning_scale")
        self.controlnet_conditioning_scale.setProperty("slider_minimum", 0)
        self.controlnet_conditioning_scale.setProperty("slider_maximum", 100)
        self.controlnet_conditioning_scale.setProperty("spinbox_minimum", 0)
        self.controlnet_conditioning_scale.setProperty("spinbox_maximum", 1.000000000000000)
        self.controlnet_conditioning_scale.setProperty("slider_tick_interval", 1)
        self.controlnet_conditioning_scale.setProperty("slider_single_step", 1)
        self.controlnet_conditioning_scale.setProperty("slider_page_step", 2)
        self.controlnet_conditioning_scale.setProperty("spinbox_single_step", 0.100000000000000)
        self.controlnet_conditioning_scale.setProperty("spinbox_page_step", 0.200000000000000)
        self.controlnet_conditioning_scale.setProperty("settings_property", u"brush_settings.conditioning_scale")
        self.controlnet_conditioning_scale.setProperty("display_as_float", True)

        self.verticalLayout.addWidget(self.controlnet_conditioning_scale)

        self.strength_slider = SliderWidget(self.widget)
        self.strength_slider.setObjectName(u"strength_slider")
        self.strength_slider.setProperty("slider_minimum", 0)
        self.strength_slider.setProperty("slider_maximum", 100)
        self.strength_slider.setProperty("spinbox_minimum", 0)
        self.strength_slider.setProperty("spinbox_maximum", 1.000000000000000)
        self.strength_slider.setProperty("slider_tick_interval", 1)
        self.strength_slider.setProperty("slider_single_step", 1)
        self.strength_slider.setProperty("slider_page_step", 10)
        self.strength_slider.setProperty("spinbox_single_step", 0.100000000000000)
        self.strength_slider.setProperty("spinbox_page_step", 0.200000000000000)
        self.strength_slider.setProperty("settings_property", u"brush_settings.strength")
        self.strength_slider.setProperty("display_as_float", True)

        self.verticalLayout.addWidget(self.strength_slider)


        self.gridLayout.addWidget(self.widget, 1, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 3, 0, 1, 1)

        self.controlnet = QComboBox(self.scrollAreaWidgetContents)
        self.controlnet.setObjectName(u"controlnet")

        self.gridLayout.addWidget(self.controlnet, 0, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_2.addWidget(self.scrollArea, 2, 0, 1, 1)


        self.retranslateUi(controlnet_settings_widget)
        self.controlnet.currentTextChanged.connect(controlnet_settings_widget.controlnet_changed)

        QMetaObject.connectSlotsByName(controlnet_settings_widget)
    # setupUi

    def retranslateUi(self, controlnet_settings_widget):
        controlnet_settings_widget.setWindowTitle(QCoreApplication.translate("controlnet_settings_widget", u"Form", None))
        self.label.setText(QCoreApplication.translate("controlnet_settings_widget", u"Controlnet Settings", None))
        self.controlnet_conditioning_scale.setProperty("label_text", QCoreApplication.translate("controlnet_settings_widget", u"Conditioning Scale", None))
        self.strength_slider.setProperty("label_text", QCoreApplication.translate("controlnet_settings_widget", u"Strength", None))
    # retranslateUi

