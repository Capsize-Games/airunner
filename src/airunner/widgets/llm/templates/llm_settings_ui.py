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
    QLayout, QLineEdit, QPushButton, QRadioButton,
    QSizePolicy, QWidget)

from airunner.widgets.slider.slider_widget import SliderWidget

class Ui_llm_settings_widget(object):
    def setupUi(self, llm_settings_widget):
        if not llm_settings_widget.objectName():
            llm_settings_widget.setObjectName(u"llm_settings_widget")
        llm_settings_widget.resize(1201, 1064)
        self.gridLayout = QGridLayout(llm_settings_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.groupBox_6 = QGroupBox(llm_settings_widget)
        self.groupBox_6.setObjectName(u"groupBox_6")
        self.gridLayout_9 = QGridLayout(self.groupBox_6)
        self.gridLayout_9.setObjectName(u"gridLayout_9")
        self.use_gpu_checkbox = QCheckBox(self.groupBox_6)
        self.use_gpu_checkbox.setObjectName(u"use_gpu_checkbox")

        self.gridLayout_9.addWidget(self.use_gpu_checkbox, 0, 0, 1, 1)

        self.dtype_description = QLabel(self.groupBox_6)
        self.dtype_description.setObjectName(u"dtype_description")
        font = QFont()
        font.setPointSize(9)
        self.dtype_description.setFont(font)

        self.gridLayout_9.addWidget(self.dtype_description, 2, 0, 1, 1)

        self.dtype_combobox = QComboBox(self.groupBox_6)
        self.dtype_combobox.addItem("")
        self.dtype_combobox.addItem("")
        self.dtype_combobox.addItem("")
        self.dtype_combobox.addItem("")
        self.dtype_combobox.addItem("")
        self.dtype_combobox.setObjectName(u"dtype_combobox")

        self.gridLayout_9.addWidget(self.dtype_combobox, 1, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_6, 2, 0, 1, 1)

        self.groupBox_8 = QGroupBox(llm_settings_widget)
        self.groupBox_8.setObjectName(u"groupBox_8")
        self.gridLayout_11 = QGridLayout(self.groupBox_8)
        self.gridLayout_11.setObjectName(u"gridLayout_11")
        self.model_version = QComboBox(self.groupBox_8)
        self.model_version.setObjectName(u"model_version")

        self.gridLayout_11.addWidget(self.model_version, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_8, 3, 0, 1, 1)

        self.groupBox = QGroupBox(llm_settings_widget)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout_2 = QGridLayout(self.groupBox)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.manual_tools = QRadioButton(self.groupBox)
        self.manual_tools.setObjectName(u"manual_tools")

        self.horizontalLayout_7.addWidget(self.manual_tools)

        self.automatic_tools = QRadioButton(self.groupBox)
        self.automatic_tools.setObjectName(u"automatic_tools")

        self.horizontalLayout_7.addWidget(self.automatic_tools)


        self.gridLayout_2.addLayout(self.horizontalLayout_7, 3, 0, 1, 1)

        self.label = QLabel(self.groupBox)
        self.label.setObjectName(u"label")
        self.label.setFont(font)

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox, 1, 0, 1, 1)

        self.groupBox_7 = QGroupBox(llm_settings_widget)
        self.groupBox_7.setObjectName(u"groupBox_7")
        self.gridLayout_10 = QGridLayout(self.groupBox_7)
        self.gridLayout_10.setObjectName(u"gridLayout_10")
        self.model = QComboBox(self.groupBox_7)
        self.model.setObjectName(u"model")

        self.gridLayout_10.addWidget(self.model, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_7, 0, 0, 1, 1)

        self.override_parameters = QGroupBox(llm_settings_widget)
        self.override_parameters.setObjectName(u"override_parameters")
        self.override_parameters.setCheckable(True)
        self.override_parameters.setChecked(True)
        self.gridLayout_12 = QGridLayout(self.override_parameters)
        self.gridLayout_12.setObjectName(u"gridLayout_12")
        self.gridLayout_3 = QGridLayout()
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.early_stopping = QCheckBox(self.override_parameters)
        self.early_stopping.setObjectName(u"early_stopping")

        self.gridLayout_3.addWidget(self.early_stopping, 0, 0, 1, 1)

        self.do_sample = QCheckBox(self.override_parameters)
        self.do_sample.setObjectName(u"do_sample")

        self.gridLayout_3.addWidget(self.do_sample, 0, 1, 1, 1)

        self.cache_quantized_model_toggle = QCheckBox(self.override_parameters)
        self.cache_quantized_model_toggle.setObjectName(u"cache_quantized_model_toggle")
        self.cache_quantized_model_toggle.setMinimumSize(QSize(0, 20))

        self.gridLayout_3.addWidget(self.cache_quantized_model_toggle, 0, 2, 1, 1)


        self.gridLayout_12.addLayout(self.gridLayout_3, 8, 0, 1, 1)

        self.line = QFrame(self.override_parameters)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_12.addWidget(self.line, 9, 0, 1, 1)

        self.label_3 = QLabel(self.override_parameters)
        self.label_3.setObjectName(u"label_3")
        font1 = QFont()
        font1.setBold(True)
        self.label_3.setFont(font1)

        self.gridLayout_12.addWidget(self.label_3, 10, 0, 1, 1)

        self.pushButton = QPushButton(self.override_parameters)
        self.pushButton.setObjectName(u"pushButton")

        self.gridLayout_12.addWidget(self.pushButton, 14, 0, 1, 1)

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.sequences = SliderWidget(self.override_parameters)
        self.sequences.setObjectName(u"sequences")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
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

        self.horizontalLayout_12 = QHBoxLayout()
        self.horizontalLayout_12.setObjectName(u"horizontalLayout_12")
        self.leave_in_vram = QRadioButton(self.override_parameters)
        self.leave_in_vram.setObjectName(u"leave_in_vram")
        self.leave_in_vram.setMinimumSize(QSize(0, 20))

        self.horizontalLayout_12.addWidget(self.leave_in_vram)

        self.move_to_cpu = QRadioButton(self.override_parameters)
        self.move_to_cpu.setObjectName(u"move_to_cpu")
        self.move_to_cpu.setMinimumSize(QSize(0, 20))

        self.horizontalLayout_12.addWidget(self.move_to_cpu)

        self.unload_model = QRadioButton(self.override_parameters)
        self.unload_model.setObjectName(u"unload_model")
        self.unload_model.setMinimumSize(QSize(0, 20))

        self.horizontalLayout_12.addWidget(self.unload_model)


        self.gridLayout_12.addLayout(self.horizontalLayout_12, 12, 0, 1, 1)

        self.horizontalLayout_5 = QHBoxLayout()
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
        self.temperature.setProperty("slider_maximum", 20000)
        self.temperature.setProperty("spinbox_minimum", 0.000100000000000)
        self.temperature.setProperty("spinbox_maximum", 2.000000000000000)
        self.temperature.setProperty("display_as_float", True)
        self.temperature.setProperty("slider_single_step", 1)
        self.temperature.setProperty("slider_page_step", 10)
        self.temperature.setProperty("spinbox_single_step", 0.010000000000000)
        self.temperature.setProperty("spinbox_page_step", 0.100000000000000)

        self.horizontalLayout_5.addWidget(self.temperature)


        self.gridLayout_12.addLayout(self.horizontalLayout_5, 4, 0, 1, 1)

        self.groupBox_19 = QGroupBox(self.override_parameters)
        self.groupBox_19.setObjectName(u"groupBox_19")
        self.horizontalLayout_4 = QHBoxLayout(self.groupBox_19)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.seed = QLineEdit(self.groupBox_19)
        self.seed.setObjectName(u"seed")
        self.seed.setMinimumSize(QSize(0, 20))

        self.horizontalLayout_4.addWidget(self.seed)

        self.random_seed = QCheckBox(self.groupBox_19)
        self.random_seed.setObjectName(u"random_seed")
        self.random_seed.setMinimumSize(QSize(0, 20))

        self.horizontalLayout_4.addWidget(self.random_seed)


        self.gridLayout_12.addWidget(self.groupBox_19, 6, 0, 1, 1)

        self.horizontalLayout_2 = QHBoxLayout()
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

        self.horizontalLayout = QHBoxLayout()
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

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.length_penalty = SliderWidget(self.override_parameters)
        self.length_penalty.setObjectName(u"length_penalty")
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

        self.label_4 = QLabel(self.override_parameters)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setFont(font)

        self.gridLayout_12.addWidget(self.label_4, 11, 0, 1, 1)


        self.gridLayout.addWidget(self.override_parameters, 5, 0, 1, 1)

        self.groupBox_14 = QGroupBox(llm_settings_widget)
        self.groupBox_14.setObjectName(u"groupBox_14")
        self.gridLayout_17 = QGridLayout(self.groupBox_14)
        self.gridLayout_17.setObjectName(u"gridLayout_17")
        self.prompt_template = QComboBox(self.groupBox_14)
        self.prompt_template.setObjectName(u"prompt_template")

        self.gridLayout_17.addWidget(self.prompt_template, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_14, 4, 0, 1, 1)

        QWidget.setTabOrder(self.model, self.model_version)
        QWidget.setTabOrder(self.model_version, self.use_gpu_checkbox)
        QWidget.setTabOrder(self.use_gpu_checkbox, self.seed)
        QWidget.setTabOrder(self.seed, self.random_seed)

        self.retranslateUi(llm_settings_widget)
        self.use_gpu_checkbox.toggled.connect(llm_settings_widget.use_gpu_toggled)
        self.override_parameters.toggled.connect(llm_settings_widget.override_parameters_toggled)
        self.seed.textEdited.connect(llm_settings_widget.seed_changed)
        self.early_stopping.toggled.connect(llm_settings_widget.early_stopping_toggled)
        self.random_seed.toggled.connect(llm_settings_widget.random_seed_toggled)
        self.pushButton.clicked.connect(llm_settings_widget.reset_settings_to_default_clicked)
        self.move_to_cpu.toggled.connect(llm_settings_widget.toggle_move_model_to_cpu)
        self.do_sample.toggled.connect(llm_settings_widget.do_sample_toggled)
        self.leave_in_vram.toggled.connect(llm_settings_widget.toggle_leave_model_in_vram)
        self.unload_model.toggled.connect(llm_settings_widget.toggle_unload_model)
        self.prompt_template.currentTextChanged.connect(llm_settings_widget.prompt_template_text_changed)
        self.model.currentTextChanged.connect(llm_settings_widget.model_text_changed)
        self.model_version.currentTextChanged.connect(llm_settings_widget.model_version_changed)
        self.manual_tools.clicked.connect(llm_settings_widget.enable_manual_tools)
        self.automatic_tools.clicked.connect(llm_settings_widget.enable_automatic_tools)
        self.cache_quantized_model_toggle.toggled.connect(llm_settings_widget.toggle_cache_quantized_model)

        self.model_version.setCurrentIndex(-1)


        QMetaObject.connectSlotsByName(llm_settings_widget)
    # setupUi

    def retranslateUi(self, llm_settings_widget):
        llm_settings_widget.setWindowTitle(QCoreApplication.translate("llm_settings_widget", u"Form", None))
        self.groupBox_6.setTitle(QCoreApplication.translate("llm_settings_widget", u"DType", None))
        self.use_gpu_checkbox.setText(QCoreApplication.translate("llm_settings_widget", u"Use GPU", None))
        self.dtype_description.setText(QCoreApplication.translate("llm_settings_widget", u"Description", None))
        self.dtype_combobox.setItemText(0, QCoreApplication.translate("llm_settings_widget", u"32-bit", None))
        self.dtype_combobox.setItemText(1, QCoreApplication.translate("llm_settings_widget", u"16-bit", None))
        self.dtype_combobox.setItemText(2, QCoreApplication.translate("llm_settings_widget", u"8-bit", None))
        self.dtype_combobox.setItemText(3, QCoreApplication.translate("llm_settings_widget", u"4-bit", None))
        self.dtype_combobox.setItemText(4, QCoreApplication.translate("llm_settings_widget", u"2-bit", None))

        self.groupBox_8.setTitle(QCoreApplication.translate("llm_settings_widget", u"Model Version", None))
        self.groupBox.setTitle(QCoreApplication.translate("llm_settings_widget", u"Tools", None))
        self.manual_tools.setText(QCoreApplication.translate("llm_settings_widget", u"Manual", None))
        self.automatic_tools.setText(QCoreApplication.translate("llm_settings_widget", u"Automatic", None))
        self.label.setText(QCoreApplication.translate("llm_settings_widget", u"LLMs can use a variety of tools. These settings define how the LLM will use those tools.", None))
        self.groupBox_7.setTitle(QCoreApplication.translate("llm_settings_widget", u"Model Type", None))
        self.override_parameters.setTitle(QCoreApplication.translate("llm_settings_widget", u"Override Prameters", None))
        self.early_stopping.setText(QCoreApplication.translate("llm_settings_widget", u"Early stopping", None))
        self.do_sample.setText(QCoreApplication.translate("llm_settings_widget", u"Do sample", None))
        self.cache_quantized_model_toggle.setText(QCoreApplication.translate("llm_settings_widget", u"Cache Quantized model to disk", None))
        self.label_3.setText(QCoreApplication.translate("llm_settings_widget", u"Model management", None))
        self.pushButton.setText(QCoreApplication.translate("llm_settings_widget", u"Reset Settings to Default", None))
        self.sequences.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"sequences", None))
        self.sequences.setProperty("label_text", QCoreApplication.translate("llm_settings_widget", u"Sequences", None))
        self.top_k.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"top_k", None))
        self.top_k.setProperty("label_text", QCoreApplication.translate("llm_settings_widget", u"Top K", None))
        self.leave_in_vram.setText(QCoreApplication.translate("llm_settings_widget", u"Leave in VRAM", None))
        self.move_to_cpu.setText(QCoreApplication.translate("llm_settings_widget", u"Move to CPU", None))
        self.unload_model.setText(QCoreApplication.translate("llm_settings_widget", u"Unload model", None))
        self.ngram_size.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"ngram_size", None))
        self.ngram_size.setProperty("label_text", QCoreApplication.translate("llm_settings_widget", u"Ngram Size", None))
        self.temperature.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"temperature", None))
        self.temperature.setProperty("label_text", QCoreApplication.translate("llm_settings_widget", u"Temperature", None))
        self.groupBox_19.setTitle(QCoreApplication.translate("llm_settings_widget", u"Seed", None))
        self.random_seed.setText(QCoreApplication.translate("llm_settings_widget", u"Random seed", None))
        self.repetition_penalty.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"repetition_penalty", None))
        self.repetition_penalty.setProperty("label_text", QCoreApplication.translate("llm_settings_widget", u"Repetition Penalty", None))
        self.min_length.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"min_length", None))
        self.min_length.setProperty("label_text", QCoreApplication.translate("llm_settings_widget", u"Min Length", None))
        self.top_p.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"top_p", None))
        self.top_p.setProperty("label_text", QCoreApplication.translate("llm_settings_widget", u"Top P", None))
        self.max_new_tokens.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"max_new_tokens", None))
        self.max_new_tokens.setProperty("label_text", QCoreApplication.translate("llm_settings_widget", u"Max New Tokens", None))
        self.length_penalty.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"length_penalty", None))
        self.length_penalty.setProperty("label_text", QCoreApplication.translate("llm_settings_widget", u"Length Penalty", None))
        self.num_beams.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"num_beams", None))
        self.num_beams.setProperty("label_text", QCoreApplication.translate("llm_settings_widget", u"Num Beams", None))
        self.label_4.setText(QCoreApplication.translate("llm_settings_widget", u"How to treat model when not in use", None))
        self.groupBox_14.setTitle(QCoreApplication.translate("llm_settings_widget", u"Prompt Template", None))
    # retranslateUi

