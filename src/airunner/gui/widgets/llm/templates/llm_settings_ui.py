# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'llm_settings.ui'
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
    QLayout, QLineEdit, QPushButton, QScrollArea,
    QSizePolicy, QSpacerItem, QVBoxLayout, QWidget)

from airunner.gui.widgets.slider.slider_widget import SliderWidget

class Ui_llm_settings_widget(object):
    def setupUi(self, llm_settings_widget):
        if not llm_settings_widget.objectName():
            llm_settings_widget.setObjectName(u"llm_settings_widget")
        llm_settings_widget.resize(581, 742)
        self.gridLayout_4 = QGridLayout(llm_settings_widget)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.gridLayout_4.setHorizontalSpacing(0)
        self.gridLayout_4.setVerticalSpacing(10)
        self.gridLayout_4.setContentsMargins(0, 0, 0, 0)
        self.scrollArea = QScrollArea(llm_settings_widget)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setFrameShadow(QFrame.Shadow.Plain)
        self.scrollArea.setLineWidth(0)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 579, 546))
        self.gridLayout = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(0)
        self.gridLayout.setVerticalSpacing(10)
        self.gridLayout.setContentsMargins(0, 0, 10, 0)
        self.prompt_template_container = QWidget(self.scrollAreaWidgetContents)
        self.prompt_template_container.setObjectName(u"prompt_template_container")
        self.gridLayout_17 = QGridLayout(self.prompt_template_container)
        self.gridLayout_17.setObjectName(u"gridLayout_17")
        self.gridLayout_17.setHorizontalSpacing(0)
        self.gridLayout_17.setVerticalSpacing(10)
        self.gridLayout_17.setContentsMargins(0, 0, 0, 0)

        self.gridLayout.addWidget(self.prompt_template_container, 0, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 263, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 2, 0, 1, 1)

        self.override_parameters = QGroupBox(self.scrollAreaWidgetContents)
        self.override_parameters.setObjectName(u"override_parameters")
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        self.override_parameters.setFont(font)
        self.override_parameters.setCheckable(True)
        self.override_parameters.setChecked(True)
        self.gridLayout_12 = QGridLayout(self.override_parameters)
        self.gridLayout_12.setObjectName(u"gridLayout_12")
        self.gridLayout_12.setHorizontalSpacing(0)
        self.gridLayout_12.setVerticalSpacing(10)
        self.gridLayout_12.setContentsMargins(0, 0, 0, 0)
        self.widget_19 = QWidget(self.override_parameters)
        self.widget_19.setObjectName(u"widget_19")
        self.gridLayout_2 = QGridLayout(self.widget_19)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setHorizontalSpacing(0)
        self.gridLayout_2.setVerticalSpacing(10)
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.seed = QLineEdit(self.widget_19)
        self.seed.setObjectName(u"seed")
        self.seed.setMinimumSize(QSize(0, 20))

        self.gridLayout_2.addWidget(self.seed, 0, 0, 1, 1)

        self.random_seed = QCheckBox(self.widget_19)
        self.random_seed.setObjectName(u"random_seed")
        self.random_seed.setMinimumSize(QSize(0, 20))

        self.gridLayout_2.addWidget(self.random_seed, 0, 1, 1, 1)


        self.gridLayout_12.addWidget(self.widget_19, 6, 0, 1, 1)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setSpacing(10)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.length_penalty = SliderWidget(self.override_parameters)
        self.length_penalty.setObjectName(u"length_penalty")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.length_penalty.sizePolicy().hasHeightForWidth())
        self.length_penalty.setSizePolicy(sizePolicy)
        self.length_penalty.setMinimumSize(QSize(0, 0))
        self.length_penalty.setProperty("slider_minimum", -100)
        self.length_penalty.setProperty("slider_maximum", 1000)
        self.length_penalty.setProperty("spinbox_minimum", 0.000000000000000)
        self.length_penalty.setProperty("spinbox_maximum", 1.000000000000000)
        self.length_penalty.setProperty("display_as_float", True)
        self.length_penalty.setProperty("slider_single_step", 1)
        self.length_penalty.setProperty("slider_page_step", 10)
        self.length_penalty.setProperty("spinbox_single_step", 0.010000000000000)
        self.length_penalty.setProperty("spinbox_page_step", 0.100000000000000)

        self.horizontalLayout_3.addWidget(self.length_penalty)

        self.num_beams = SliderWidget(self.override_parameters)
        self.num_beams.setObjectName(u"num_beams")
        sizePolicy.setHeightForWidth(self.num_beams.sizePolicy().hasHeightForWidth())
        self.num_beams.setSizePolicy(sizePolicy)
        self.num_beams.setMinimumSize(QSize(0, 0))
        self.num_beams.setProperty("slider_minimum", 1)
        self.num_beams.setProperty("slider_maximum", 100)
        self.num_beams.setProperty("spinbox_minimum", 0.000000000000000)
        self.num_beams.setProperty("spinbox_maximum", 100.000000000000000)
        self.num_beams.setProperty("display_as_float", False)
        self.num_beams.setProperty("slider_single_step", 1)
        self.num_beams.setProperty("slider_page_step", 10)
        self.num_beams.setProperty("spinbox_single_step", 0.010000000000000)
        self.num_beams.setProperty("spinbox_page_step", 0.100000000000000)

        self.horizontalLayout_3.addWidget(self.num_beams)


        self.gridLayout_12.addLayout(self.horizontalLayout_3, 3, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(10)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
        self.top_p = SliderWidget(self.override_parameters)
        self.top_p.setObjectName(u"top_p")
        sizePolicy.setHeightForWidth(self.top_p.sizePolicy().hasHeightForWidth())
        self.top_p.setSizePolicy(sizePolicy)
        self.top_p.setMinimumSize(QSize(0, 0))
        self.top_p.setProperty("slider_minimum", 1)
        self.top_p.setProperty("slider_maximum", 1000)
        self.top_p.setProperty("spinbox_minimum", 0.000000000000000)
        self.top_p.setProperty("spinbox_maximum", 1.000000000000000)
        self.top_p.setProperty("display_as_float", True)
        self.top_p.setProperty("slider_single_step", 1)
        self.top_p.setProperty("slider_page_step", 10)
        self.top_p.setProperty("spinbox_single_step", 0.010000000000000)
        self.top_p.setProperty("spinbox_page_step", 0.100000000000000)

        self.horizontalLayout.addWidget(self.top_p)

        self.max_new_tokens = SliderWidget(self.override_parameters)
        self.max_new_tokens.setObjectName(u"max_new_tokens")
        sizePolicy.setHeightForWidth(self.max_new_tokens.sizePolicy().hasHeightForWidth())
        self.max_new_tokens.setSizePolicy(sizePolicy)
        self.max_new_tokens.setMinimumSize(QSize(0, 0))
        self.max_new_tokens.setProperty("slider_minimum", 1)
        self.max_new_tokens.setProperty("slider_maximum", 2556)
        self.max_new_tokens.setProperty("spinbox_minimum", 1.000000000000000)
        self.max_new_tokens.setProperty("spinbox_maximum", 2556.000000000000000)
        self.max_new_tokens.setProperty("display_as_float", False)
        self.max_new_tokens.setProperty("slider_single_step", 1)
        self.max_new_tokens.setProperty("slider_page_step", 2556)
        self.max_new_tokens.setProperty("spinbox_single_step", 1)
        self.max_new_tokens.setProperty("spinbox_page_step", 2556)

        self.horizontalLayout.addWidget(self.max_new_tokens)


        self.gridLayout_12.addLayout(self.horizontalLayout, 0, 0, 1, 1)

        self.line = QFrame(self.override_parameters)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_12.addWidget(self.line, 9, 0, 1, 1)

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setSpacing(10)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.sequences = SliderWidget(self.override_parameters)
        self.sequences.setObjectName(u"sequences")
        sizePolicy.setHeightForWidth(self.sequences.sizePolicy().hasHeightForWidth())
        self.sequences.setSizePolicy(sizePolicy)
        self.sequences.setMinimumSize(QSize(0, 0))
        self.sequences.setProperty("slider_minimum", 1)
        self.sequences.setProperty("slider_maximum", 100)
        self.sequences.setProperty("spinbox_minimum", 0.000000000000000)
        self.sequences.setProperty("spinbox_maximum", 100.000000000000000)
        self.sequences.setProperty("display_as_float", False)
        self.sequences.setProperty("slider_single_step", 1)
        self.sequences.setProperty("slider_page_step", 10)
        self.sequences.setProperty("spinbox_single_step", 0.010000000000000)
        self.sequences.setProperty("spinbox_page_step", 0.100000000000000)

        self.horizontalLayout_6.addWidget(self.sequences)

        self.top_k = SliderWidget(self.override_parameters)
        self.top_k.setObjectName(u"top_k")
        sizePolicy.setHeightForWidth(self.top_k.sizePolicy().hasHeightForWidth())
        self.top_k.setSizePolicy(sizePolicy)
        self.top_k.setMinimumSize(QSize(0, 0))
        self.top_k.setProperty("slider_minimum", 0)
        self.top_k.setProperty("slider_maximum", 256)
        self.top_k.setProperty("spinbox_minimum", 0.000000000000000)
        self.top_k.setProperty("spinbox_maximum", 256.000000000000000)
        self.top_k.setProperty("display_as_float", False)
        self.top_k.setProperty("slider_single_step", 1)
        self.top_k.setProperty("slider_page_step", 10)
        self.top_k.setProperty("spinbox_single_step", 1)
        self.top_k.setProperty("spinbox_page_step", 10)

        self.horizontalLayout_6.addWidget(self.top_k)


        self.gridLayout_12.addLayout(self.horizontalLayout_6, 5, 0, 1, 1)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setSpacing(10)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.ngram_size = SliderWidget(self.override_parameters)
        self.ngram_size.setObjectName(u"ngram_size")
        sizePolicy.setHeightForWidth(self.ngram_size.sizePolicy().hasHeightForWidth())
        self.ngram_size.setSizePolicy(sizePolicy)
        self.ngram_size.setMinimumSize(QSize(0, 0))
        self.ngram_size.setProperty("slider_minimum", 0)
        self.ngram_size.setProperty("slider_maximum", 20)
        self.ngram_size.setProperty("spinbox_minimum", 0.000000000000000)
        self.ngram_size.setProperty("spinbox_maximum", 20.000000000000000)
        self.ngram_size.setProperty("display_as_float", False)
        self.ngram_size.setProperty("slider_single_step", 1)
        self.ngram_size.setProperty("slider_page_step", 1)
        self.ngram_size.setProperty("spinbox_single_step", 1.000000000000000)
        self.ngram_size.setProperty("spinbox_page_step", 1.000000000000000)

        self.horizontalLayout_5.addWidget(self.ngram_size)

        self.temperature = SliderWidget(self.override_parameters)
        self.temperature.setObjectName(u"temperature")
        sizePolicy.setHeightForWidth(self.temperature.sizePolicy().hasHeightForWidth())
        self.temperature.setSizePolicy(sizePolicy)
        self.temperature.setMinimumSize(QSize(0, 0))
        self.temperature.setProperty("slider_minimum", 1)
        self.temperature.setProperty("slider_maximum", 10000)
        self.temperature.setProperty("spinbox_minimum", 0.000100000000000)
        self.temperature.setProperty("spinbox_maximum", 1.000000000000000)
        self.temperature.setProperty("display_as_float", True)
        self.temperature.setProperty("slider_single_step", 1)
        self.temperature.setProperty("slider_page_step", 10)
        self.temperature.setProperty("spinbox_single_step", 0.010000000000000)
        self.temperature.setProperty("spinbox_page_step", 0.100000000000000)

        self.horizontalLayout_5.addWidget(self.temperature)


        self.gridLayout_12.addLayout(self.horizontalLayout_5, 4, 0, 1, 1)

        self.gridLayout_3 = QGridLayout()
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setHorizontalSpacing(0)
        self.gridLayout_3.setVerticalSpacing(10)
        self.early_stopping = QCheckBox(self.override_parameters)
        self.early_stopping.setObjectName(u"early_stopping")

        self.gridLayout_3.addWidget(self.early_stopping, 0, 0, 1, 1)

        self.use_cache = QCheckBox(self.override_parameters)
        self.use_cache.setObjectName(u"use_cache")

        self.gridLayout_3.addWidget(self.use_cache, 0, 2, 1, 1)

        self.do_sample = QCheckBox(self.override_parameters)
        self.do_sample.setObjectName(u"do_sample")

        self.gridLayout_3.addWidget(self.do_sample, 0, 1, 1, 1)


        self.gridLayout_12.addLayout(self.gridLayout_3, 8, 0, 1, 1)

        self.pushButton = QPushButton(self.override_parameters)
        self.pushButton.setObjectName(u"pushButton")
        font1 = QFont()
        font1.setPointSize(9)
        font1.setBold(False)
        self.pushButton.setFont(font1)

        self.gridLayout_12.addWidget(self.pushButton, 11, 0, 1, 1)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setSpacing(10)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.repetition_penalty = SliderWidget(self.override_parameters)
        self.repetition_penalty.setObjectName(u"repetition_penalty")
        sizePolicy.setHeightForWidth(self.repetition_penalty.sizePolicy().hasHeightForWidth())
        self.repetition_penalty.setSizePolicy(sizePolicy)
        self.repetition_penalty.setMinimumSize(QSize(0, 0))
        self.repetition_penalty.setProperty("slider_minimum", 1)
        self.repetition_penalty.setProperty("slider_maximum", 10000)
        self.repetition_penalty.setProperty("spinbox_minimum", 0.010000000000000)
        self.repetition_penalty.setProperty("spinbox_maximum", 100.000000000000000)
        self.repetition_penalty.setProperty("display_as_float", True)
        self.repetition_penalty.setProperty("slider_single_step", 0)
        self.repetition_penalty.setProperty("slider_page_step", 1)
        self.repetition_penalty.setProperty("spinbox_single_step", 1.000000000000000)
        self.repetition_penalty.setProperty("spinbox_page_step", 10.000000000000000)

        self.horizontalLayout_2.addWidget(self.repetition_penalty)

        self.min_length = SliderWidget(self.override_parameters)
        self.min_length.setObjectName(u"min_length")
        sizePolicy.setHeightForWidth(self.min_length.sizePolicy().hasHeightForWidth())
        self.min_length.setSizePolicy(sizePolicy)
        self.min_length.setMinimumSize(QSize(0, 0))
        self.min_length.setProperty("slider_minimum", 1)
        self.min_length.setProperty("slider_maximum", 2556)
        self.min_length.setProperty("spinbox_minimum", 1.000000000000000)
        self.min_length.setProperty("spinbox_maximum", 2556.000000000000000)
        self.min_length.setProperty("display_as_float", False)
        self.min_length.setProperty("slider_single_step", 1)
        self.min_length.setProperty("slider_page_step", 2556)
        self.min_length.setProperty("spinbox_single_step", 1)
        self.min_length.setProperty("spinbox_page_step", 2556)

        self.horizontalLayout_2.addWidget(self.min_length)


        self.gridLayout_12.addLayout(self.horizontalLayout_2, 2, 0, 1, 1)


        self.gridLayout.addWidget(self.override_parameters, 1, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_4.addWidget(self.scrollArea, 4, 0, 1, 1)

        self.label_2 = QLabel(llm_settings_widget)
        self.label_2.setObjectName(u"label_2")
        font2 = QFont()
        font2.setPointSize(11)
        font2.setBold(True)
        self.label_2.setFont(font2)

        self.gridLayout_4.addWidget(self.label_2, 0, 0, 1, 1)

        self.line_2 = QFrame(llm_settings_widget)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_4.addWidget(self.line_2, 1, 0, 1, 1)

        self.groupBox = QGroupBox(llm_settings_widget)
        self.groupBox.setObjectName(u"groupBox")
        font3 = QFont()
        font3.setPointSize(10)
        font3.setBold(True)
        self.groupBox.setFont(font3)
        self.verticalLayout = QVBoxLayout(self.groupBox)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(9, 9, 9, 9)
        self.model_service = QComboBox(self.groupBox)
        self.model_service.setObjectName(u"model_service")

        self.verticalLayout.addWidget(self.model_service)


        self.gridLayout_4.addWidget(self.groupBox, 2, 0, 1, 1)

        self.remote_model_path = QGroupBox(llm_settings_widget)
        self.remote_model_path.setObjectName(u"remote_model_path")
        self.remote_model_path.setFont(font3)
        self.verticalLayout_2 = QVBoxLayout(self.remote_model_path)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(9, 9, 9, 9)
        self.model_path = QLineEdit(self.remote_model_path)
        self.model_path.setObjectName(u"model_path")

        self.verticalLayout_2.addWidget(self.model_path)


        self.gridLayout_4.addWidget(self.remote_model_path, 3, 0, 1, 1)

        QWidget.setTabOrder(self.seed, self.random_seed)

        self.retranslateUi(llm_settings_widget)
        self.override_parameters.toggled.connect(llm_settings_widget.override_parameters_toggled)
        self.early_stopping.toggled.connect(llm_settings_widget.early_stopping_toggled)
        self.pushButton.clicked.connect(llm_settings_widget.reset_settings_to_default_clicked)
        self.do_sample.toggled.connect(llm_settings_widget.do_sample_toggled)
        self.use_cache.clicked["bool"].connect(llm_settings_widget.toggle_use_cache)
        self.model_service.currentTextChanged.connect(llm_settings_widget.on_model_service_currentTextChanged)
        self.model_path.textChanged.connect(llm_settings_widget.on_model_path_textChanged)

        QMetaObject.connectSlotsByName(llm_settings_widget)
    # setupUi

    def retranslateUi(self, llm_settings_widget):
        llm_settings_widget.setWindowTitle(QCoreApplication.translate("llm_settings_widget", u"Form", None))
        self.override_parameters.setTitle(QCoreApplication.translate("llm_settings_widget", u"Override Prameters", None))
        self.random_seed.setText(QCoreApplication.translate("llm_settings_widget", u"Random seed", None))
        self.length_penalty.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"llm_generator_settings.length_penalty", None))
        self.length_penalty.setProperty("label_text", QCoreApplication.translate("llm_settings_widget", u"Length Penalty", None))
        self.num_beams.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"llm_generator_settings.num_beams", None))
        self.num_beams.setProperty("label_text", QCoreApplication.translate("llm_settings_widget", u"Num Beams", None))
        self.top_p.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"llm_generator_settings.top_p", None))
        self.top_p.setProperty("label_text", QCoreApplication.translate("llm_settings_widget", u"Top P", None))
        self.max_new_tokens.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"llm_generator_settings.max_new_tokens", None))
        self.max_new_tokens.setProperty("label_text", QCoreApplication.translate("llm_settings_widget", u"Max New Tokens", None))
        self.sequences.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"llm_generator_settings.sequences", None))
        self.sequences.setProperty("label_text", QCoreApplication.translate("llm_settings_widget", u"Sequences", None))
        self.top_k.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"llm_generator_settings.top_k", None))
        self.top_k.setProperty("label_text", QCoreApplication.translate("llm_settings_widget", u"Top K", None))
        self.ngram_size.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"llm_generator_settings.ngram_size", None))
        self.ngram_size.setProperty("label_text", QCoreApplication.translate("llm_settings_widget", u"Ngram Size", None))
        self.temperature.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"llm_generator_settings.temperature", None))
        self.temperature.setProperty("label_text", QCoreApplication.translate("llm_settings_widget", u"Temperature", None))
        self.early_stopping.setText(QCoreApplication.translate("llm_settings_widget", u"Early stopping", None))
        self.use_cache.setText(QCoreApplication.translate("llm_settings_widget", u"Use Cache", None))
        self.do_sample.setText(QCoreApplication.translate("llm_settings_widget", u"Do sample", None))
        self.pushButton.setText(QCoreApplication.translate("llm_settings_widget", u"Reset Settings to Default", None))
        self.repetition_penalty.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"llm_generator_settings.repetition_penalty", None))
        self.repetition_penalty.setProperty("label_text", QCoreApplication.translate("llm_settings_widget", u"Repetition Penalty", None))
        self.min_length.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"llm_generator_settings.min_length", None))
        self.min_length.setProperty("label_text", QCoreApplication.translate("llm_settings_widget", u"Min Length", None))
        self.label_2.setText(QCoreApplication.translate("llm_settings_widget", u"LLM Settings", None))
        self.groupBox.setTitle(QCoreApplication.translate("llm_settings_widget", u"Model service", None))
        self.remote_model_path.setTitle(QCoreApplication.translate("llm_settings_widget", u"Custom path", None))
    # retranslateUi

