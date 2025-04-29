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
    QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)

from airunner.gui.widgets.seed.seed_widget import SeedWidget
from airunner.gui.widgets.slider.slider_widget import SliderWidget

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
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 409, 921))
        self.gridLayout = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(0)
        self.gridLayout.setVerticalSpacing(10)
        self.gridLayout.setContentsMargins(0, 0, 10, 0)
        self.verticalSpacer = QSpacerItem(20, 394, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 10, 1, 1, 1)

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


        self.gridLayout.addLayout(self.verticalLayout_3, 7, 0, 1, 2)

        self.use_compel = QCheckBox(self.scrollAreaWidgetContents)
        self.use_compel.setObjectName(u"use_compel")
        sizePolicy.setHeightForWidth(self.use_compel.sizePolicy().hasHeightForWidth())
        self.use_compel.setSizePolicy(sizePolicy)

        self.gridLayout.addWidget(self.use_compel, 9, 0, 1, 2)

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

        self.gridLayout.addWidget(self.clip_skip_slider_widget, 8, 0, 1, 2)

        self.groupBox_2 = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_2.setObjectName(u"groupBox_2")
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self.groupBox_2.setFont(font)
        self.gridLayout_4 = QGridLayout(self.groupBox_2)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.model = QComboBox(self.groupBox_2)
        self.model.setObjectName(u"model")
        sizePolicy.setHeightForWidth(self.model.sizePolicy().hasHeightForWidth())
        self.model.setSizePolicy(sizePolicy)

        self.gridLayout_4.addWidget(self.model, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_2, 2, 0, 1, 2)

        self.groupBox_3 = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.groupBox_3.setFont(font)
        self.horizontalLayout = QHBoxLayout(self.groupBox_3)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.pipeline = QComboBox(self.groupBox_3)
        self.pipeline.setObjectName(u"pipeline")
        sizePolicy.setHeightForWidth(self.pipeline.sizePolicy().hasHeightForWidth())
        self.pipeline.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.pipeline)


        self.gridLayout.addWidget(self.groupBox_3, 1, 0, 1, 2)

        self.groupBox_4 = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_4.setObjectName(u"groupBox_4")
        self.groupBox_4.setFont(font)
        self.gridLayout_5 = QGridLayout(self.groupBox_4)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.version = QComboBox(self.groupBox_4)
        self.version.setObjectName(u"version")

        self.gridLayout_5.addWidget(self.version, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_4, 0, 0, 1, 2)

        self.seed_widget = SeedWidget(self.scrollAreaWidgetContents)
        self.seed_widget.setObjectName(u"seed_widget")
        sizePolicy.setHeightForWidth(self.seed_widget.sizePolicy().hasHeightForWidth())
        self.seed_widget.setSizePolicy(sizePolicy)
        self.seed_widget.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.seed_widget, 5, 0, 1, 2)

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


        self.gridLayout.addLayout(self.verticalLayout, 6, 0, 1, 2)

        self.groupBox = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox.setObjectName(u"groupBox")
        self.groupBox.setFont(font)
        self.gridLayout_7 = QGridLayout(self.groupBox)
        self.gridLayout_7.setObjectName(u"gridLayout_7")
        self.custom_model = QLineEdit(self.groupBox)
        self.custom_model.setObjectName(u"custom_model")

        self.gridLayout_7.addWidget(self.custom_model, 0, 0, 1, 1)

        self.browse_button = QPushButton(self.groupBox)
        self.browse_button.setObjectName(u"browse_button")
        self.browse_button.setMaximumSize(QSize(80, 16777215))

        self.gridLayout_7.addWidget(self.browse_button, 0, 1, 1, 1)


        self.gridLayout.addWidget(self.groupBox, 3, 0, 1, 2)

        self.groupBox_5 = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_5.setObjectName(u"groupBox_5")
        self.groupBox_5.setFont(font)
        self.gridLayout_3 = QGridLayout(self.groupBox_5)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.scheduler = QComboBox(self.groupBox_5)
        self.scheduler.setObjectName(u"scheduler")
        sizePolicy.setHeightForWidth(self.scheduler.sizePolicy().hasHeightForWidth())
        self.scheduler.setSizePolicy(sizePolicy)
        self.scheduler.setCursor(QCursor(Qt.ArrowCursor))

        self.gridLayout_3.addWidget(self.scheduler, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_5, 4, 0, 1, 2)

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
        self.custom_model.textEdited.connect(stable_diffusion_settings_widget.on_custom_model_textChanged)

        QMetaObject.connectSlotsByName(stable_diffusion_settings_widget)
    # setupUi

    def retranslateUi(self, stable_diffusion_settings_widget):
        stable_diffusion_settings_widget.setWindowTitle(QCoreApplication.translate("stable_diffusion_settings_widget", u"Form", None))
        self.scale_widget.setProperty("label_text", QCoreApplication.translate("stable_diffusion_settings_widget", u"Guidance Scale", None))
        self.steps_widget.setProperty("label_text", QCoreApplication.translate("stable_diffusion_settings_widget", u"Steps", None))
        self.use_compel.setText(QCoreApplication.translate("stable_diffusion_settings_widget", u"Use Compel", None))
        self.clip_skip_slider_widget.setProperty("label_text", QCoreApplication.translate("stable_diffusion_settings_widget", u"Clip Skip", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("stable_diffusion_settings_widget", u"Model", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("stable_diffusion_settings_widget", u"Pipeline", None))
        self.groupBox_4.setTitle(QCoreApplication.translate("stable_diffusion_settings_widget", u"Version", None))
        self.seed_widget.setProperty("generator_section", "")
        self.seed_widget.setProperty("generator_name", "")
        self.seed_widget.setProperty("property_name", QCoreApplication.translate("stable_diffusion_settings_widget", u"generator_settings.random_seed", None))
        self.frames_slider_widget.setProperty("label_text", QCoreApplication.translate("stable_diffusion_settings_widget", u"Frames", None))
        self.ddim_eta_slider_widget.setProperty("label_text", QCoreApplication.translate("stable_diffusion_settings_widget", u"DDIM ETA", None))
        self.groupBox.setTitle(QCoreApplication.translate("stable_diffusion_settings_widget", u"Custom path", None))
        self.browse_button.setText(QCoreApplication.translate("stable_diffusion_settings_widget", u"Browse", None))
        self.groupBox_5.setTitle(QCoreApplication.translate("stable_diffusion_settings_widget", u"Scheduler", None))
        self.label.setText(QCoreApplication.translate("stable_diffusion_settings_widget", u"Stable Diffusion", None))
    # retranslateUi

