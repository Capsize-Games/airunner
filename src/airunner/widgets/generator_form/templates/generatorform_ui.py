# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'generatorform.ui'
##
## Created by: Qt User Interface Compiler version 6.4.2
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
    QGridLayout, QHBoxLayout, QLabel, QPlainTextEdit,
    QProgressBar, QPushButton, QScrollArea, QSizePolicy,
    QSplitter, QVBoxLayout, QWidget)

from airunner.widgets.controlnet_settings.controlnet_settings_widget import ControlNetSettingsWidget
from airunner.widgets.input_image.input_image_settings_widget import InputImageSettingsWidget
from airunner.widgets.seed.seed_widget import (LatentsSeedWidget, SeedWidget)
from airunner.widgets.slider.slider_widget import SliderWidget
import resources_rc

class Ui_generator_form(object):
    def setupUi(self, generator_form):
        if not generator_form.objectName():
            generator_form.setObjectName(u"generator_form")
        generator_form.resize(663, 1139)
        font = QFont()
        font.setPointSize(8)
        generator_form.setFont(font)
        self.gridLayout_3 = QGridLayout(generator_form)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.scrollArea = QScrollArea(generator_form)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setFrameShape(QFrame.NoFrame)
        self.scrollArea.setFrameShadow(QFrame.Plain)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 663, 1139))
        self.gridLayout_2 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.splitter = QSplitter(self.scrollAreaWidgetContents)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Vertical)
        self.splitter.setChildrenCollapsible(False)
        self.layoutWidget = QWidget(self.splitter)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.verticalLayout_4 = QVBoxLayout(self.layoutWidget)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.label = QLabel(self.layoutWidget)
        self.label.setObjectName(u"label")
        font1 = QFont()
        font1.setPointSize(8)
        font1.setBold(True)
        self.label.setFont(font1)

        self.horizontalLayout_6.addWidget(self.label)

        self.use_prompt_builder_checkbox = QCheckBox(self.layoutWidget)
        self.use_prompt_builder_checkbox.setObjectName(u"use_prompt_builder_checkbox")
        self.use_prompt_builder_checkbox.setMaximumSize(QSize(120, 16777215))
        self.use_prompt_builder_checkbox.setLayoutDirection(Qt.LeftToRight)

        self.horizontalLayout_6.addWidget(self.use_prompt_builder_checkbox)

        self.prompt_builder_settings_button = QPushButton(self.layoutWidget)
        self.prompt_builder_settings_button.setObjectName(u"prompt_builder_settings_button")
        self.prompt_builder_settings_button.setMinimumSize(QSize(24, 24))
        self.prompt_builder_settings_button.setMaximumSize(QSize(24, 24))
        self.prompt_builder_settings_button.setBaseSize(QSize(0, 0))
        icon = QIcon()
        iconThemeName = u"preferences-desktop"
        if QIcon.hasThemeIcon(iconThemeName):
            icon = QIcon.fromTheme(iconThemeName)
        else:
            icon.addFile(u".", QSize(), QIcon.Normal, QIcon.Off)

        self.prompt_builder_settings_button.setIcon(icon)
        self.prompt_builder_settings_button.setFlat(True)

        self.horizontalLayout_6.addWidget(self.prompt_builder_settings_button)


        self.verticalLayout_4.addLayout(self.horizontalLayout_6)

        self.prompt = QPlainTextEdit(self.layoutWidget)
        self.prompt.setObjectName(u"prompt")

        self.verticalLayout_4.addWidget(self.prompt)

        self.splitter.addWidget(self.layoutWidget)
        self.layoutWidget1 = QWidget(self.splitter)
        self.layoutWidget1.setObjectName(u"layoutWidget1")
        self.verticalLayout_6 = QVBoxLayout(self.layoutWidget1)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.label_2 = QLabel(self.layoutWidget1)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setFont(font1)

        self.verticalLayout_6.addWidget(self.label_2)

        self.negative_prompt = QPlainTextEdit(self.layoutWidget1)
        self.negative_prompt.setObjectName(u"negative_prompt")

        self.verticalLayout_6.addWidget(self.negative_prompt)

        self.splitter.addWidget(self.layoutWidget1)
        self.layoutWidget2 = QWidget(self.splitter)
        self.layoutWidget2.setObjectName(u"layoutWidget2")
        self.gridLayout = QGridLayout(self.layoutWidget2)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.seed_widget = SeedWidget(self.layoutWidget2)
        self.seed_widget.setObjectName(u"seed_widget")

        self.horizontalLayout.addWidget(self.seed_widget)

        self.seed_widget_latents = LatentsSeedWidget(self.layoutWidget2)
        self.seed_widget_latents.setObjectName(u"seed_widget_latents")

        self.horizontalLayout.addWidget(self.seed_widget_latents)


        self.gridLayout.addLayout(self.horizontalLayout, 2, 0, 1, 1)

        self.verticalLayout_5 = QVBoxLayout()
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.variation_checkbox = QCheckBox(self.layoutWidget2)
        self.variation_checkbox.setObjectName(u"variation_checkbox")

        self.verticalLayout_5.addWidget(self.variation_checkbox)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.generate_button = QPushButton(self.layoutWidget2)
        self.generate_button.setObjectName(u"generate_button")

        self.horizontalLayout_3.addWidget(self.generate_button)

        self.progress_bar = QProgressBar(self.layoutWidget2)
        self.progress_bar.setObjectName(u"progress_bar")
        self.progress_bar.setValue(0)

        self.horizontalLayout_3.addWidget(self.progress_bar)

        self.interrupt_button = QPushButton(self.layoutWidget2)
        self.interrupt_button.setObjectName(u"interrupt_button")

        self.horizontalLayout_3.addWidget(self.interrupt_button)


        self.verticalLayout_5.addLayout(self.horizontalLayout_3)


        self.gridLayout.addLayout(self.verticalLayout_5, 6, 0, 1, 1)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.samples_widget = SliderWidget(self.layoutWidget2)
        self.samples_widget.setObjectName(u"samples_widget")
        self.samples_widget.setProperty("slider_callback", u"handle_value_change")
        self.samples_widget.setProperty("current_value", 0)
        self.samples_widget.setProperty("slider_maximum", 500)
        self.samples_widget.setProperty("spinbox_maximum", 500.000000000000000)
        self.samples_widget.setProperty("display_as_float", False)
        self.samples_widget.setProperty("spinbox_single_step", 1)
        self.samples_widget.setProperty("spinbox_page_step", 1)
        self.samples_widget.setProperty("spinbox_minimum", 1)
        self.samples_widget.setProperty("slider_minimum", 1)

        self.horizontalLayout_4.addWidget(self.samples_widget)

        self.clip_skip_slider_widget = SliderWidget(self.layoutWidget2)
        self.clip_skip_slider_widget.setObjectName(u"clip_skip_slider_widget")
        self.clip_skip_slider_widget.setProperty("current_value", 0)
        self.clip_skip_slider_widget.setProperty("slider_maximum", 11)
        self.clip_skip_slider_widget.setProperty("spinbox_maximum", 12.000000000000000)
        self.clip_skip_slider_widget.setProperty("display_as_float", False)
        self.clip_skip_slider_widget.setProperty("spinbox_single_step", 1)
        self.clip_skip_slider_widget.setProperty("spinbox_page_step", 1)
        self.clip_skip_slider_widget.setProperty("spinbox_minimum", 0)
        self.clip_skip_slider_widget.setProperty("slider_minimum", 0)
        self.clip_skip_slider_widget.setProperty("slider_callback", u"handle_value_change")
        self.clip_skip_slider_widget.setProperty("settings_property", u"generator.clip_skip")

        self.horizontalLayout_4.addWidget(self.clip_skip_slider_widget)


        self.gridLayout.addLayout(self.horizontalLayout_4, 4, 0, 1, 1)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label_3 = QLabel(self.layoutWidget2)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setFont(font1)

        self.verticalLayout.addWidget(self.label_3)

        self.model = QComboBox(self.layoutWidget2)
        self.model.setObjectName(u"model")

        self.verticalLayout.addWidget(self.model)


        self.horizontalLayout_5.addLayout(self.verticalLayout)

        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.label_4 = QLabel(self.layoutWidget2)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setFont(font1)

        self.verticalLayout_2.addWidget(self.label_4)

        self.scheduler = QComboBox(self.layoutWidget2)
        self.scheduler.setObjectName(u"scheduler")

        self.verticalLayout_2.addWidget(self.scheduler)


        self.horizontalLayout_5.addLayout(self.verticalLayout_2)


        self.gridLayout.addLayout(self.horizontalLayout_5, 1, 0, 1, 1)

        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.input_image_widget = InputImageSettingsWidget(self.layoutWidget2)
        self.input_image_widget.setObjectName(u"input_image_widget")
        self.input_image_widget.setMinimumSize(QSize(0, 0))
        self.input_image_widget.setAcceptDrops(False)

        self.verticalLayout_3.addWidget(self.input_image_widget)

        self.controlnet_settings = ControlNetSettingsWidget(self.layoutWidget2)
        self.controlnet_settings.setObjectName(u"controlnet_settings")
        self.controlnet_settings.setMinimumSize(QSize(0, 0))
        self.controlnet_settings.setAcceptDrops(False)

        self.verticalLayout_3.addWidget(self.controlnet_settings)


        self.gridLayout.addLayout(self.verticalLayout_3, 0, 0, 1, 1)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.steps_widget = SliderWidget(self.layoutWidget2)
        self.steps_widget.setObjectName(u"steps_widget")
        self.steps_widget.setProperty("slider_callback", u"handle_value_change")
        self.steps_widget.setProperty("current_value", 0)
        self.steps_widget.setProperty("slider_maximum", 200)
        self.steps_widget.setProperty("spinbox_maximum", 200.000000000000000)
        self.steps_widget.setProperty("display_as_float", False)
        self.steps_widget.setProperty("spinbox_single_step", 1)
        self.steps_widget.setProperty("spinbox_page_step", 1)
        self.steps_widget.setProperty("spinbox_minimum", 1)
        self.steps_widget.setProperty("slider_minimum", 1)
        self.steps_widget.setProperty("settings_property", u"generator.steps")

        self.horizontalLayout_2.addWidget(self.steps_widget)

        self.scale_widget = SliderWidget(self.layoutWidget2)
        self.scale_widget.setObjectName(u"scale_widget")
        self.scale_widget.setProperty("current_value", 0)
        self.scale_widget.setProperty("slider_maximum", 10000)
        self.scale_widget.setProperty("spinbox_maximum", 100.000000000000000)
        self.scale_widget.setProperty("display_as_float", True)
        self.scale_widget.setProperty("spinbox_single_step", 0.010000000000000)
        self.scale_widget.setProperty("spinbox_page_step", 0.010000000000000)
        self.scale_widget.setProperty("slider_callback", u"handle_value_change")
        self.scale_widget.setProperty("settings_property", u"generator.scale")

        self.horizontalLayout_2.addWidget(self.scale_widget)


        self.gridLayout.addLayout(self.horizontalLayout_2, 3, 0, 1, 1)

        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.ddim_eta_slider_widget = SliderWidget(self.layoutWidget2)
        self.ddim_eta_slider_widget.setObjectName(u"ddim_eta_slider_widget")
        self.ddim_eta_slider_widget.setProperty("slider_callback", u"handle_value_change")
        self.ddim_eta_slider_widget.setProperty("current_value", 1)
        self.ddim_eta_slider_widget.setProperty("slider_maximum", 10)
        self.ddim_eta_slider_widget.setProperty("spinbox_maximum", 10)
        self.ddim_eta_slider_widget.setProperty("display_as_float", False)
        self.ddim_eta_slider_widget.setProperty("spinbox_single_step", 1)
        self.ddim_eta_slider_widget.setProperty("spinbox_page_step", 1)
        self.ddim_eta_slider_widget.setProperty("spinbox_minimum", 1)
        self.ddim_eta_slider_widget.setProperty("slider_minimum", 1)
        self.ddim_eta_slider_widget.setProperty("settings_property", u"generator.ddim_eta")

        self.horizontalLayout_7.addWidget(self.ddim_eta_slider_widget)

        self.frames_slider_widget = SliderWidget(self.layoutWidget2)
        self.frames_slider_widget.setObjectName(u"frames_slider_widget")
        self.frames_slider_widget.setProperty("slider_callback", u"handle_value_change")
        self.frames_slider_widget.setProperty("current_value", 0)
        self.frames_slider_widget.setProperty("slider_maximum", 200)
        self.frames_slider_widget.setProperty("spinbox_maximum", 200.000000000000000)
        self.frames_slider_widget.setProperty("display_as_float", False)
        self.frames_slider_widget.setProperty("spinbox_single_step", 1)
        self.frames_slider_widget.setProperty("spinbox_page_step", 1)
        self.frames_slider_widget.setProperty("spinbox_minimum", 1)
        self.frames_slider_widget.setProperty("slider_minimum", 1)
        self.frames_slider_widget.setProperty("settings_property", u"generator.n_samples")

        self.horizontalLayout_7.addWidget(self.frames_slider_widget)


        self.gridLayout.addLayout(self.horizontalLayout_7, 5, 0, 1, 1)

        self.splitter.addWidget(self.layoutWidget2)

        self.gridLayout_2.addWidget(self.splitter, 0, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_3.addWidget(self.scrollArea, 0, 0, 1, 1)


        self.retranslateUi(generator_form)
        self.prompt.textChanged.connect(generator_form.handle_prompt_changed)
        self.negative_prompt.textChanged.connect(generator_form.handle_negative_prompt_changed)
        self.use_prompt_builder_checkbox.toggled.connect(generator_form.toggle_prompt_builder_checkbox)
        self.model.currentTextChanged.connect(generator_form.handle_model_changed)
        self.scheduler.currentTextChanged.connect(generator_form.handle_scheduler_changed)
        self.variation_checkbox.toggled.connect(generator_form.toggle_variation)
        self.generate_button.clicked.connect(generator_form.handle_generate_button_clicked)
        self.interrupt_button.clicked.connect(generator_form.handle_interrupt_button_clicked)

        QMetaObject.connectSlotsByName(generator_form)
    # setupUi

    def retranslateUi(self, generator_form):
        generator_form.setWindowTitle(QCoreApplication.translate("generator_form", u"Form", None))
        self.label.setText(QCoreApplication.translate("generator_form", u"Prompt", None))
        self.use_prompt_builder_checkbox.setText(QCoreApplication.translate("generator_form", u"Use Prompt Builder", None))
        self.prompt_builder_settings_button.setText("")
        self.label_2.setText(QCoreApplication.translate("generator_form", u"Negative Prompt", None))
        self.seed_widget.setProperty("generator_section", "")
        self.seed_widget.setProperty("generator_name", "")
        self.seed_widget_latents.setProperty("generator_section", "")
        self.seed_widget_latents.setProperty("generator_name", "")
        self.variation_checkbox.setText(QCoreApplication.translate("generator_form", u"Variation", None))
        self.generate_button.setText(QCoreApplication.translate("generator_form", u"Generate", None))
        self.interrupt_button.setText(QCoreApplication.translate("generator_form", u"Interrupt", None))
        self.samples_widget.setProperty("label_text", QCoreApplication.translate("generator_form", u"Samples", None))
        self.samples_widget.setProperty("settings_property", QCoreApplication.translate("generator_form", u"generator.n_samples", None))
        self.clip_skip_slider_widget.setProperty("label_text", QCoreApplication.translate("generator_form", u"Clip Skip", None))
        self.label_3.setText(QCoreApplication.translate("generator_form", u"Model", None))
        self.label_4.setText(QCoreApplication.translate("generator_form", u"Scheduler", None))
        self.input_image_widget.setProperty("generator_section", "")
        self.input_image_widget.setProperty("generator_name", "")
        self.input_image_widget.setProperty("checkbox_label", QCoreApplication.translate("generator_form", u"Use Input Image", None))
        self.controlnet_settings.setProperty("generator_section", "")
        self.controlnet_settings.setProperty("generator_name", "")
        self.controlnet_settings.setProperty("checkbox_label", QCoreApplication.translate("generator_form", u"Controlnet", None))
        self.steps_widget.setProperty("label_text", QCoreApplication.translate("generator_form", u"Steps", None))
        self.scale_widget.setProperty("label_text", QCoreApplication.translate("generator_form", u"Scale", None))
        self.ddim_eta_slider_widget.setProperty("label_text", QCoreApplication.translate("generator_form", u"DDIM ETA", None))
        self.frames_slider_widget.setProperty("label_text", QCoreApplication.translate("generator_form", u"Frames", None))
    # retranslateUi

