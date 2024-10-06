# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'stable_diffusion_settings.ui'
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
    QGridLayout, QLabel, QScrollArea, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)

from airunner.widgets.seed.seed_widget import SeedWidget
from airunner.widgets.slider.slider_widget import SliderWidget
import airunner.resources_light_rc

class Ui_stable_diffusion_settings_widget(object):
    def setupUi(self, stable_diffusion_settings_widget):
        if not stable_diffusion_settings_widget.objectName():
            stable_diffusion_settings_widget.setObjectName(u"stable_diffusion_settings_widget")
        stable_diffusion_settings_widget.resize(411, 964)
        stable_diffusion_settings_widget.setMaximumSize(QSize(16777215, 16777215))
        self.gridLayout_2 = QGridLayout(stable_diffusion_settings_widget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setHorizontalSpacing(0)
        self.gridLayout_2.setVerticalSpacing(10)
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.scrollArea = QScrollArea(stable_diffusion_settings_widget)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 409, 922))
        self.gridLayout = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(0)
        self.gridLayout.setVerticalSpacing(10)
        self.gridLayout.setContentsMargins(0, 0, 10, 0)
        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setSpacing(10)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.scale_widget = SliderWidget(self.scrollAreaWidgetContents)
        self.scale_widget.setObjectName(u"scale_widget")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scale_widget.sizePolicy().hasHeightForWidth())
        self.scale_widget.setSizePolicy(sizePolicy)
        self.scale_widget.setMinimumSize(QSize(0, 0))
        self.scale_widget.setProperty("current_value", 0)
        self.scale_widget.setProperty("slider_maximum", 10000)
        self.scale_widget.setProperty("spinbox_maximum", 100.000000000000000)
        self.scale_widget.setProperty("display_as_float", True)
        self.scale_widget.setProperty("spinbox_single_step", 0.010000000000000)
        self.scale_widget.setProperty("spinbox_page_step", 0.010000000000000)
        self.scale_widget.setProperty("settings_property", u"generator_settings.scale")

        self.verticalLayout_3.addWidget(self.scale_widget)

        self.steps_widget = SliderWidget(self.scrollAreaWidgetContents)
        self.steps_widget.setObjectName(u"steps_widget")
        sizePolicy.setHeightForWidth(self.steps_widget.sizePolicy().hasHeightForWidth())
        self.steps_widget.setSizePolicy(sizePolicy)
        self.steps_widget.setMinimumSize(QSize(0, 0))
        self.steps_widget.setProperty("current_value", 0)
        self.steps_widget.setProperty("slider_maximum", 200)
        self.steps_widget.setProperty("spinbox_maximum", 200.000000000000000)
        self.steps_widget.setProperty("display_as_float", False)
        self.steps_widget.setProperty("spinbox_single_step", 1)
        self.steps_widget.setProperty("spinbox_page_step", 1)
        self.steps_widget.setProperty("spinbox_minimum", 1)
        self.steps_widget.setProperty("slider_minimum", 1)
        self.steps_widget.setProperty("settings_property", u"generator_settings.steps")

        self.verticalLayout_3.addWidget(self.steps_widget)


        self.gridLayout.addLayout(self.verticalLayout_3, 6, 0, 1, 2)

        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.label_4 = QLabel(self.scrollAreaWidgetContents)
        self.label_4.setObjectName(u"label_4")
        font = QFont()
        font.setPointSize(8)
        font.setBold(True)
        self.label_4.setFont(font)

        self.verticalLayout_2.addWidget(self.label_4)

        self.scheduler = QComboBox(self.scrollAreaWidgetContents)
        self.scheduler.setObjectName(u"scheduler")
        sizePolicy.setHeightForWidth(self.scheduler.sizePolicy().hasHeightForWidth())
        self.scheduler.setSizePolicy(sizePolicy)
        self.scheduler.setCursor(QCursor(Qt.ArrowCursor))

        self.verticalLayout_2.addWidget(self.scheduler)


        self.gridLayout.addLayout(self.verticalLayout_2, 3, 0, 1, 2)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setSpacing(10)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.frames_slider_widget = SliderWidget(self.scrollAreaWidgetContents)
        self.frames_slider_widget.setObjectName(u"frames_slider_widget")
        sizePolicy.setHeightForWidth(self.frames_slider_widget.sizePolicy().hasHeightForWidth())
        self.frames_slider_widget.setSizePolicy(sizePolicy)
        self.frames_slider_widget.setMinimumSize(QSize(0, 0))
        self.frames_slider_widget.setProperty("current_value", 0)
        self.frames_slider_widget.setProperty("slider_maximum", 200)
        self.frames_slider_widget.setProperty("spinbox_maximum", 200.000000000000000)
        self.frames_slider_widget.setProperty("display_as_float", False)
        self.frames_slider_widget.setProperty("spinbox_single_step", 1)
        self.frames_slider_widget.setProperty("spinbox_page_step", 1)
        self.frames_slider_widget.setProperty("spinbox_minimum", 1)
        self.frames_slider_widget.setProperty("slider_minimum", 1)
        self.frames_slider_widget.setProperty("settings_property", u"generator_settings.n_samples")

        self.verticalLayout.addWidget(self.frames_slider_widget)

        self.ddim_eta_slider_widget = SliderWidget(self.scrollAreaWidgetContents)
        self.ddim_eta_slider_widget.setObjectName(u"ddim_eta_slider_widget")
        sizePolicy.setHeightForWidth(self.ddim_eta_slider_widget.sizePolicy().hasHeightForWidth())
        self.ddim_eta_slider_widget.setSizePolicy(sizePolicy)
        self.ddim_eta_slider_widget.setMinimumSize(QSize(0, 0))
        self.ddim_eta_slider_widget.setProperty("current_value", 1)
        self.ddim_eta_slider_widget.setProperty("slider_maximum", 10)
        self.ddim_eta_slider_widget.setProperty("spinbox_maximum", 10)
        self.ddim_eta_slider_widget.setProperty("display_as_float", False)
        self.ddim_eta_slider_widget.setProperty("spinbox_single_step", 1)
        self.ddim_eta_slider_widget.setProperty("spinbox_page_step", 1)
        self.ddim_eta_slider_widget.setProperty("spinbox_minimum", 1)
        self.ddim_eta_slider_widget.setProperty("slider_minimum", 1)
        self.ddim_eta_slider_widget.setProperty("settings_property", u"generator_settings.ddim_eta")

        self.verticalLayout.addWidget(self.ddim_eta_slider_widget)


        self.gridLayout.addLayout(self.verticalLayout, 5, 0, 1, 2)

        self.clip_skip_slider_widget = SliderWidget(self.scrollAreaWidgetContents)
        self.clip_skip_slider_widget.setObjectName(u"clip_skip_slider_widget")
        sizePolicy.setHeightForWidth(self.clip_skip_slider_widget.sizePolicy().hasHeightForWidth())
        self.clip_skip_slider_widget.setSizePolicy(sizePolicy)
        self.clip_skip_slider_widget.setMinimumSize(QSize(0, 0))
        self.clip_skip_slider_widget.setProperty("current_value", 0)
        self.clip_skip_slider_widget.setProperty("slider_maximum", 11)
        self.clip_skip_slider_widget.setProperty("spinbox_maximum", 12.000000000000000)
        self.clip_skip_slider_widget.setProperty("display_as_float", False)
        self.clip_skip_slider_widget.setProperty("spinbox_single_step", 1)
        self.clip_skip_slider_widget.setProperty("spinbox_page_step", 1)
        self.clip_skip_slider_widget.setProperty("spinbox_minimum", 0)
        self.clip_skip_slider_widget.setProperty("slider_minimum", 0)
        self.clip_skip_slider_widget.setProperty("settings_property", u"generator_settings.clip_skip")

        self.gridLayout.addWidget(self.clip_skip_slider_widget, 7, 0, 1, 2)

        self.verticalLayout_7 = QVBoxLayout()
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.label_6 = QLabel(self.scrollAreaWidgetContents)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setFont(font)

        self.verticalLayout_7.addWidget(self.label_6)

        self.version = QComboBox(self.scrollAreaWidgetContents)
        self.version.setObjectName(u"version")

        self.verticalLayout_7.addWidget(self.version)


        self.gridLayout.addLayout(self.verticalLayout_7, 0, 0, 1, 2)

        self.model_layout = QVBoxLayout()
        self.model_layout.setSpacing(10)
        self.model_layout.setObjectName(u"model_layout")
        self.label_3 = QLabel(self.scrollAreaWidgetContents)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setFont(font)

        self.model_layout.addWidget(self.label_3)

        self.model = QComboBox(self.scrollAreaWidgetContents)
        self.model.setObjectName(u"model")
        sizePolicy.setHeightForWidth(self.model.sizePolicy().hasHeightForWidth())
        self.model.setSizePolicy(sizePolicy)

        self.model_layout.addWidget(self.model)


        self.gridLayout.addLayout(self.model_layout, 2, 0, 1, 2)

        self.use_compel = QCheckBox(self.scrollAreaWidgetContents)
        self.use_compel.setObjectName(u"use_compel")
        sizePolicy.setHeightForWidth(self.use_compel.sizePolicy().hasHeightForWidth())
        self.use_compel.setSizePolicy(sizePolicy)

        self.gridLayout.addWidget(self.use_compel, 8, 0, 1, 2)

        self.seed_widget = SeedWidget(self.scrollAreaWidgetContents)
        self.seed_widget.setObjectName(u"seed_widget")
        sizePolicy.setHeightForWidth(self.seed_widget.sizePolicy().hasHeightForWidth())
        self.seed_widget.setSizePolicy(sizePolicy)
        self.seed_widget.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.seed_widget, 4, 0, 1, 2)

        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.label_5 = QLabel(self.scrollAreaWidgetContents)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setFont(font)

        self.verticalLayout_4.addWidget(self.label_5)

        self.pipeline = QComboBox(self.scrollAreaWidgetContents)
        self.pipeline.setObjectName(u"pipeline")
        sizePolicy.setHeightForWidth(self.pipeline.sizePolicy().hasHeightForWidth())
        self.pipeline.setSizePolicy(sizePolicy)

        self.verticalLayout_4.addWidget(self.pipeline)


        self.gridLayout.addLayout(self.verticalLayout_4, 1, 0, 1, 2)

        self.verticalSpacer = QSpacerItem(20, 394, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 9, 1, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_2.addWidget(self.scrollArea, 2, 0, 1, 1)

        self.label = QLabel(stable_diffusion_settings_widget)
        self.label.setObjectName(u"label")
        font1 = QFont()
        font1.setBold(True)
        self.label.setFont(font1)

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)

        self.line = QFrame(stable_diffusion_settings_widget)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_2.addWidget(self.line, 1, 0, 1, 1)


        self.retranslateUi(stable_diffusion_settings_widget)
        self.version.currentTextChanged.connect(stable_diffusion_settings_widget.handle_version_changed)
        self.pipeline.currentTextChanged.connect(stable_diffusion_settings_widget.handle_pipeline_changed)
        self.use_compel.toggled.connect(stable_diffusion_settings_widget.toggled_use_compel)
        self.scheduler.currentTextChanged.connect(stable_diffusion_settings_widget.handle_scheduler_changed)
        self.model.currentTextChanged.connect(stable_diffusion_settings_widget.handle_model_changed)

        QMetaObject.connectSlotsByName(stable_diffusion_settings_widget)
    # setupUi

    def retranslateUi(self, stable_diffusion_settings_widget):
        stable_diffusion_settings_widget.setWindowTitle(QCoreApplication.translate("stable_diffusion_settings_widget", u"Form", None))
        self.scale_widget.setProperty("label_text", QCoreApplication.translate("stable_diffusion_settings_widget", u"Guidance Scale", None))
        self.steps_widget.setProperty("label_text", QCoreApplication.translate("stable_diffusion_settings_widget", u"Steps", None))
        self.label_4.setText(QCoreApplication.translate("stable_diffusion_settings_widget", u"Scheduler", None))
        self.frames_slider_widget.setProperty("label_text", QCoreApplication.translate("stable_diffusion_settings_widget", u"Frames", None))
        self.ddim_eta_slider_widget.setProperty("label_text", QCoreApplication.translate("stable_diffusion_settings_widget", u"DDIM ETA", None))
        self.clip_skip_slider_widget.setProperty("label_text", QCoreApplication.translate("stable_diffusion_settings_widget", u"Clip Skip", None))
        self.label_6.setText(QCoreApplication.translate("stable_diffusion_settings_widget", u"Version", None))
        self.label_3.setText(QCoreApplication.translate("stable_diffusion_settings_widget", u"Model", None))
        self.use_compel.setText(QCoreApplication.translate("stable_diffusion_settings_widget", u"Use Compel", None))
        self.seed_widget.setProperty("generator_section", "")
        self.seed_widget.setProperty("generator_name", "")
        self.seed_widget.setProperty("property_name", QCoreApplication.translate("stable_diffusion_settings_widget", u"generator_settings.random_seed", None))
        self.label_5.setText(QCoreApplication.translate("stable_diffusion_settings_widget", u"Pipeline", None))
        self.label.setText(QCoreApplication.translate("stable_diffusion_settings_widget", u"Stable Diffusion", None))
    # retranslateUi

