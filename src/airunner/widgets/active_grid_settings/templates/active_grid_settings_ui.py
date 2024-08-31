# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'active_grid_settings.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QSizePolicy, QSpacerItem, QWidget)

from airunner.widgets.slider.slider_widget import SliderWidget

class Ui_active_grid_settings_widget(object):
    def setupUi(self, active_grid_settings_widget):
        if not active_grid_settings_widget.objectName():
            active_grid_settings_widget.setObjectName(u"active_grid_settings_widget")
        active_grid_settings_widget.resize(724, 663)
        self.gridLayout = QGridLayout(active_grid_settings_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setVerticalSpacing(10)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.line = QFrame(active_grid_settings_widget)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 1, 0, 1, 1)

        self.active_grid_area_groupbox = QGroupBox(active_grid_settings_widget)
        self.active_grid_area_groupbox.setObjectName(u"active_grid_area_groupbox")
        self.active_grid_area_groupbox.setCheckable(True)
        self.active_grid_area_groupbox.setChecked(False)
        self.gridLayout_4 = QGridLayout(self.active_grid_area_groupbox)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.gridLayout_4.setVerticalSpacing(0)
        self.gridLayout_4.setContentsMargins(0, 0, 0, 0)
        self.scrollArea = QScrollArea(self.active_grid_area_groupbox)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setFrameShape(QFrame.Shape.NoFrame)
        self.scrollArea.setFrameShadow(QFrame.Shadow.Plain)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 718, 577))
        self.gridLayout_3 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setVerticalSpacing(10)
        self.gridLayout_3.setContentsMargins(10, 10, 10, 0)
        self.groupBox_3 = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_3.setObjectName(u"groupBox_3")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox_3.sizePolicy().hasHeightForWidth())
        self.groupBox_3.setSizePolicy(sizePolicy)
        self.groupBox_3.setMinimumSize(QSize(0, 80))
        self.horizontalLayout = QHBoxLayout(self.groupBox_3)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.width_slider_widget = SliderWidget(self.groupBox_3)
        self.width_slider_widget.setObjectName(u"width_slider_widget")
        self.width_slider_widget.setMinimumSize(QSize(0, 20))
        self.width_slider_widget.setProperty("slider_minimum", 64)
        self.width_slider_widget.setProperty("slider_maximum", 4096)
        self.width_slider_widget.setProperty("spinbox_minimum", 64)
        self.width_slider_widget.setProperty("spinbox_maximum", 4096)
        self.width_slider_widget.setProperty("slider_tick_interval", 64)
        self.width_slider_widget.setProperty("slider_single_step", 64)
        self.width_slider_widget.setProperty("slider_page_step", 64)
        self.width_slider_widget.setProperty("spinbox_single_step", 64)
        self.width_slider_widget.setProperty("spinbox_page_step", 64)
        self.width_slider_widget.setProperty("settings_property", u"working_width")
        self.width_slider_widget.setProperty("display_as_float", False)

        self.horizontalLayout.addWidget(self.width_slider_widget)

        self.height_slider_widget = SliderWidget(self.groupBox_3)
        self.height_slider_widget.setObjectName(u"height_slider_widget")
        self.height_slider_widget.setMinimumSize(QSize(0, 20))
        self.height_slider_widget.setProperty("slider_minimum", 64)
        self.height_slider_widget.setProperty("slider_maximum", 4096)
        self.height_slider_widget.setProperty("spinbox_minimum", 64)
        self.height_slider_widget.setProperty("spinbox_maximum", 4096)
        self.height_slider_widget.setProperty("slider_tick_interval", 64)
        self.height_slider_widget.setProperty("slider_single_step", 64)
        self.height_slider_widget.setProperty("slider_page_step", 64)
        self.height_slider_widget.setProperty("spinbox_single_step", 64)
        self.height_slider_widget.setProperty("spinbox_page_step", 64)
        self.height_slider_widget.setProperty("display_as_float", False)

        self.horizontalLayout.addWidget(self.height_slider_widget)


        self.gridLayout_3.addWidget(self.groupBox_3, 0, 0, 1, 1)

        self.active_grid_border_groupbox = QGroupBox(self.scrollAreaWidgetContents)
        self.active_grid_border_groupbox.setObjectName(u"active_grid_border_groupbox")
        sizePolicy.setHeightForWidth(self.active_grid_border_groupbox.sizePolicy().hasHeightForWidth())
        self.active_grid_border_groupbox.setSizePolicy(sizePolicy)
        self.active_grid_border_groupbox.setMinimumSize(QSize(0, 80))
        self.active_grid_border_groupbox.setCheckable(True)
        self.active_grid_border_groupbox.setChecked(False)
        self.horizontalLayout_2 = QHBoxLayout(self.active_grid_border_groupbox)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.border_opacity_slider_widget = SliderWidget(self.active_grid_border_groupbox)
        self.border_opacity_slider_widget.setObjectName(u"border_opacity_slider_widget")
        self.border_opacity_slider_widget.setProperty("spinbox_single_step", 0.010000000000000)
        self.border_opacity_slider_widget.setProperty("slider_page_step", 1)
        self.border_opacity_slider_widget.setProperty("spinbox_page_step", 0.100000000000000)
        self.border_opacity_slider_widget.setProperty("display_as_float", True)
        self.border_opacity_slider_widget.setProperty("slider_minimum", 0)
        self.border_opacity_slider_widget.setProperty("slider_maximum", 255)
        self.border_opacity_slider_widget.setProperty("spinbox_minimum", 0.000000000000000)
        self.border_opacity_slider_widget.setProperty("spinbox_maximum", 1.000000000000000)
        self.border_opacity_slider_widget.setProperty("slider_tick_interval", 1.000000000000000)
        self.border_opacity_slider_widget.setProperty("slider_singlestep", 1)

        self.horizontalLayout_2.addWidget(self.border_opacity_slider_widget)

        self.border_choose_color_button = QPushButton(self.active_grid_border_groupbox)
        self.border_choose_color_button.setObjectName(u"border_choose_color_button")
        self.border_choose_color_button.setCursor(QCursor(Qt.PointingHandCursor))

        self.horizontalLayout_2.addWidget(self.border_choose_color_button)


        self.gridLayout_3.addWidget(self.active_grid_border_groupbox, 1, 0, 1, 1)

        self.active_grid_fill_groupbox = QGroupBox(self.scrollAreaWidgetContents)
        self.active_grid_fill_groupbox.setObjectName(u"active_grid_fill_groupbox")
        sizePolicy.setHeightForWidth(self.active_grid_fill_groupbox.sizePolicy().hasHeightForWidth())
        self.active_grid_fill_groupbox.setSizePolicy(sizePolicy)
        self.active_grid_fill_groupbox.setMinimumSize(QSize(0, 80))
        self.active_grid_fill_groupbox.setCheckable(True)
        self.active_grid_fill_groupbox.setChecked(False)
        self.horizontalLayout_3 = QHBoxLayout(self.active_grid_fill_groupbox)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.fill_opacity_slider_widget = SliderWidget(self.active_grid_fill_groupbox)
        self.fill_opacity_slider_widget.setObjectName(u"fill_opacity_slider_widget")
        self.fill_opacity_slider_widget.setProperty("spinbox_single_step", 0.010000000000000)
        self.fill_opacity_slider_widget.setProperty("slider_page_step", 1)
        self.fill_opacity_slider_widget.setProperty("spinbox_page_step", 0.100000000000000)
        self.fill_opacity_slider_widget.setProperty("display_as_float", True)
        self.fill_opacity_slider_widget.setProperty("slider_minimum", 0)
        self.fill_opacity_slider_widget.setProperty("slider_maximum", 255)
        self.fill_opacity_slider_widget.setProperty("spinbox_minimum", 0.000000000000000)
        self.fill_opacity_slider_widget.setProperty("spinbox_maximum", 1.000000000000000)
        self.fill_opacity_slider_widget.setProperty("slider_tick_interval", 1.000000000000000)
        self.fill_opacity_slider_widget.setProperty("slider_singlestep", 1)

        self.horizontalLayout_3.addWidget(self.fill_opacity_slider_widget)

        self.fill_choose_color_button = QPushButton(self.active_grid_fill_groupbox)
        self.fill_choose_color_button.setObjectName(u"fill_choose_color_button")
        self.fill_choose_color_button.setCursor(QCursor(Qt.PointingHandCursor))

        self.horizontalLayout_3.addWidget(self.fill_choose_color_button)


        self.gridLayout_3.addWidget(self.active_grid_fill_groupbox, 2, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 139, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_3.addItem(self.verticalSpacer, 3, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_4.addWidget(self.scrollArea, 3, 0, 1, 1)


        self.gridLayout.addWidget(self.active_grid_area_groupbox, 2, 0, 1, 1)

        self.widget = QWidget(active_grid_settings_widget)
        self.widget.setObjectName(u"widget")
        sizePolicy.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy)
        self.widget.setMinimumSize(QSize(0, 37))
        self.gridLayout_2 = QGridLayout(self.widget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setVerticalSpacing(0)
        self.gridLayout_2.setContentsMargins(10, 10, 10, 0)
        self.label = QLabel(self.widget)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.widget, 0, 0, 1, 1)


        self.retranslateUi(active_grid_settings_widget)
        self.active_grid_border_groupbox.toggled.connect(active_grid_settings_widget.action_clicked_checkbox_toggle_active_grid_border)
        self.active_grid_fill_groupbox.toggled.connect(active_grid_settings_widget.action_clicked_checkbox_toggle_active_grid_fill)
        self.active_grid_area_groupbox.toggled.connect(active_grid_settings_widget.action_clicked_checkbox_toggle_active_grid_area)
        self.border_choose_color_button.clicked.connect(active_grid_settings_widget.action_choose_border_color_clicked)
        self.fill_choose_color_button.clicked.connect(active_grid_settings_widget.action_choose_fill_color_clicked)

        QMetaObject.connectSlotsByName(active_grid_settings_widget)
    # setupUi

    def retranslateUi(self, active_grid_settings_widget):
        active_grid_settings_widget.setWindowTitle(QCoreApplication.translate("active_grid_settings_widget", u"Form", None))
        self.active_grid_area_groupbox.setTitle(QCoreApplication.translate("active_grid_settings_widget", u"Enable", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("active_grid_settings_widget", u"Active Grid Size", None))
        self.width_slider_widget.setProperty("label_text", QCoreApplication.translate("active_grid_settings_widget", u"Width", None))
        self.height_slider_widget.setProperty("label_text", QCoreApplication.translate("active_grid_settings_widget", u"Height", None))
        self.height_slider_widget.setProperty("settings_property", QCoreApplication.translate("active_grid_settings_widget", u"working_height", None))
        self.active_grid_border_groupbox.setTitle(QCoreApplication.translate("active_grid_settings_widget", u"Border", None))
        self.border_opacity_slider_widget.setProperty("label_text", QCoreApplication.translate("active_grid_settings_widget", u"Border Opacity", None))
        self.border_opacity_slider_widget.setProperty("settings_property", QCoreApplication.translate("active_grid_settings_widget", u"active_grid_settings.border_opacity", None))
        self.border_choose_color_button.setText("")
        self.active_grid_fill_groupbox.setTitle(QCoreApplication.translate("active_grid_settings_widget", u"Fill", None))
        self.fill_opacity_slider_widget.setProperty("label_text", QCoreApplication.translate("active_grid_settings_widget", u"Fill Opacity", None))
        self.fill_opacity_slider_widget.setProperty("settings_property", QCoreApplication.translate("active_grid_settings_widget", u"active_grid_settings.fill_opacity", None))
        self.fill_choose_color_button.setText("")
        self.label.setText(QCoreApplication.translate("active_grid_settings_widget", u"Active Grid Area", None))
    # retranslateUi

