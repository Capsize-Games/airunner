# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'input_image.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QGraphicsView, QGridLayout,
    QHBoxLayout, QPushButton, QScrollArea, QSizePolicy,
    QSpacerItem, QWidget)

from airunner.widgets.controlnet.controlnet_settings_widget import ControlnetSettingsWidget
from airunner.widgets.slider.slider_widget import SliderWidget

class Ui_input_image(object):
    def setupUi(self, input_image):
        if not input_image.objectName():
            input_image.setObjectName(u"input_image")
        input_image.resize(581, 568)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(input_image.sizePolicy().hasHeightForWidth())
        input_image.setSizePolicy(sizePolicy)
        self.gridLayout_3 = QGridLayout(input_image)
        self.gridLayout_3.setSpacing(0)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.scrollArea = QScrollArea(input_image)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 565, 512))
        self.gridLayout_2 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_2.setSpacing(0)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.image_container = QGraphicsView(self.scrollAreaWidgetContents)
        self.image_container.setObjectName(u"image_container")
        sizePolicy.setHeightForWidth(self.image_container.sizePolicy().hasHeightForWidth())
        self.image_container.setSizePolicy(sizePolicy)
        self.image_container.setMinimumSize(QSize(512, 512))

        self.gridLayout_2.addWidget(self.image_container, 0, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_3.addWidget(self.scrollArea, 0, 0, 1, 1)

        self.verticalWidget = QWidget(input_image)
        self.verticalWidget.setObjectName(u"verticalWidget")
        self.gridLayout = QGridLayout(self.verticalWidget)
        self.gridLayout.setSpacing(10)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(10, 10, 10, 10)
        self.strength_slider_widget = SliderWidget(self.verticalWidget)
        self.strength_slider_widget.setObjectName(u"strength_slider_widget")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.strength_slider_widget.sizePolicy().hasHeightForWidth())
        self.strength_slider_widget.setSizePolicy(sizePolicy1)
        self.strength_slider_widget.setProperty("slider_maximum", 100)
        self.strength_slider_widget.setProperty("current_value", 0)
        self.strength_slider_widget.setProperty("spinbox_maximum", 1.000000000000000)
        self.strength_slider_widget.setProperty("display_as_float", True)
        self.strength_slider_widget.setProperty("spinbox_single_step", 0.010000000000000)
        self.strength_slider_widget.setProperty("spinbox_page_step", 0.100000000000000)

        self.gridLayout.addWidget(self.strength_slider_widget, 0, 0, 1, 1)

        self.mask_blur_slider_widget = SliderWidget(self.verticalWidget)
        self.mask_blur_slider_widget.setObjectName(u"mask_blur_slider_widget")
        sizePolicy1.setHeightForWidth(self.mask_blur_slider_widget.sizePolicy().hasHeightForWidth())
        self.mask_blur_slider_widget.setSizePolicy(sizePolicy1)
        self.mask_blur_slider_widget.setProperty("slider_maximum", 100)
        self.mask_blur_slider_widget.setProperty("current_value", 0)
        self.mask_blur_slider_widget.setProperty("spinbox_maximum", 1.000000000000000)
        self.mask_blur_slider_widget.setProperty("display_as_float", True)
        self.mask_blur_slider_widget.setProperty("spinbox_single_step", 0.010000000000000)
        self.mask_blur_slider_widget.setProperty("spinbox_page_step", 0.100000000000000)

        self.gridLayout.addWidget(self.mask_blur_slider_widget, 1, 0, 1, 1)

        self.controlnet_settings = ControlnetSettingsWidget(self.verticalWidget)
        self.controlnet_settings.setObjectName(u"controlnet_settings")

        self.gridLayout.addWidget(self.controlnet_settings, 2, 0, 1, 1)


        self.gridLayout_3.addWidget(self.verticalWidget, 1, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(10)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(10, -1, 10, 10)
        self.use_grid_image_as_input_checkbox = QCheckBox(input_image)
        self.use_grid_image_as_input_checkbox.setObjectName(u"use_grid_image_as_input_checkbox")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.use_grid_image_as_input_checkbox.sizePolicy().hasHeightForWidth())
        self.use_grid_image_as_input_checkbox.setSizePolicy(sizePolicy2)

        self.horizontalLayout.addWidget(self.use_grid_image_as_input_checkbox)

        self.enable_checkbox = QCheckBox(input_image)
        self.enable_checkbox.setObjectName(u"enable_checkbox")
        sizePolicy2.setHeightForWidth(self.enable_checkbox.sizePolicy().hasHeightForWidth())
        self.enable_checkbox.setSizePolicy(sizePolicy2)

        self.horizontalLayout.addWidget(self.enable_checkbox)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.import_button = QPushButton(input_image)
        self.import_button.setObjectName(u"import_button")
        icon = QIcon(QIcon.fromTheme(u"folder"))
        self.import_button.setIcon(icon)

        self.horizontalLayout.addWidget(self.import_button)

        self.delete_button = QPushButton(input_image)
        self.delete_button.setObjectName(u"delete_button")
        icon1 = QIcon(QIcon.fromTheme(u"user-trash"))
        self.delete_button.setIcon(icon1)

        self.horizontalLayout.addWidget(self.delete_button)


        self.gridLayout_3.addLayout(self.horizontalLayout, 2, 0, 1, 1)


        self.retranslateUi(input_image)
        self.use_grid_image_as_input_checkbox.toggled.connect(input_image.use_grid_image_as_input_toggled)
        self.enable_checkbox.toggled.connect(input_image.enabled_toggled)
        self.import_button.clicked.connect(input_image.import_clicked)
        self.delete_button.clicked.connect(input_image.delete_clicked)

        QMetaObject.connectSlotsByName(input_image)
    # setupUi

    def retranslateUi(self, input_image):
        input_image.setWindowTitle(QCoreApplication.translate("input_image", u"Form", None))
        self.strength_slider_widget.setProperty("label_text", QCoreApplication.translate("input_image", u"Strength", None))
        self.strength_slider_widget.setProperty("settings_property", QCoreApplication.translate("input_image", u"generator_settings.strength", None))
        self.mask_blur_slider_widget.setProperty("label_text", QCoreApplication.translate("input_image", u"Mask Blur", None))
        self.mask_blur_slider_widget.setProperty("settings_property", QCoreApplication.translate("input_image", u"outpaint_settings.mask_blur", None))
#if QT_CONFIG(tooltip)
        self.use_grid_image_as_input_checkbox.setToolTip(QCoreApplication.translate("input_image", u"Use grid image as input", None))
#endif // QT_CONFIG(tooltip)
        self.use_grid_image_as_input_checkbox.setText(QCoreApplication.translate("input_image", u"Grid Image", None))
#if QT_CONFIG(tooltip)
        self.enable_checkbox.setToolTip(QCoreApplication.translate("input_image", u"Enable", None))
#endif // QT_CONFIG(tooltip)
        self.enable_checkbox.setText(QCoreApplication.translate("input_image", u"Enable ", None))
#if QT_CONFIG(tooltip)
        self.import_button.setToolTip(QCoreApplication.translate("input_image", u"Import", None))
#endif // QT_CONFIG(tooltip)
        self.import_button.setText("")
#if QT_CONFIG(tooltip)
        self.delete_button.setToolTip(QCoreApplication.translate("input_image", u"Delete", None))
#endif // QT_CONFIG(tooltip)
        self.delete_button.setText("")
    # retranslateUi

