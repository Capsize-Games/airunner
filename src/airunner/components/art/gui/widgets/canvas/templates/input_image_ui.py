# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'input_image.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
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

from airunner.components.application.gui.widgets.slider.slider_widget import SliderWidget
from airunner.components.art.gui.widgets.controlnet.controlnet_settings_widget import ControlnetSettingsWidget
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
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 579, 496))
        self.gridLayout_2 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_2.setSpacing(0)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.image_container = QGraphicsView(self.scrollAreaWidgetContents)
        self.image_container.setObjectName(u"image_container")
        sizePolicy.setHeightForWidth(self.image_container.sizePolicy().hasHeightForWidth())
        self.image_container.setSizePolicy(sizePolicy)
        self.image_container.setMinimumSize(QSize(0, 0))

        self.gridLayout_2.addWidget(self.image_container, 0, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_3.addWidget(self.scrollArea, 0, 0, 1, 1)

        self.verticalWidget = QWidget(input_image)
        self.verticalWidget.setObjectName(u"verticalWidget")
        self.gridLayout = QGridLayout(self.verticalWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(0)
        self.gridLayout.setVerticalSpacing(5)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.strength_slider_widget = SliderWidget(self.verticalWidget)
        self.strength_slider_widget.setObjectName(u"strength_slider_widget")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.strength_slider_widget.sizePolicy().hasHeightForWidth())
        self.strength_slider_widget.setSizePolicy(sizePolicy1)
        self.strength_slider_widget.setProperty(u"slider_maximum", 100)
        self.strength_slider_widget.setProperty(u"current_value", 0)
        self.strength_slider_widget.setProperty(u"spinbox_maximum", 1.000000000000000)
        self.strength_slider_widget.setProperty(u"display_as_float", True)
        self.strength_slider_widget.setProperty(u"spinbox_single_step", 0.010000000000000)
        self.strength_slider_widget.setProperty(u"spinbox_page_step", 0.100000000000000)

        self.gridLayout.addWidget(self.strength_slider_widget, 0, 0, 1, 1)

        self.mask_blur_slider_widget = SliderWidget(self.verticalWidget)
        self.mask_blur_slider_widget.setObjectName(u"mask_blur_slider_widget")
        sizePolicy1.setHeightForWidth(self.mask_blur_slider_widget.sizePolicy().hasHeightForWidth())
        self.mask_blur_slider_widget.setSizePolicy(sizePolicy1)
        self.mask_blur_slider_widget.setProperty(u"slider_maximum", 100)
        self.mask_blur_slider_widget.setProperty(u"current_value", 0)
        self.mask_blur_slider_widget.setProperty(u"spinbox_maximum", 1.000000000000000)
        self.mask_blur_slider_widget.setProperty(u"display_as_float", True)
        self.mask_blur_slider_widget.setProperty(u"spinbox_single_step", 0.010000000000000)
        self.mask_blur_slider_widget.setProperty(u"spinbox_page_step", 0.100000000000000)

        self.gridLayout.addWidget(self.mask_blur_slider_widget, 1, 0, 1, 1)

        self.controlnet_settings = ControlnetSettingsWidget(self.verticalWidget)
        self.controlnet_settings.setObjectName(u"controlnet_settings")

        self.gridLayout.addWidget(self.controlnet_settings, 2, 0, 1, 1)


        self.gridLayout_3.addWidget(self.verticalWidget, 1, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(5)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, -1, 0, 0)
        self.pin_image = QPushButton(input_image)
        self.pin_image.setObjectName(u"pin_image")
        self.pin_image.setMinimumSize(QSize(28, 28))
        self.pin_image.setMaximumSize(QSize(28, 28))
        self.pin_image.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon = QIcon()
        icon.addFile(u":/light/icons/lucide/light/pin.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.pin_image.setIcon(icon)
        self.pin_image.setCheckable(True)

        self.horizontalLayout.addWidget(self.pin_image)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.grid_image = QPushButton(input_image)
        self.grid_image.setObjectName(u"grid_image")
        self.grid_image.setMinimumSize(QSize(28, 28))
        self.grid_image.setMaximumSize(QSize(28, 28))
        icon1 = QIcon()
        icon1.addFile(u":/light/icons/lucide/light/grid-3x3.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.grid_image.setIcon(icon1)

        self.horizontalLayout.addWidget(self.grid_image)

        self.import_button = QPushButton(input_image)
        self.import_button.setObjectName(u"import_button")
        self.import_button.setMinimumSize(QSize(28, 28))
        self.import_button.setMaximumSize(QSize(28, 28))
        self.import_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon2 = QIcon()
        icon2.addFile(u":/light/icons/feather/light/folder.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.import_button.setIcon(icon2)

        self.horizontalLayout.addWidget(self.import_button)


        self.gridLayout_3.addLayout(self.horizontalLayout, 2, 0, 1, 1)


        self.retranslateUi(input_image)

        QMetaObject.connectSlotsByName(input_image)
    # setupUi

    def retranslateUi(self, input_image):
        input_image.setWindowTitle(QCoreApplication.translate("input_image", u"Form", None))
        self.strength_slider_widget.setProperty(u"label_text", QCoreApplication.translate("input_image", u"Strength", None))
        self.strength_slider_widget.setProperty(u"settings_property", QCoreApplication.translate("input_image", u"generator_settings.strength", None))
        self.mask_blur_slider_widget.setProperty(u"label_text", QCoreApplication.translate("input_image", u"Mask Blur", None))
        self.mask_blur_slider_widget.setProperty(u"settings_property", QCoreApplication.translate("input_image", u"outpaint_settings.mask_blur", None))
#if QT_CONFIG(tooltip)
        self.pin_image.setToolTip(QCoreApplication.translate("input_image", u"Pin current image", None))
#endif // QT_CONFIG(tooltip)
        self.pin_image.setText("")
#if QT_CONFIG(tooltip)
        self.grid_image.setToolTip(QCoreApplication.translate("input_image", u"Use grid image", None))
#endif // QT_CONFIG(tooltip)
        self.grid_image.setText("")
#if QT_CONFIG(tooltip)
        self.import_button.setToolTip(QCoreApplication.translate("input_image", u"Import image", None))
#endif // QT_CONFIG(tooltip)
        self.import_button.setText("")
    # retranslateUi

