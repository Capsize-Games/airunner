# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'brush_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QScrollArea, QSizePolicy, QSpacerItem, QToolButton,
    QWidget)

from airunner.widgets.slider.slider_widget import SliderWidget

class Ui_brush_widget(object):
    def setupUi(self, brush_widget):
        if not brush_widget.objectName():
            brush_widget.setObjectName(u"brush_widget")
        brush_widget.resize(1004, 622)
        self.gridLayout_2 = QGridLayout(brush_widget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label = QLabel(brush_widget)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)

        self.scrollArea = QScrollArea(brush_widget)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 984, 570))
        self.gridLayout = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(9, 0, 9, 0)
        self.controlnet = QComboBox(self.scrollAreaWidgetContents)
        self.controlnet.setObjectName(u"controlnet")

        self.gridLayout.addWidget(self.controlnet, 0, 0, 1, 1)

        self.widget = QWidget(self.scrollAreaWidgetContents)
        self.widget.setObjectName(u"widget")
        self.widget.setMinimumSize(QSize(0, 0))
        self.horizontalLayout = QHBoxLayout(self.widget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, -1)
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

        self.horizontalLayout.addWidget(self.controlnet_conditioning_scale)

        self.controlnet_guidance_scale = SliderWidget(self.widget)
        self.controlnet_guidance_scale.setObjectName(u"controlnet_guidance_scale")
        self.controlnet_guidance_scale.setProperty("slider_minimum", 1)
        self.controlnet_guidance_scale.setProperty("slider_maximum", 1000)
        self.controlnet_guidance_scale.setProperty("spinbox_minimum", 1)
        self.controlnet_guidance_scale.setProperty("spinbox_maximum", 100.000000000000000)
        self.controlnet_guidance_scale.setProperty("slider_tick_interval", 1)
        self.controlnet_guidance_scale.setProperty("slider_single_step", 1)
        self.controlnet_guidance_scale.setProperty("slider_page_step", 10)
        self.controlnet_guidance_scale.setProperty("spinbox_single_step", 0.100000000000000)
        self.controlnet_guidance_scale.setProperty("spinbox_page_step", 0.200000000000000)
        self.controlnet_guidance_scale.setProperty("settings_property", u"brush_settings.guidance_scale")
        self.controlnet_guidance_scale.setProperty("display_as_float", True)

        self.horizontalLayout.addWidget(self.controlnet_guidance_scale)


        self.gridLayout.addWidget(self.widget, 1, 0, 1, 1)

        self.groupBox_4 = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_4.setObjectName(u"groupBox_4")
        self.groupBox_4.setMinimumSize(QSize(0, 60))
        font1 = QFont()
        font1.setPointSize(10)
        font1.setBold(True)
        self.groupBox_4.setFont(font1)
        self.gridLayout_3 = QGridLayout(self.groupBox_4)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setContentsMargins(6, 9, 6, 6)
        self.primary_color_button = QToolButton(self.groupBox_4)
        self.primary_color_button.setObjectName(u"primary_color_button")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.primary_color_button.sizePolicy().hasHeightForWidth())
        self.primary_color_button.setSizePolicy(sizePolicy)
        self.primary_color_button.setFont(font1)

        self.gridLayout_3.addWidget(self.primary_color_button, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_4, 4, 0, 1, 1)

        self.widget_2 = QWidget(self.scrollAreaWidgetContents)
        self.widget_2.setObjectName(u"widget_2")
        self.widget_2.setMinimumSize(QSize(0, 20))
        self.widget_2.setStyleSheet(u"")
        self.horizontalLayout_2 = QHBoxLayout(self.widget_2)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, -1)
        self.strength_slider = SliderWidget(self.widget_2)
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

        self.horizontalLayout_2.addWidget(self.strength_slider)

        self.brush_size_slider = SliderWidget(self.widget_2)
        self.brush_size_slider.setObjectName(u"brush_size_slider")
        self.brush_size_slider.setProperty("slider_minimum", 1)
        self.brush_size_slider.setProperty("slider_maximum", 100)
        self.brush_size_slider.setProperty("spinbox_minimum", 1)
        self.brush_size_slider.setProperty("spinbox_maximum", 100)
        self.brush_size_slider.setProperty("slider_tick_interval", 1)
        self.brush_size_slider.setProperty("slider_single_step", 1)
        self.brush_size_slider.setProperty("slider_page_step", 10)
        self.brush_size_slider.setProperty("spinbox_single_step", 1)
        self.brush_size_slider.setProperty("spinbox_page_step", 10)
        self.brush_size_slider.setProperty("settings_property", u"brush_settings.size")
        self.brush_size_slider.setProperty("display_as_float", False)

        self.horizontalLayout_2.addWidget(self.brush_size_slider)


        self.gridLayout.addWidget(self.widget_2, 2, 0, 1, 1)

        self.toggle_auto_generate_while_drawing = QCheckBox(self.scrollAreaWidgetContents)
        self.toggle_auto_generate_while_drawing.setObjectName(u"toggle_auto_generate_while_drawing")

        self.gridLayout.addWidget(self.toggle_auto_generate_while_drawing, 5, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 6, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_2.addWidget(self.scrollArea, 2, 0, 1, 1)

        self.line = QFrame(brush_widget)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_2.addWidget(self.line, 1, 0, 1, 1)


        self.retranslateUi(brush_widget)
        self.primary_color_button.clicked.connect(brush_widget.color_button_clicked)
        self.controlnet.currentTextChanged.connect(brush_widget.controlnet_changed)
        self.toggle_auto_generate_while_drawing.toggled.connect(brush_widget.toggle_auto_generate_while_drawing)

        QMetaObject.connectSlotsByName(brush_widget)
    # setupUi

    def retranslateUi(self, brush_widget):
        brush_widget.setWindowTitle(QCoreApplication.translate("brush_widget", u"Form", None))
        self.label.setText(QCoreApplication.translate("brush_widget", u"Brush Settings", None))
        self.controlnet_conditioning_scale.setProperty("label_text", QCoreApplication.translate("brush_widget", u"Conditioning Scale", None))
        self.controlnet_guidance_scale.setProperty("label_text", QCoreApplication.translate("brush_widget", u"Guidance Scale", None))
        self.groupBox_4.setTitle(QCoreApplication.translate("brush_widget", u"Brush color", None))
        self.primary_color_button.setText("")
        self.strength_slider.setProperty("label_text", QCoreApplication.translate("brush_widget", u"Strength", None))
        self.brush_size_slider.setProperty("label_text", QCoreApplication.translate("brush_widget", u"Brush Size", None))
        self.toggle_auto_generate_while_drawing.setText(QCoreApplication.translate("brush_widget", u"Auto-generate while drawing", None))
    # retranslateUi

