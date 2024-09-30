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
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QGraphicsView,
    QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QSizePolicy, QSpacerItem, QWidget)

from airunner.widgets.controlnet.controlnet_settings_widget import ControlnetSettingsWidget
from airunner.widgets.slider.slider_widget import SliderWidget

class Ui_input_image(object):
    def setupUi(self, input_image):
        if not input_image.objectName():
            input_image.setObjectName(u"input_image")
        input_image.resize(605, 920)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(input_image.sizePolicy().hasHeightForWidth())
        input_image.setSizePolicy(sizePolicy)
        self.gridLayout = QGridLayout(input_image)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.scrollArea = QScrollArea(input_image)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 603, 918))
        self.gridLayout_2 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setHorizontalSpacing(0)
        self.gridLayout_2.setVerticalSpacing(10)
        self.gridLayout_2.setContentsMargins(10, 10, 10, 10)
        self.line = QFrame(self.scrollAreaWidgetContents)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_2.addWidget(self.line, 1, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer, 3, 0, 1, 1)

        self.strength_slider_widget = SliderWidget(self.scrollAreaWidgetContents)
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

        self.gridLayout_2.addWidget(self.strength_slider_widget, 6, 0, 1, 1)

        self.image_container = QGraphicsView(self.scrollAreaWidgetContents)
        self.image_container.setObjectName(u"image_container")
        sizePolicy.setHeightForWidth(self.image_container.sizePolicy().hasHeightForWidth())
        self.image_container.setSizePolicy(sizePolicy)
        self.image_container.setMinimumSize(QSize(512, 512))

        self.gridLayout_2.addWidget(self.image_container, 2, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(10)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.use_grid_image_as_input_checkbox = QCheckBox(self.scrollAreaWidgetContents)
        self.use_grid_image_as_input_checkbox.setObjectName(u"use_grid_image_as_input_checkbox")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.use_grid_image_as_input_checkbox.sizePolicy().hasHeightForWidth())
        self.use_grid_image_as_input_checkbox.setSizePolicy(sizePolicy2)

        self.horizontalLayout.addWidget(self.use_grid_image_as_input_checkbox)

        self.enable_checkbox = QCheckBox(self.scrollAreaWidgetContents)
        self.enable_checkbox.setObjectName(u"enable_checkbox")
        sizePolicy2.setHeightForWidth(self.enable_checkbox.sizePolicy().hasHeightForWidth())
        self.enable_checkbox.setSizePolicy(sizePolicy2)

        self.horizontalLayout.addWidget(self.enable_checkbox)

        self.import_button = QPushButton(self.scrollAreaWidgetContents)
        self.import_button.setObjectName(u"import_button")
        icon = QIcon(QIcon.fromTheme(u"folder"))
        self.import_button.setIcon(icon)

        self.horizontalLayout.addWidget(self.import_button)

        self.delete_button = QPushButton(self.scrollAreaWidgetContents)
        self.delete_button.setObjectName(u"delete_button")
        icon1 = QIcon(QIcon.fromTheme(u"user-trash"))
        self.delete_button.setIcon(icon1)

        self.horizontalLayout.addWidget(self.delete_button)


        self.gridLayout_2.addLayout(self.horizontalLayout, 4, 0, 1, 1)

        self.label = QLabel(self.scrollAreaWidgetContents)
        self.label.setObjectName(u"label")

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)

        self.controlnet_settings = ControlnetSettingsWidget(self.scrollAreaWidgetContents)
        self.controlnet_settings.setObjectName(u"controlnet_settings")

        self.gridLayout_2.addWidget(self.controlnet_settings, 5, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout.addWidget(self.scrollArea, 0, 0, 1, 1)


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
        self.use_grid_image_as_input_checkbox.setText(QCoreApplication.translate("input_image", u"Use grid image as input", None))
        self.enable_checkbox.setText(QCoreApplication.translate("input_image", u"Enable ", None))
        self.import_button.setText(QCoreApplication.translate("input_image", u"Import", None))
        self.delete_button.setText(QCoreApplication.translate("input_image", u"Delete", None))
        self.label.setText(QCoreApplication.translate("input_image", u"TextLabel", None))
    # retranslateUi

