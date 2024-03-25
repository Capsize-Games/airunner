# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'llm_settings.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QRadioButton, QSizePolicy,
    QSpacerItem, QWidget)

from airunner.widgets.slider.slider_widget import SliderWidget

class Ui_llm_settings_widget(object):
    def setupUi(self, llm_settings_widget):
        if not llm_settings_widget.objectName():
            llm_settings_widget.setObjectName(u"llm_settings_widget")
        llm_settings_widget.resize(759, 1036)
        self.gridLayout = QGridLayout(llm_settings_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.groupBox_8 = QGroupBox(llm_settings_widget)
        self.groupBox_8.setObjectName(u"groupBox_8")
        self.gridLayout_11 = QGridLayout(self.groupBox_8)
        self.gridLayout_11.setObjectName(u"gridLayout_11")
        self.model_version = QComboBox(self.groupBox_8)
        self.model_version.setObjectName(u"model_version")

        self.gridLayout_11.addWidget(self.model_version, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_8, 1, 0, 1, 2)

        self.groupBox_6 = QGroupBox(llm_settings_widget)
        self.groupBox_6.setObjectName(u"groupBox_6")
        self.gridLayout_9 = QGridLayout(self.groupBox_6)
        self.gridLayout_9.setObjectName(u"gridLayout_9")
        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.radio_button_2bit = QRadioButton(self.groupBox_6)
        self.radio_button_2bit.setObjectName(u"radio_button_2bit")

        self.horizontalLayout_3.addWidget(self.radio_button_2bit)

        self.radio_button_4bit = QRadioButton(self.groupBox_6)
        self.radio_button_4bit.setObjectName(u"radio_button_4bit")

        self.horizontalLayout_3.addWidget(self.radio_button_4bit)

        self.radio_button_8bit = QRadioButton(self.groupBox_6)
        self.radio_button_8bit.setObjectName(u"radio_button_8bit")

        self.horizontalLayout_3.addWidget(self.radio_button_8bit)

        self.radio_button_16bit = QRadioButton(self.groupBox_6)
        self.radio_button_16bit.setObjectName(u"radio_button_16bit")

        self.horizontalLayout_3.addWidget(self.radio_button_16bit)

        self.radio_button_32bit = QRadioButton(self.groupBox_6)
        self.radio_button_32bit.setObjectName(u"radio_button_32bit")

        self.horizontalLayout_3.addWidget(self.radio_button_32bit)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer)


        self.gridLayout_9.addLayout(self.horizontalLayout_3, 1, 0, 1, 1)

        self.dtype_description = QLabel(self.groupBox_6)
        self.dtype_description.setObjectName(u"dtype_description")
        font = QFont()
        font.setPointSize(9)
        self.dtype_description.setFont(font)

        self.gridLayout_9.addWidget(self.dtype_description, 2, 0, 1, 1)

        self.use_gpu_checkbox = QCheckBox(self.groupBox_6)
        self.use_gpu_checkbox.setObjectName(u"use_gpu_checkbox")

        self.gridLayout_9.addWidget(self.use_gpu_checkbox, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_6, 4, 0, 1, 2)

        self.override_parameters = QGroupBox(llm_settings_widget)
        self.override_parameters.setObjectName(u"override_parameters")
        self.override_parameters.setCheckable(True)
        self.override_parameters.setChecked(True)
        self.gridLayout_12 = QGridLayout(self.override_parameters)
        self.gridLayout_12.setObjectName(u"gridLayout_12")
        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.early_stopping = QCheckBox(self.override_parameters)
        self.early_stopping.setObjectName(u"early_stopping")

        self.horizontalLayout_6.addWidget(self.early_stopping)

        self.do_sample = QCheckBox(self.override_parameters)
        self.do_sample.setObjectName(u"do_sample")

        self.horizontalLayout_6.addWidget(self.do_sample)

        self.cache_quantized_model_toggle = QCheckBox(self.override_parameters)
        self.cache_quantized_model_toggle.setObjectName(u"cache_quantized_model_toggle")

        self.horizontalLayout_6.addWidget(self.cache_quantized_model_toggle)


        self.gridLayout_12.addLayout(self.horizontalLayout_6, 7, 0, 1, 1)

        self.line = QFrame(self.override_parameters)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.gridLayout_12.addWidget(self.line, 8, 0, 1, 1)

        self.horizontalLayout_11 = QHBoxLayout()
        self.horizontalLayout_11.setObjectName(u"horizontalLayout_11")
        self.groupBox_24 = QGroupBox(self.override_parameters)
        self.groupBox_24.setObjectName(u"groupBox_24")
        self.gridLayout_28 = QGridLayout(self.groupBox_24)
        self.gridLayout_28.setObjectName(u"gridLayout_28")
        self.length_penalty = SliderWidget(self.groupBox_24)
        self.length_penalty.setObjectName(u"length_penalty")
        self.length_penalty.setProperty("slider_minimum", -100)
        self.length_penalty.setProperty("slider_maximum", 100)
        self.length_penalty.setProperty("spinbox_minimum", 0.000000000000000)
        self.length_penalty.setProperty("spinbox_maximum", 1.000000000000000)
        self.length_penalty.setProperty("display_as_float", True)
        self.length_penalty.setProperty("slider_single_step", 1)
        self.length_penalty.setProperty("slider_page_step", 10)
        self.length_penalty.setProperty("spinbox_single_step", 0.010000000000000)
        self.length_penalty.setProperty("spinbox_page_step", 0.100000000000000)

        self.gridLayout_28.addWidget(self.length_penalty, 0, 0, 1, 1)


        self.horizontalLayout_11.addWidget(self.groupBox_24)

        self.groupBox_25 = QGroupBox(self.override_parameters)
        self.groupBox_25.setObjectName(u"groupBox_25")
        self.gridLayout_29 = QGridLayout(self.groupBox_25)
        self.gridLayout_29.setObjectName(u"gridLayout_29")
        self.num_beams = SliderWidget(self.groupBox_25)
        self.num_beams.setObjectName(u"num_beams")
        self.num_beams.setProperty("slider_minimum", 1)
        self.num_beams.setProperty("slider_maximum", 100)
        self.num_beams.setProperty("spinbox_minimum", 0.000000000000000)
        self.num_beams.setProperty("spinbox_maximum", 100.000000000000000)
        self.num_beams.setProperty("display_as_float", False)
        self.num_beams.setProperty("slider_single_step", 1)
        self.num_beams.setProperty("slider_page_step", 10)
        self.num_beams.setProperty("spinbox_single_step", 0.010000000000000)
        self.num_beams.setProperty("spinbox_page_step", 0.100000000000000)

        self.gridLayout_29.addWidget(self.num_beams, 0, 0, 1, 1)


        self.horizontalLayout_11.addWidget(self.groupBox_25)


        self.gridLayout_12.addLayout(self.horizontalLayout_11, 2, 0, 1, 1)

        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.groupBox_17 = QGroupBox(self.override_parameters)
        self.groupBox_17.setObjectName(u"groupBox_17")
        self.gridLayout_21 = QGridLayout(self.groupBox_17)
        self.gridLayout_21.setObjectName(u"gridLayout_21")
        self.ngram_size = SliderWidget(self.groupBox_17)
        self.ngram_size.setObjectName(u"ngram_size")
        self.ngram_size.setProperty("slider_minimum", 0)
        self.ngram_size.setProperty("slider_maximum", 20)
        self.ngram_size.setProperty("spinbox_minimum", 0.000000000000000)
        self.ngram_size.setProperty("spinbox_maximum", 20.000000000000000)
        self.ngram_size.setProperty("display_as_float", False)
        self.ngram_size.setProperty("slider_single_step", 1)
        self.ngram_size.setProperty("slider_page_step", 1)
        self.ngram_size.setProperty("spinbox_single_step", 1.000000000000000)
        self.ngram_size.setProperty("spinbox_page_step", 1.000000000000000)

        self.gridLayout_21.addWidget(self.ngram_size, 0, 0, 1, 1)


        self.horizontalLayout_8.addWidget(self.groupBox_17)

        self.groupBox_18 = QGroupBox(self.override_parameters)
        self.groupBox_18.setObjectName(u"groupBox_18")
        self.gridLayout_22 = QGridLayout(self.groupBox_18)
        self.gridLayout_22.setObjectName(u"gridLayout_22")
        self.temperature = SliderWidget(self.groupBox_18)
        self.temperature.setObjectName(u"temperature")
        self.temperature.setProperty("slider_minimum", 1)
        self.temperature.setProperty("slider_maximum", 20000)
        self.temperature.setProperty("spinbox_minimum", 0.000100000000000)
        self.temperature.setProperty("spinbox_maximum", 2.000000000000000)
        self.temperature.setProperty("display_as_float", True)
        self.temperature.setProperty("slider_single_step", 1)
        self.temperature.setProperty("slider_page_step", 10)
        self.temperature.setProperty("spinbox_single_step", 0.010000000000000)
        self.temperature.setProperty("spinbox_page_step", 0.100000000000000)

        self.gridLayout_22.addWidget(self.temperature, 0, 0, 1, 1)


        self.horizontalLayout_8.addWidget(self.groupBox_18)


        self.gridLayout_12.addLayout(self.horizontalLayout_8, 3, 0, 1, 1)

        self.horizontalLayout_12 = QHBoxLayout()
        self.horizontalLayout_12.setObjectName(u"horizontalLayout_12")
        self.leave_in_vram = QRadioButton(self.override_parameters)
        self.leave_in_vram.setObjectName(u"leave_in_vram")

        self.horizontalLayout_12.addWidget(self.leave_in_vram)

        self.move_to_cpu = QRadioButton(self.override_parameters)
        self.move_to_cpu.setObjectName(u"move_to_cpu")

        self.horizontalLayout_12.addWidget(self.move_to_cpu)

        self.unload_model = QRadioButton(self.override_parameters)
        self.unload_model.setObjectName(u"unload_model")

        self.horizontalLayout_12.addWidget(self.unload_model)


        self.gridLayout_12.addLayout(self.horizontalLayout_12, 11, 0, 1, 1)

        self.groupBox_19 = QGroupBox(self.override_parameters)
        self.groupBox_19.setObjectName(u"groupBox_19")
        self.horizontalLayout_4 = QHBoxLayout(self.groupBox_19)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.seed = QLineEdit(self.groupBox_19)
        self.seed.setObjectName(u"seed")

        self.horizontalLayout_4.addWidget(self.seed)

        self.random_seed = QCheckBox(self.groupBox_19)
        self.random_seed.setObjectName(u"random_seed")

        self.horizontalLayout_4.addWidget(self.random_seed)


        self.gridLayout_12.addWidget(self.groupBox_19, 5, 0, 1, 1)

        self.label_3 = QLabel(self.override_parameters)
        self.label_3.setObjectName(u"label_3")
        font1 = QFont()
        font1.setBold(True)
        self.label_3.setFont(font1)

        self.gridLayout_12.addWidget(self.label_3, 9, 0, 1, 1)

        self.label_4 = QLabel(self.override_parameters)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setFont(font)

        self.gridLayout_12.addWidget(self.label_4, 10, 0, 1, 1)

        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.groupBox_11 = QGroupBox(self.override_parameters)
        self.groupBox_11.setObjectName(u"groupBox_11")
        self.gridLayout_19 = QGridLayout(self.groupBox_11)
        self.gridLayout_19.setObjectName(u"gridLayout_19")
        self.repetition_penalty = SliderWidget(self.groupBox_11)
        self.repetition_penalty.setObjectName(u"repetition_penalty")
        self.repetition_penalty.setProperty("slider_minimum", 1)
        self.repetition_penalty.setProperty("slider_maximum", 10000)
        self.repetition_penalty.setProperty("spinbox_minimum", 0.010000000000000)
        self.repetition_penalty.setProperty("spinbox_maximum", 100.000000000000000)
        self.repetition_penalty.setProperty("display_as_float", True)
        self.repetition_penalty.setProperty("slider_single_step", 0)
        self.repetition_penalty.setProperty("slider_page_step", 1)
        self.repetition_penalty.setProperty("spinbox_single_step", 1.000000000000000)
        self.repetition_penalty.setProperty("spinbox_page_step", 10.000000000000000)

        self.gridLayout_19.addWidget(self.repetition_penalty, 0, 0, 1, 1)


        self.horizontalLayout_7.addWidget(self.groupBox_11)

        self.groupBox_16 = QGroupBox(self.override_parameters)
        self.groupBox_16.setObjectName(u"groupBox_16")
        self.gridLayout_20 = QGridLayout(self.groupBox_16)
        self.gridLayout_20.setObjectName(u"gridLayout_20")
        self.min_length = SliderWidget(self.groupBox_16)
        self.min_length.setObjectName(u"min_length")
        self.min_length.setProperty("slider_minimum", 1)
        self.min_length.setProperty("slider_maximum", 2556)
        self.min_length.setProperty("spinbox_minimum", 1.000000000000000)
        self.min_length.setProperty("spinbox_maximum", 2556.000000000000000)
        self.min_length.setProperty("display_as_float", False)
        self.min_length.setProperty("slider_single_step", 1)
        self.min_length.setProperty("slider_page_step", 2556)
        self.min_length.setProperty("spinbox_single_step", 1)
        self.min_length.setProperty("spinbox_page_step", 2556)

        self.gridLayout_20.addWidget(self.min_length, 0, 0, 1, 1)


        self.horizontalLayout_7.addWidget(self.groupBox_16)


        self.gridLayout_12.addLayout(self.horizontalLayout_7, 1, 0, 1, 1)

        self.horizontalLayout_10 = QHBoxLayout()
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.groupBox_22 = QGroupBox(self.override_parameters)
        self.groupBox_22.setObjectName(u"groupBox_22")
        self.gridLayout_26 = QGridLayout(self.groupBox_22)
        self.gridLayout_26.setObjectName(u"gridLayout_26")
        self.sequences = SliderWidget(self.groupBox_22)
        self.sequences.setObjectName(u"sequences")
        self.sequences.setProperty("slider_minimum", 1)
        self.sequences.setProperty("slider_maximum", 100)
        self.sequences.setProperty("spinbox_minimum", 0.000000000000000)
        self.sequences.setProperty("spinbox_maximum", 100.000000000000000)
        self.sequences.setProperty("display_as_float", False)
        self.sequences.setProperty("slider_single_step", 1)
        self.sequences.setProperty("slider_page_step", 10)
        self.sequences.setProperty("spinbox_single_step", 0.010000000000000)
        self.sequences.setProperty("spinbox_page_step", 0.100000000000000)

        self.gridLayout_26.addWidget(self.sequences, 0, 0, 1, 1)


        self.horizontalLayout_10.addWidget(self.groupBox_22)

        self.groupBox_23 = QGroupBox(self.override_parameters)
        self.groupBox_23.setObjectName(u"groupBox_23")
        self.gridLayout_27 = QGridLayout(self.groupBox_23)
        self.gridLayout_27.setObjectName(u"gridLayout_27")
        self.top_k = SliderWidget(self.groupBox_23)
        self.top_k.setObjectName(u"top_k")
        self.top_k.setProperty("slider_minimum", 0)
        self.top_k.setProperty("slider_maximum", 256)
        self.top_k.setProperty("spinbox_minimum", 0.000000000000000)
        self.top_k.setProperty("spinbox_maximum", 256.000000000000000)
        self.top_k.setProperty("display_as_float", False)
        self.top_k.setProperty("slider_single_step", 1)
        self.top_k.setProperty("slider_page_step", 10)
        self.top_k.setProperty("spinbox_single_step", 1)
        self.top_k.setProperty("spinbox_page_step", 10)

        self.gridLayout_27.addWidget(self.top_k, 0, 0, 1, 1)


        self.horizontalLayout_10.addWidget(self.groupBox_23)


        self.gridLayout_12.addLayout(self.horizontalLayout_10, 4, 0, 1, 1)

        self.horizontalLayout_9 = QHBoxLayout()
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.groupBox_20 = QGroupBox(self.override_parameters)
        self.groupBox_20.setObjectName(u"groupBox_20")
        self.gridLayout_24 = QGridLayout(self.groupBox_20)
        self.gridLayout_24.setObjectName(u"gridLayout_24")
        self.top_p = SliderWidget(self.groupBox_20)
        self.top_p.setObjectName(u"top_p")
        self.top_p.setProperty("slider_minimum", 1)
        self.top_p.setProperty("slider_maximum", 100)
        self.top_p.setProperty("spinbox_minimum", 0.000000000000000)
        self.top_p.setProperty("spinbox_maximum", 1.000000000000000)
        self.top_p.setProperty("display_as_float", True)
        self.top_p.setProperty("slider_single_step", 1)
        self.top_p.setProperty("slider_page_step", 10)
        self.top_p.setProperty("spinbox_single_step", 0.010000000000000)
        self.top_p.setProperty("spinbox_page_step", 0.100000000000000)

        self.gridLayout_24.addWidget(self.top_p, 0, 0, 1, 1)


        self.horizontalLayout_9.addWidget(self.groupBox_20)

        self.groupBox_21 = QGroupBox(self.override_parameters)
        self.groupBox_21.setObjectName(u"groupBox_21")
        self.gridLayout_25 = QGridLayout(self.groupBox_21)
        self.gridLayout_25.setObjectName(u"gridLayout_25")
        self.max_length = SliderWidget(self.groupBox_21)
        self.max_length.setObjectName(u"max_length")
        self.max_length.setProperty("slider_minimum", 1)
        self.max_length.setProperty("slider_maximum", 2556)
        self.max_length.setProperty("spinbox_minimum", 1.000000000000000)
        self.max_length.setProperty("spinbox_maximum", 2556.000000000000000)
        self.max_length.setProperty("display_as_float", False)
        self.max_length.setProperty("slider_single_step", 1)
        self.max_length.setProperty("slider_page_step", 2556)
        self.max_length.setProperty("spinbox_single_step", 1)
        self.max_length.setProperty("spinbox_page_step", 2556)

        self.gridLayout_25.addWidget(self.max_length, 0, 0, 1, 1)


        self.horizontalLayout_9.addWidget(self.groupBox_21)


        self.gridLayout_12.addLayout(self.horizontalLayout_9, 0, 0, 1, 1)

        self.pushButton = QPushButton(self.override_parameters)
        self.pushButton.setObjectName(u"pushButton")

        self.gridLayout_12.addWidget(self.pushButton, 13, 0, 1, 1)


        self.gridLayout.addWidget(self.override_parameters, 5, 0, 1, 2)

        self.groupBox_7 = QGroupBox(llm_settings_widget)
        self.groupBox_7.setObjectName(u"groupBox_7")
        self.gridLayout_10 = QGridLayout(self.groupBox_7)
        self.gridLayout_10.setObjectName(u"gridLayout_10")
        self.model = QComboBox(self.groupBox_7)
        self.model.setObjectName(u"model")

        self.gridLayout_10.addWidget(self.model, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_7, 0, 0, 1, 2)

        self.groupBox_14 = QGroupBox(llm_settings_widget)
        self.groupBox_14.setObjectName(u"groupBox_14")
        self.gridLayout_17 = QGridLayout(self.groupBox_14)
        self.gridLayout_17.setObjectName(u"gridLayout_17")
        self.prompt_template = QComboBox(self.groupBox_14)
        self.prompt_template.setObjectName(u"prompt_template")

        self.gridLayout_17.addWidget(self.prompt_template, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_14, 2, 0, 1, 2)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 6, 0, 1, 1)

        self.groupBox = QGroupBox(llm_settings_widget)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout_2 = QGridLayout(self.groupBox)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.manual_tools = QRadioButton(self.groupBox)
        self.manual_tools.setObjectName(u"manual_tools")

        self.horizontalLayout.addWidget(self.manual_tools)

        self.automatic_tools = QRadioButton(self.groupBox)
        self.automatic_tools.setObjectName(u"automatic_tools")

        self.horizontalLayout.addWidget(self.automatic_tools)


        self.gridLayout_2.addLayout(self.horizontalLayout, 3, 0, 1, 1)

        self.label = QLabel(self.groupBox)
        self.label.setObjectName(u"label")
        self.label.setFont(font)

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox, 3, 0, 1, 2)

        QWidget.setTabOrder(self.model, self.model_version)
        QWidget.setTabOrder(self.model_version, self.use_gpu_checkbox)
        QWidget.setTabOrder(self.use_gpu_checkbox, self.radio_button_4bit)
        QWidget.setTabOrder(self.radio_button_4bit, self.radio_button_8bit)
        QWidget.setTabOrder(self.radio_button_8bit, self.radio_button_16bit)
        QWidget.setTabOrder(self.radio_button_16bit, self.radio_button_32bit)
        QWidget.setTabOrder(self.radio_button_32bit, self.seed)
        QWidget.setTabOrder(self.seed, self.random_seed)

        self.retranslateUi(llm_settings_widget)
        self.radio_button_2bit.toggled.connect(llm_settings_widget.toggled_2bit)
        self.radio_button_16bit.toggled.connect(llm_settings_widget.toggled_16bit)
        self.use_gpu_checkbox.toggled.connect(llm_settings_widget.use_gpu_toggled)
        self.radio_button_4bit.toggled.connect(llm_settings_widget.toggled_4bit)
        self.radio_button_8bit.toggled.connect(llm_settings_widget.toggled_8bit)
        self.radio_button_32bit.toggled.connect(llm_settings_widget.toggled_32bit)
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
        self.groupBox_8.setTitle(QCoreApplication.translate("llm_settings_widget", u"Model Version", None))
        self.groupBox_6.setTitle(QCoreApplication.translate("llm_settings_widget", u"DType", None))
        self.radio_button_2bit.setText(QCoreApplication.translate("llm_settings_widget", u"2-bit", None))
        self.radio_button_4bit.setText(QCoreApplication.translate("llm_settings_widget", u"4-bit", None))
        self.radio_button_8bit.setText(QCoreApplication.translate("llm_settings_widget", u"8-bit", None))
        self.radio_button_16bit.setText(QCoreApplication.translate("llm_settings_widget", u"16-bit", None))
        self.radio_button_32bit.setText(QCoreApplication.translate("llm_settings_widget", u"32-bit", None))
        self.dtype_description.setText(QCoreApplication.translate("llm_settings_widget", u"Description", None))
        self.use_gpu_checkbox.setText(QCoreApplication.translate("llm_settings_widget", u"Use GPU", None))
        self.override_parameters.setTitle(QCoreApplication.translate("llm_settings_widget", u"Override Prameters", None))
        self.early_stopping.setText(QCoreApplication.translate("llm_settings_widget", u"Early stopping", None))
        self.do_sample.setText(QCoreApplication.translate("llm_settings_widget", u"Do sample", None))
        self.cache_quantized_model_toggle.setText(QCoreApplication.translate("llm_settings_widget", u"Cache Quantized model to disk", None))
        self.groupBox_24.setTitle(QCoreApplication.translate("llm_settings_widget", u"Length penalty", None))
        self.length_penalty.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"llm_generator_settings.length_penalty", None))
        self.groupBox_25.setTitle(QCoreApplication.translate("llm_settings_widget", u"Num beams", None))
        self.num_beams.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"llm_generator_settings.num_beams", None))
        self.groupBox_17.setTitle(QCoreApplication.translate("llm_settings_widget", u"No repeat ngram size", None))
        self.ngram_size.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"llm_generator_settings.ngram_size", None))
        self.groupBox_18.setTitle(QCoreApplication.translate("llm_settings_widget", u"Temperature", None))
        self.temperature.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"llm_generator_settings.temperature", None))
        self.leave_in_vram.setText(QCoreApplication.translate("llm_settings_widget", u"Leave in VRAM", None))
        self.move_to_cpu.setText(QCoreApplication.translate("llm_settings_widget", u"Move to CPU", None))
        self.unload_model.setText(QCoreApplication.translate("llm_settings_widget", u"Unload model", None))
        self.groupBox_19.setTitle(QCoreApplication.translate("llm_settings_widget", u"Seed", None))
        self.random_seed.setText(QCoreApplication.translate("llm_settings_widget", u"Random seed", None))
        self.label_3.setText(QCoreApplication.translate("llm_settings_widget", u"Model management", None))
        self.label_4.setText(QCoreApplication.translate("llm_settings_widget", u"How to treat model when not in use", None))
        self.groupBox_11.setTitle(QCoreApplication.translate("llm_settings_widget", u"Repetition penalty", None))
        self.repetition_penalty.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"llm_generator_settings.repetition_penalty", None))
        self.groupBox_16.setTitle(QCoreApplication.translate("llm_settings_widget", u"Min length", None))
        self.min_length.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"llm_generator_settings.min_length", None))
        self.groupBox_22.setTitle(QCoreApplication.translate("llm_settings_widget", u"Sequences to generate", None))
        self.sequences.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"llm_generator_settings.sequences", None))
        self.groupBox_23.setTitle(QCoreApplication.translate("llm_settings_widget", u"Top k", None))
        self.top_k.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"llm_generator_settings.top_k", None))
        self.groupBox_20.setTitle(QCoreApplication.translate("llm_settings_widget", u"Top P", None))
        self.top_p.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"llm_generator_settings.top_p", None))
        self.groupBox_21.setTitle(QCoreApplication.translate("llm_settings_widget", u"Max length", None))
        self.max_length.setProperty("settings_property", QCoreApplication.translate("llm_settings_widget", u"llm_generator_settings.max_length", None))
        self.pushButton.setText(QCoreApplication.translate("llm_settings_widget", u"Reset Settings to Default", None))
        self.groupBox_7.setTitle(QCoreApplication.translate("llm_settings_widget", u"Model Type", None))
        self.groupBox_14.setTitle(QCoreApplication.translate("llm_settings_widget", u"Prompt Template", None))
        self.groupBox.setTitle(QCoreApplication.translate("llm_settings_widget", u"Tools", None))
        self.manual_tools.setText(QCoreApplication.translate("llm_settings_widget", u"Manual", None))
        self.automatic_tools.setText(QCoreApplication.translate("llm_settings_widget", u"Automatic", None))
        self.label.setText(QCoreApplication.translate("llm_settings_widget", u"LLMs can use a variety of tools. These settings define how the LLM will use those tools.", None))
    # retranslateUi

