# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'lora_container.ui'
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
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)

from airunner.gui.widgets.llm.loading_widget import LoadingWidget
from airunner.gui.widgets.slider.slider_widget import SliderWidget

class Ui_lora_container(object):
    def setupUi(self, lora_container):
        if not lora_container.objectName():
            lora_container.setObjectName(u"lora_container")
        lora_container.resize(583, 831)
        self.gridLayout = QGridLayout(lora_container)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(0)
        self.gridLayout.setVerticalSpacing(10)
        self.gridLayout.setContentsMargins(10, 10, 10, 10)
        self.pushButton = QPushButton(lora_container)
        self.pushButton.setObjectName(u"pushButton")

        self.gridLayout.addWidget(self.pushButton, 8, 0, 1, 1)

        self.lora_scroll_area = QScrollArea(lora_container)
        self.lora_scroll_area.setObjectName(u"lora_scroll_area")
        font = QFont()
        font.setPointSize(9)
        self.lora_scroll_area.setFont(font)
        self.lora_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.lora_scroll_area.setFrameShadow(QFrame.Shadow.Plain)
        self.lora_scroll_area.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 563, 652))
        self.gridLayout_2 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setHorizontalSpacing(0)
        self.gridLayout_2.setVerticalSpacing(10)
        self.gridLayout_2.setContentsMargins(0, 0, 10, 0)
        self.lora_scroll_area.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout.addWidget(self.lora_scroll_area, 7, 0, 1, 1)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setSpacing(10)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 10, 10)
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(-1, -1, 0, -1)
        self.label = QLabel(lora_container)
        self.label.setObjectName(u"label")
        font1 = QFont()
        font1.setBold(False)
        self.label.setFont(font1)

        self.horizontalLayout_2.addWidget(self.label)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)

        self.loading_icon = LoadingWidget(lora_container)
        self.loading_icon.setObjectName(u"loading_icon")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.loading_icon.sizePolicy().hasHeightForWidth())
        self.loading_icon.setSizePolicy(sizePolicy)
        self.loading_icon.setMinimumSize(QSize(0, 0))

        self.horizontalLayout_2.addWidget(self.loading_icon)

        self.apply_lora_button = QPushButton(lora_container)
        self.apply_lora_button.setObjectName(u"apply_lora_button")

        self.horizontalLayout_2.addWidget(self.apply_lora_button)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.line = QFrame(lora_container)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout.addWidget(self.line)

        self.lora_scale_slider = SliderWidget(lora_container)
        self.lora_scale_slider.setObjectName(u"lora_scale_slider")
        sizePolicy.setHeightForWidth(self.lora_scale_slider.sizePolicy().hasHeightForWidth())
        self.lora_scale_slider.setSizePolicy(sizePolicy)
        self.lora_scale_slider.setMinimumSize(QSize(0, 0))
        self.lora_scale_slider.setProperty("slider_minimum", 0)
        self.lora_scale_slider.setProperty("slider_maximum", 100)
        self.lora_scale_slider.setProperty("spinbox_minimum", 0.000000000000000)
        self.lora_scale_slider.setProperty("spinbox_maximum", 1.000000000000000)
        self.lora_scale_slider.setProperty("display_as_float", True)
        self.lora_scale_slider.setProperty("slider_single_step", 1)
        self.lora_scale_slider.setProperty("slider_page_step", 5)
        self.lora_scale_slider.setProperty("spinbox_single_step", 0.010000000000000)
        self.lora_scale_slider.setProperty("spinbox_page_step", 0.100000000000000)

        self.verticalLayout.addWidget(self.lora_scale_slider)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(10)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, -1, 0, -1)
        self.lineEdit = QLineEdit(lora_container)
        self.lineEdit.setObjectName(u"lineEdit")

        self.horizontalLayout.addWidget(self.lineEdit)

        self.toggleAllLora = QCheckBox(lora_container)
        self.toggleAllLora.setObjectName(u"toggleAllLora")
        self.toggleAllLora.setFont(font)
        self.toggleAllLora.setChecked(False)
        self.toggleAllLora.setTristate(False)

        self.horizontalLayout.addWidget(self.toggleAllLora)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.line_2 = QFrame(lora_container)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout.addWidget(self.line_2)


        self.gridLayout.addLayout(self.verticalLayout, 2, 0, 1, 1)


        self.retranslateUi(lora_container)
        self.toggleAllLora.toggled.connect(lora_container.toggle_all)
        self.lineEdit.textEdited.connect(lora_container.search_text_changed)
        self.pushButton.clicked.connect(lora_container.scan_for_lora)
        self.apply_lora_button.clicked.connect(lora_container.apply_lora)

        QMetaObject.connectSlotsByName(lora_container)
    # setupUi

    def retranslateUi(self, lora_container):
        lora_container.setWindowTitle(QCoreApplication.translate("lora_container", u"Form", None))
        self.pushButton.setText(QCoreApplication.translate("lora_container", u"Scan for LoRA", None))
        self.label.setText(QCoreApplication.translate("lora_container", u"Lora", None))
        self.apply_lora_button.setText(QCoreApplication.translate("lora_container", u"Apply Changes", None))
        self.lora_scale_slider.setProperty("settings_property", QCoreApplication.translate("lora_container", u"generator_settings.lora_scale", None))
        self.lora_scale_slider.setProperty("label_text", QCoreApplication.translate("lora_container", u"Scale", None))
        self.lineEdit.setPlaceholderText(QCoreApplication.translate("lora_container", u"Search", None))
        self.toggleAllLora.setText(QCoreApplication.translate("lora_container", u"Toggle all", None))
    # retranslateUi

