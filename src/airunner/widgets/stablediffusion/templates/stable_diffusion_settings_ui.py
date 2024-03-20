# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'stable_diffusion_settings.ui'
##
## Created by: Qt User Interface Compiler version 6.6.2
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy, QSpacerItem,
    QVBoxLayout, QWidget)

from airunner.widgets.seed.seed_widget import SeedWidget
from airunner.widgets.slider.slider_widget import SliderWidget
import airunner.resources_light_rc

class Ui_stable_diffusion_settings_widget(object):
    def setupUi(self, stable_diffusion_settings_widget):
        if not stable_diffusion_settings_widget.objectName():
            stable_diffusion_settings_widget.setObjectName(u"stable_diffusion_settings_widget")
        stable_diffusion_settings_widget.resize(690, 969)
        stable_diffusion_settings_widget.setMaximumSize(QSize(16777215, 16777215))
        self.gridLayout = QGridLayout(stable_diffusion_settings_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.label_4 = QLabel(stable_diffusion_settings_widget)
        self.label_4.setObjectName(u"label_4")
        font = QFont()
        font.setPointSize(8)
        font.setBold(True)
        self.label_4.setFont(font)

        self.verticalLayout_2.addWidget(self.label_4)

        self.scheduler = QComboBox(stable_diffusion_settings_widget)
        self.scheduler.setObjectName(u"scheduler")
        self.scheduler.setCursor(QCursor(Qt.ArrowCursor))

        self.verticalLayout_2.addWidget(self.scheduler)


        self.gridLayout.addLayout(self.verticalLayout_2, 6, 0, 1, 5)

        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.label_5 = QLabel(stable_diffusion_settings_widget)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setFont(font)

        self.verticalLayout_4.addWidget(self.label_5)

        self.pipeline = QComboBox(stable_diffusion_settings_widget)
        self.pipeline.setObjectName(u"pipeline")

        self.verticalLayout_4.addWidget(self.pipeline)


        self.gridLayout.addLayout(self.verticalLayout_4, 3, 0, 1, 5)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label_3 = QLabel(stable_diffusion_settings_widget)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setFont(font)

        self.verticalLayout.addWidget(self.label_3)

        self.model = QComboBox(stable_diffusion_settings_widget)
        self.model.setObjectName(u"model")

        self.verticalLayout.addWidget(self.model)


        self.gridLayout.addLayout(self.verticalLayout, 5, 0, 1, 5)

        self.ddim_frames = QHBoxLayout()
        self.ddim_frames.setObjectName(u"ddim_frames")
        self.ddim_eta_slider_widget = SliderWidget(stable_diffusion_settings_widget)
        self.ddim_eta_slider_widget.setObjectName(u"ddim_eta_slider_widget")
        self.ddim_eta_slider_widget.setMinimumSize(QSize(0, 10))
        self.ddim_eta_slider_widget.setProperty("slider_callback", u"handle_value_change")
        self.ddim_eta_slider_widget.setProperty("current_value", 1)
        self.ddim_eta_slider_widget.setProperty("slider_maximum", 10)
        self.ddim_eta_slider_widget.setProperty("spinbox_maximum", 10)
        self.ddim_eta_slider_widget.setProperty("display_as_float", False)
        self.ddim_eta_slider_widget.setProperty("spinbox_single_step", 1)
        self.ddim_eta_slider_widget.setProperty("spinbox_page_step", 1)
        self.ddim_eta_slider_widget.setProperty("spinbox_minimum", 1)
        self.ddim_eta_slider_widget.setProperty("slider_minimum", 1)
        self.ddim_eta_slider_widget.setProperty("settings_property", u"generator_settings.ddim_eta")

        self.ddim_frames.addWidget(self.ddim_eta_slider_widget)

        self.frames_slider_widget = SliderWidget(stable_diffusion_settings_widget)
        self.frames_slider_widget.setObjectName(u"frames_slider_widget")
        self.frames_slider_widget.setMinimumSize(QSize(0, 10))
        self.frames_slider_widget.setProperty("slider_callback", u"handle_value_change")
        self.frames_slider_widget.setProperty("current_value", 0)
        self.frames_slider_widget.setProperty("slider_maximum", 200)
        self.frames_slider_widget.setProperty("spinbox_maximum", 200.000000000000000)
        self.frames_slider_widget.setProperty("display_as_float", False)
        self.frames_slider_widget.setProperty("spinbox_single_step", 1)
        self.frames_slider_widget.setProperty("spinbox_page_step", 1)
        self.frames_slider_widget.setProperty("spinbox_minimum", 1)
        self.frames_slider_widget.setProperty("slider_minimum", 1)
        self.frames_slider_widget.setProperty("settings_property", u"generator_settings.n_samples")

        self.ddim_frames.addWidget(self.frames_slider_widget)


        self.gridLayout.addLayout(self.ddim_frames, 10, 0, 1, 5)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.seed_widget = SeedWidget(stable_diffusion_settings_widget)
        self.seed_widget.setObjectName(u"seed_widget")
        self.seed_widget.setMinimumSize(QSize(0, 10))

        self.horizontalLayout_3.addWidget(self.seed_widget)


        self.gridLayout.addLayout(self.horizontalLayout_3, 7, 0, 1, 5)

        self.reload_selected_preset = QPushButton(stable_diffusion_settings_widget)
        self.reload_selected_preset.setObjectName(u"reload_selected_preset")
        self.reload_selected_preset.setMaximumSize(QSize(32, 16777215))
        icon = QIcon()
        icon.addFile(u":/icons/light/exchange-refresh-icon.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.reload_selected_preset.setIcon(icon)

        self.gridLayout.addWidget(self.reload_selected_preset, 1, 4, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 13, 0, 1, 1)

        self.verticalLayout_7 = QVBoxLayout()
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.label_6 = QLabel(stable_diffusion_settings_widget)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setFont(font)

        self.verticalLayout_7.addWidget(self.label_6)

        self.version = QComboBox(stable_diffusion_settings_widget)
        self.version.setObjectName(u"version")

        self.verticalLayout_7.addWidget(self.version)


        self.gridLayout.addLayout(self.verticalLayout_7, 4, 0, 1, 5)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.steps_widget = SliderWidget(stable_diffusion_settings_widget)
        self.steps_widget.setObjectName(u"steps_widget")
        self.steps_widget.setMinimumSize(QSize(0, 10))
        self.steps_widget.setProperty("slider_callback", u"handle_value_change")
        self.steps_widget.setProperty("current_value", 0)
        self.steps_widget.setProperty("slider_maximum", 200)
        self.steps_widget.setProperty("spinbox_maximum", 200.000000000000000)
        self.steps_widget.setProperty("display_as_float", False)
        self.steps_widget.setProperty("spinbox_single_step", 1)
        self.steps_widget.setProperty("spinbox_page_step", 1)
        self.steps_widget.setProperty("spinbox_minimum", 1)
        self.steps_widget.setProperty("slider_minimum", 1)
        self.steps_widget.setProperty("settings_property", u"generator_settings.steps")

        self.horizontalLayout_5.addWidget(self.steps_widget)

        self.scale_widget = SliderWidget(stable_diffusion_settings_widget)
        self.scale_widget.setObjectName(u"scale_widget")
        self.scale_widget.setMinimumSize(QSize(0, 10))
        self.scale_widget.setProperty("current_value", 0)
        self.scale_widget.setProperty("slider_maximum", 10000)
        self.scale_widget.setProperty("spinbox_maximum", 100.000000000000000)
        self.scale_widget.setProperty("display_as_float", True)
        self.scale_widget.setProperty("spinbox_single_step", 0.010000000000000)
        self.scale_widget.setProperty("spinbox_page_step", 0.010000000000000)
        self.scale_widget.setProperty("slider_callback", u"handle_value_change")
        self.scale_widget.setProperty("settings_property", u"generator_settings.scale")

        self.horizontalLayout_5.addWidget(self.scale_widget)


        self.gridLayout.addLayout(self.horizontalLayout_5, 11, 0, 1, 5)

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.samples = SliderWidget(stable_diffusion_settings_widget)
        self.samples.setObjectName(u"samples")
        self.samples.setMinimumSize(QSize(0, 10))
        self.samples.setProperty("slider_callback", u"handle_value_change")
        self.samples.setProperty("current_value", 0)
        self.samples.setProperty("slider_maximum", 500)
        self.samples.setProperty("spinbox_maximum", 500.000000000000000)
        self.samples.setProperty("display_as_float", False)
        self.samples.setProperty("spinbox_single_step", 1)
        self.samples.setProperty("spinbox_page_step", 1)
        self.samples.setProperty("spinbox_minimum", 1)
        self.samples.setProperty("slider_minimum", 1)

        self.horizontalLayout_6.addWidget(self.samples)

        self.clip_skip_slider_widget = SliderWidget(stable_diffusion_settings_widget)
        self.clip_skip_slider_widget.setObjectName(u"clip_skip_slider_widget")
        self.clip_skip_slider_widget.setMinimumSize(QSize(0, 10))
        self.clip_skip_slider_widget.setProperty("current_value", 0)
        self.clip_skip_slider_widget.setProperty("slider_maximum", 11)
        self.clip_skip_slider_widget.setProperty("spinbox_maximum", 12.000000000000000)
        self.clip_skip_slider_widget.setProperty("display_as_float", False)
        self.clip_skip_slider_widget.setProperty("spinbox_single_step", 1)
        self.clip_skip_slider_widget.setProperty("spinbox_page_step", 1)
        self.clip_skip_slider_widget.setProperty("spinbox_minimum", 0)
        self.clip_skip_slider_widget.setProperty("slider_minimum", 0)
        self.clip_skip_slider_widget.setProperty("slider_callback", u"handle_value_change")
        self.clip_skip_slider_widget.setProperty("settings_property", u"generator_settings.clip_skip")

        self.horizontalLayout_6.addWidget(self.clip_skip_slider_widget)


        self.gridLayout.addLayout(self.horizontalLayout_6, 8, 0, 1, 5)

        self.presets = QComboBox(stable_diffusion_settings_widget)
        self.presets.setObjectName(u"presets")

        self.gridLayout.addWidget(self.presets, 1, 0, 1, 4)

        self.label = QLabel(stable_diffusion_settings_widget)
        self.label.setObjectName(u"label")

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)


        self.retranslateUi(stable_diffusion_settings_widget)
        self.pipeline.currentTextChanged.connect(stable_diffusion_settings_widget.handle_pipeline_changed)
        self.version.currentTextChanged.connect(stable_diffusion_settings_widget.handle_version_changed)
        self.model.currentTextChanged.connect(stable_diffusion_settings_widget.handle_model_changed)
        self.scheduler.currentTextChanged.connect(stable_diffusion_settings_widget.handle_scheduler_changed)
        self.reload_selected_preset.clicked.connect(stable_diffusion_settings_widget.reload_selected_preset)
        self.presets.currentTextChanged.connect(stable_diffusion_settings_widget.selected_preset_changed)

        QMetaObject.connectSlotsByName(stable_diffusion_settings_widget)
    # setupUi

    def retranslateUi(self, stable_diffusion_settings_widget):
        stable_diffusion_settings_widget.setWindowTitle(QCoreApplication.translate("stable_diffusion_settings_widget", u"Form", None))
        self.label_4.setText(QCoreApplication.translate("stable_diffusion_settings_widget", u"Scheduler", None))
        self.label_5.setText(QCoreApplication.translate("stable_diffusion_settings_widget", u"Pipeline", None))
        self.label_3.setText(QCoreApplication.translate("stable_diffusion_settings_widget", u"Model", None))
        self.ddim_eta_slider_widget.setProperty("label_text", QCoreApplication.translate("stable_diffusion_settings_widget", u"DDIM ETA", None))
        self.frames_slider_widget.setProperty("label_text", QCoreApplication.translate("stable_diffusion_settings_widget", u"Frames", None))
        self.seed_widget.setProperty("generator_section", "")
        self.seed_widget.setProperty("generator_name", "")
        self.seed_widget.setProperty("property_name", QCoreApplication.translate("stable_diffusion_settings_widget", u"generator_settings.random_seed", None))
        self.reload_selected_preset.setText("")
        self.label_6.setText(QCoreApplication.translate("stable_diffusion_settings_widget", u"Version", None))
        self.steps_widget.setProperty("label_text", QCoreApplication.translate("stable_diffusion_settings_widget", u"Steps", None))
        self.scale_widget.setProperty("label_text", QCoreApplication.translate("stable_diffusion_settings_widget", u"Scale", None))
        self.samples.setProperty("label_text", QCoreApplication.translate("stable_diffusion_settings_widget", u"Samples", None))
        self.samples.setProperty("settings_property", QCoreApplication.translate("stable_diffusion_settings_widget", u"n_samples", None))
        self.clip_skip_slider_widget.setProperty("label_text", QCoreApplication.translate("stable_diffusion_settings_widget", u"Clip Skip", None))
        self.label.setText(QCoreApplication.translate("stable_diffusion_settings_widget", u"Presets", None))
    # retranslateUi

