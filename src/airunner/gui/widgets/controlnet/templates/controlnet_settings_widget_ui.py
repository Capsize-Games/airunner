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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QSizePolicy,
    QVBoxLayout, QWidget)

from airunner.gui.widgets.slider.slider_widget import SliderWidget

class Ui_controlnet_settings_widget(object):
    def setupUi(self, controlnet_settings_widget):
        if not controlnet_settings_widget.objectName():
            controlnet_settings_widget.setObjectName(u"controlnet_settings_widget")
        controlnet_settings_widget.resize(694, 763)
        self.gridLayout_2 = QGridLayout(controlnet_settings_widget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setHorizontalSpacing(0)
        self.gridLayout_2.setVerticalSpacing(10)
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.widget_3 = QWidget(controlnet_settings_widget)
        self.widget_3.setObjectName(u"widget_3")
        self.gridLayout = QGridLayout(self.widget_3)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(0)
        self.gridLayout.setVerticalSpacing(10)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.widget = QWidget(self.widget_3)
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
        self.controlnet_conditioning_scale.setProperty("settings_property", u"controlnet_settings.conditioning_scale")
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
        self.strength_slider.setProperty("settings_property", u"controlnet_settings.strength")
        self.strength_slider.setProperty("display_as_float", True)

        self.verticalLayout.addWidget(self.strength_slider)


        self.gridLayout.addWidget(self.widget, 1, 0, 1, 1)

        self.controlnet = QComboBox(self.widget_3)
        self.controlnet.setObjectName(u"controlnet")

        self.gridLayout.addWidget(self.controlnet, 0, 0, 1, 1)


        self.gridLayout_2.addWidget(self.widget_3, 1, 0, 1, 1)

        self.section_header = QWidget(controlnet_settings_widget)
        self.section_header.setObjectName(u"section_header")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.section_header.sizePolicy().hasHeightForWidth())
        self.section_header.setSizePolicy(sizePolicy)
        self.section_header.setMinimumSize(QSize(0, 0))
        self.gridLayout_3 = QGridLayout(self.section_header)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setContentsMargins(0, 0, 10, 0)

        self.gridLayout_2.addWidget(self.section_header, 0, 0, 1, 1)


        self.retranslateUi(controlnet_settings_widget)
        self.controlnet.currentTextChanged.connect(controlnet_settings_widget.controlnet_changed)

        QMetaObject.connectSlotsByName(controlnet_settings_widget)
    # setupUi

    def retranslateUi(self, controlnet_settings_widget):
        controlnet_settings_widget.setWindowTitle(QCoreApplication.translate("controlnet_settings_widget", u"Form", None))
        self.controlnet_conditioning_scale.setProperty("label_text", QCoreApplication.translate("controlnet_settings_widget", u"Conditioning Scale", None))
        self.strength_slider.setProperty("label_text", QCoreApplication.translate("controlnet_settings_widget", u"Strength", None))
    # retranslateUi

