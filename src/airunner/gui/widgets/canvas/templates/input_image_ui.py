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
from PySide6.QtWidgets import (QApplication, QGraphicsView, QGridLayout, QHBoxLayout,
    QPushButton, QScrollArea, QSizePolicy, QSpacerItem,
    QWidget)

from airunner.gui.widgets.controlnet.controlnet_settings_widget import ControlnetSettingsWidget
from airunner.gui.widgets.slider.slider_widget import SliderWidget
from airunner.gui.widgets.switch_widget.switch_widget import SwitchWidget
import airunner.feather_rc

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
        self.link_to_grid_image_button = QPushButton(input_image)
        self.link_to_grid_image_button.setObjectName(u"link_to_grid_image_button")
        icon = QIcon()
        icon.addFile(u":/light/icons/feather/light/link.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.link_to_grid_image_button.setIcon(icon)
        self.link_to_grid_image_button.setCheckable(True)

        self.horizontalLayout.addWidget(self.link_to_grid_image_button)

        self.lock_input_image_button = QPushButton(input_image)
        self.lock_input_image_button.setObjectName(u"lock_input_image_button")
        self.lock_input_image_button.setMinimumSize(QSize(24, 24))
        self.lock_input_image_button.setMaximumSize(QSize(24, 24))
        icon1 = QIcon()
        icon1.addFile(u":/light/icons/feather/light/lock.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.lock_input_image_button.setIcon(icon1)
        self.lock_input_image_button.setCheckable(True)

        self.horizontalLayout.addWidget(self.lock_input_image_button)

        self.refresh_button = QPushButton(input_image)
        self.refresh_button.setObjectName(u"refresh_button")
        icon2 = QIcon()
        icon2.addFile(u":/light/icons/feather/light/refresh-ccw.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.refresh_button.setIcon(icon2)

        self.horizontalLayout.addWidget(self.refresh_button)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.EnableSwitch = SwitchWidget(input_image)
        self.EnableSwitch.setObjectName(u"EnableSwitch")
        self.EnableSwitch.setMinimumSize(QSize(45, 20))
        self.EnableSwitch.setMaximumSize(QSize(45, 20))

        self.horizontalLayout.addWidget(self.EnableSwitch)

        self.import_button = QPushButton(input_image)
        self.import_button.setObjectName(u"import_button")
        icon3 = QIcon()
        icon3.addFile(u":/light/icons/feather/light/folder.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.import_button.setIcon(icon3)

        self.horizontalLayout.addWidget(self.import_button)

        self.delete_button = QPushButton(input_image)
        self.delete_button.setObjectName(u"delete_button")
        icon4 = QIcon()
        icon4.addFile(u":/light/icons/feather/light/trash-2.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.delete_button.setIcon(icon4)

        self.horizontalLayout.addWidget(self.delete_button)


        self.gridLayout_3.addLayout(self.horizontalLayout, 2, 0, 1, 1)


        self.retranslateUi(input_image)
        self.import_button.clicked.connect(input_image.import_clicked)
        self.delete_button.clicked.connect(input_image.delete_clicked)
        self.link_to_grid_image_button.toggled.connect(input_image.use_grid_image_as_input_toggled)
        self.lock_input_image_button.toggled.connect(input_image.lock_input_image)
        self.refresh_button.clicked.connect(input_image.refresh_input_image_from_grid)

        QMetaObject.connectSlotsByName(input_image)
    # setupUi

    def retranslateUi(self, input_image):
        input_image.setWindowTitle(QCoreApplication.translate("input_image", u"Form", None))
        self.strength_slider_widget.setProperty("label_text", QCoreApplication.translate("input_image", u"Strength", None))
        self.strength_slider_widget.setProperty("settings_property", QCoreApplication.translate("input_image", u"generator_settings.strength", None))
        self.mask_blur_slider_widget.setProperty("label_text", QCoreApplication.translate("input_image", u"Mask Blur", None))
        self.mask_blur_slider_widget.setProperty("settings_property", QCoreApplication.translate("input_image", u"outpaint_settings.mask_blur", None))
#if QT_CONFIG(tooltip)
        self.link_to_grid_image_button.setToolTip(QCoreApplication.translate("input_image", u"Link to Grid image", None))
#endif // QT_CONFIG(tooltip)
        self.link_to_grid_image_button.setText("")
#if QT_CONFIG(tooltip)
        self.lock_input_image_button.setToolTip(QCoreApplication.translate("input_image", u"Lock current input image", None))
#endif // QT_CONFIG(tooltip)
        self.lock_input_image_button.setText("")
#if QT_CONFIG(tooltip)
        self.refresh_button.setToolTip(QCoreApplication.translate("input_image", u"Refresh from grid image", None))
#endif // QT_CONFIG(tooltip)
        self.refresh_button.setText("")
#if QT_CONFIG(tooltip)
        self.import_button.setToolTip(QCoreApplication.translate("input_image", u"Import", None))
#endif // QT_CONFIG(tooltip)
        self.import_button.setText("")
#if QT_CONFIG(tooltip)
        self.delete_button.setToolTip(QCoreApplication.translate("input_image", u"Delete", None))
#endif // QT_CONFIG(tooltip)
        self.delete_button.setText("")
    # retranslateUi

