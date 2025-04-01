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
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QSizePolicy, QSpacerItem, QWidget)

from airunner.gui.widgets.slider.slider_widget import SliderWidget

class Ui_active_grid_settings_widget(object):
    def setupUi(self, active_grid_settings_widget):
        if not active_grid_settings_widget.objectName():
            active_grid_settings_widget.setObjectName(u"active_grid_settings_widget")
        active_grid_settings_widget.resize(724, 369)
        self.gridLayout = QGridLayout(active_grid_settings_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(0)
        self.gridLayout.setVerticalSpacing(10)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.scrollArea = QScrollArea(active_grid_settings_widget)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setFrameShape(QFrame.Shape.NoFrame)
        self.scrollArea.setFrameShadow(QFrame.Shadow.Plain)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 724, 296))
        self.gridLayout_3 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setHorizontalSpacing(0)
        self.gridLayout_3.setVerticalSpacing(10)
        self.gridLayout_3.setContentsMargins(0, 0, 10, 0)
        self.groupBox_3 = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_3.setObjectName(u"groupBox_3")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox_3.sizePolicy().hasHeightForWidth())
        self.groupBox_3.setSizePolicy(sizePolicy)
        self.groupBox_3.setMinimumSize(QSize(0, 0))
        self.groupBox_3.setFlat(False)
        self.horizontalLayout = QHBoxLayout(self.groupBox_3)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
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
        self.width_slider_widget.setProperty("settings_property", u"application_settings.working_width")
        self.width_slider_widget.setProperty("display_as_float", False)

        self.horizontalLayout.addWidget(self.width_slider_widget)

        self.size_lock_button = QPushButton(self.groupBox_3)
        self.size_lock_button.setObjectName(u"size_lock_button")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.size_lock_button.sizePolicy().hasHeightForWidth())
        self.size_lock_button.setSizePolicy(sizePolicy1)
        icon = QIcon(QIcon.fromTheme(u"system-lock-screen"))
        self.size_lock_button.setIcon(icon)
        self.size_lock_button.setCheckable(True)

        self.horizontalLayout.addWidget(self.size_lock_button)

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
        self.active_grid_border_groupbox.setMinimumSize(QSize(0, 0))
        self.active_grid_border_groupbox.setCheckable(True)
        self.active_grid_border_groupbox.setChecked(False)
        self.horizontalLayout_3 = QHBoxLayout(self.active_grid_border_groupbox)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
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

        self.horizontalLayout_3.addWidget(self.border_opacity_slider_widget)

        self.border_choose_color_button = QPushButton(self.active_grid_border_groupbox)
        self.border_choose_color_button.setObjectName(u"border_choose_color_button")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.border_choose_color_button.sizePolicy().hasHeightForWidth())
        self.border_choose_color_button.setSizePolicy(sizePolicy2)
        self.border_choose_color_button.setCursor(QCursor(Qt.PointingHandCursor))

        self.horizontalLayout_3.addWidget(self.border_choose_color_button)


        self.gridLayout_3.addWidget(self.active_grid_border_groupbox, 1, 0, 1, 1)

        self.active_grid_fill_groupbox = QGroupBox(self.scrollAreaWidgetContents)
        self.active_grid_fill_groupbox.setObjectName(u"active_grid_fill_groupbox")
        sizePolicy.setHeightForWidth(self.active_grid_fill_groupbox.sizePolicy().hasHeightForWidth())
        self.active_grid_fill_groupbox.setSizePolicy(sizePolicy)
        self.active_grid_fill_groupbox.setMinimumSize(QSize(0, 0))
        self.active_grid_fill_groupbox.setCheckable(True)
        self.active_grid_fill_groupbox.setChecked(False)
        self.horizontalLayout_2 = QHBoxLayout(self.active_grid_fill_groupbox)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
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

        self.horizontalLayout_2.addWidget(self.fill_opacity_slider_widget)

        self.fill_choose_color_button = QPushButton(self.active_grid_fill_groupbox)
        self.fill_choose_color_button.setObjectName(u"fill_choose_color_button")
        sizePolicy2.setHeightForWidth(self.fill_choose_color_button.sizePolicy().hasHeightForWidth())
        self.fill_choose_color_button.setSizePolicy(sizePolicy2)
        self.fill_choose_color_button.setCursor(QCursor(Qt.PointingHandCursor))

        self.horizontalLayout_2.addWidget(self.fill_choose_color_button)


        self.gridLayout_3.addWidget(self.active_grid_fill_groupbox, 2, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 139, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_3.addItem(self.verticalSpacer, 3, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout.addWidget(self.scrollArea, 3, 0, 1, 1)

        self.label = QLabel(active_grid_settings_widget)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.active_grid_area_checkbox = QCheckBox(active_grid_settings_widget)
        self.active_grid_area_checkbox.setObjectName(u"active_grid_area_checkbox")
        font1 = QFont()
        font1.setBold(False)
        self.active_grid_area_checkbox.setFont(font1)

        self.gridLayout.addWidget(self.active_grid_area_checkbox, 2, 0, 1, 1)

        self.line = QFrame(active_grid_settings_widget)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 1, 0, 1, 1)


        self.retranslateUi(active_grid_settings_widget)
        self.active_grid_area_checkbox.clicked["bool"].connect(active_grid_settings_widget.action_clicked_checkbox_toggle_active_grid_area)
        self.size_lock_button.toggled.connect(active_grid_settings_widget.size_lock_toggled)
        self.border_choose_color_button.clicked.connect(active_grid_settings_widget.action_choose_border_color_clicked)
        self.fill_choose_color_button.clicked.connect(active_grid_settings_widget.action_choose_fill_color_clicked)

        QMetaObject.connectSlotsByName(active_grid_settings_widget)
    # setupUi

    def retranslateUi(self, active_grid_settings_widget):
        active_grid_settings_widget.setWindowTitle(QCoreApplication.translate("active_grid_settings_widget", u"Form", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("active_grid_settings_widget", u"Size", None))
        self.width_slider_widget.setProperty("label_text", QCoreApplication.translate("active_grid_settings_widget", u"Width", None))
        self.size_lock_button.setText("")
        self.height_slider_widget.setProperty("label_text", QCoreApplication.translate("active_grid_settings_widget", u"Height", None))
        self.height_slider_widget.setProperty("settings_property", QCoreApplication.translate("active_grid_settings_widget", u"application_settings.working_height", None))
        self.active_grid_border_groupbox.setTitle(QCoreApplication.translate("active_grid_settings_widget", u"Border", None))
        self.border_opacity_slider_widget.setProperty("label_text", QCoreApplication.translate("active_grid_settings_widget", u"Border Opacity", None))
        self.border_opacity_slider_widget.setProperty("settings_property", QCoreApplication.translate("active_grid_settings_widget", u"active_grid_settings.border_opacity", None))
        self.border_choose_color_button.setText(QCoreApplication.translate("active_grid_settings_widget", u"Color", None))
        self.active_grid_fill_groupbox.setTitle(QCoreApplication.translate("active_grid_settings_widget", u"Fill", None))
        self.fill_opacity_slider_widget.setProperty("label_text", QCoreApplication.translate("active_grid_settings_widget", u"Fill Opacity", None))
        self.fill_opacity_slider_widget.setProperty("settings_property", QCoreApplication.translate("active_grid_settings_widget", u"active_grid_settings.fill_opacity", None))
        self.fill_choose_color_button.setText(QCoreApplication.translate("active_grid_settings_widget", u"Color", None))
        self.label.setText(QCoreApplication.translate("active_grid_settings_widget", u"Active Grid Settings", None))
        self.active_grid_area_checkbox.setText(QCoreApplication.translate("active_grid_settings_widget", u"Enable Active Grid Area", None))
    # retranslateUi

