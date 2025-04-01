# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'flan_generator_form.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGridLayout,
    QGroupBox, QHBoxLayout, QLineEdit, QSizePolicy,
    QWidget)

from airunner.gui.widgets.slider.slider_widget import SliderWidget

class Ui_flan_generator_form(object):
    def setupUi(self, flan_generator_form):
        if not flan_generator_form.objectName():
            flan_generator_form.setObjectName(u"flan_generator_form")
        flan_generator_form.resize(400, 631)
        self.gridLayout = QGridLayout(flan_generator_form)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.groupBox = QGroupBox(flan_generator_form)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout_2 = QGridLayout(self.groupBox)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.top_p = SliderWidget(self.groupBox)
        self.top_p.setObjectName(u"top_p")
        self.top_p.setProperty("min_slider", 1)
        self.top_p.setProperty("max_slider", 100)
        self.top_p.setProperty("min_spinbox", 0.000000000000000)
        self.top_p.setProperty("max_spinbox", 1.000000000000000)
        self.top_p.setProperty("display_as_float", True)
        self.top_p.setProperty("slider_step", 1)
        self.top_p.setProperty("slider_page", 10)
        self.top_p.setProperty("spinbox_step", 0.010000000000000)
        self.top_p.setProperty("spinbox_page", 0.100000000000000)

        self.gridLayout_2.addWidget(self.top_p, 0, 0, 1, 1)


        self.horizontalLayout_2.addWidget(self.groupBox)

        self.groupBox_2 = QGroupBox(flan_generator_form)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.gridLayout_3 = QGridLayout(self.groupBox_2)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.max_length = SliderWidget(self.groupBox_2)
        self.max_length.setObjectName(u"max_length")
        self.max_length.setProperty("min_slider", 1)
        self.max_length.setProperty("max_slider", 2556)
        self.max_length.setProperty("min_spinbox", 1.000000000000000)
        self.max_length.setProperty("max_spinbox", 2556.000000000000000)
        self.max_length.setProperty("display_as_float", False)
        self.max_length.setProperty("slider_step", 1)
        self.max_length.setProperty("slider_page", 2556)
        self.max_length.setProperty("spinbox_step", 1)
        self.max_length.setProperty("spinbox_page", 2556)

        self.gridLayout_3.addWidget(self.max_length, 0, 0, 1, 1)


        self.horizontalLayout_2.addWidget(self.groupBox_2)


        self.gridLayout.addLayout(self.horizontalLayout_2, 1, 0, 1, 1)

        self.random_seed = QCheckBox(flan_generator_form)
        self.random_seed.setObjectName(u"random_seed")

        self.gridLayout.addWidget(self.random_seed, 10, 0, 1, 1)

        self.groupBox_11 = QGroupBox(flan_generator_form)
        self.groupBox_11.setObjectName(u"groupBox_11")
        self.gridLayout_4 = QGridLayout(self.groupBox_11)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.seed = QLineEdit(self.groupBox_11)
        self.seed.setObjectName(u"seed")

        self.gridLayout_4.addWidget(self.seed, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_11, 9, 0, 1, 1)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.groupBox_5 = QGroupBox(flan_generator_form)
        self.groupBox_5.setObjectName(u"groupBox_5")
        self.gridLayout_7 = QGridLayout(self.groupBox_5)
        self.gridLayout_7.setObjectName(u"gridLayout_7")
        self.length_penalty = SliderWidget(self.groupBox_5)
        self.length_penalty.setObjectName(u"length_penalty")
        self.length_penalty.setProperty("min_slider", 0)
        self.length_penalty.setProperty("max_slider", 200)
        self.length_penalty.setProperty("min_spinbox", 0.000000000000000)
        self.length_penalty.setProperty("max_spinbox", 2.000000000000000)
        self.length_penalty.setProperty("display_as_float", True)
        self.length_penalty.setProperty("slider_step", 1)
        self.length_penalty.setProperty("slider_page", 10)
        self.length_penalty.setProperty("spinbox_step", 0.010000000000000)
        self.length_penalty.setProperty("spinbox_page", 0.100000000000000)

        self.gridLayout_7.addWidget(self.length_penalty, 0, 0, 1, 1)


        self.horizontalLayout_4.addWidget(self.groupBox_5)

        self.groupBox_6 = QGroupBox(flan_generator_form)
        self.groupBox_6.setObjectName(u"groupBox_6")
        self.gridLayout_8 = QGridLayout(self.groupBox_6)
        self.gridLayout_8.setObjectName(u"gridLayout_8")
        self.num_beams = SliderWidget(self.groupBox_6)
        self.num_beams.setObjectName(u"num_beams")
        self.num_beams.setProperty("min_slider", 1)
        self.num_beams.setProperty("max_slider", 100)
        self.num_beams.setProperty("min_spinbox", 0.000000000000000)
        self.num_beams.setProperty("max_spinbox", 100.000000000000000)
        self.num_beams.setProperty("display_as_float", False)
        self.num_beams.setProperty("slider_step", 1)
        self.num_beams.setProperty("slider_page", 10)
        self.num_beams.setProperty("spinbox_step", 0.010000000000000)
        self.num_beams.setProperty("spinbox_page", 0.100000000000000)

        self.gridLayout_8.addWidget(self.num_beams, 0, 0, 1, 1)


        self.horizontalLayout_4.addWidget(self.groupBox_6)


        self.gridLayout.addLayout(self.horizontalLayout_4, 3, 0, 1, 1)

        self.do_sample = QCheckBox(flan_generator_form)
        self.do_sample.setObjectName(u"do_sample")

        self.gridLayout.addWidget(self.do_sample, 7, 0, 1, 1)

        self.model_version = QComboBox(flan_generator_form)
        self.model_version.setObjectName(u"model_version")

        self.gridLayout.addWidget(self.model_version, 0, 0, 1, 1)

        self.early_stopping = QCheckBox(flan_generator_form)
        self.early_stopping.setObjectName(u"early_stopping")

        self.gridLayout.addWidget(self.early_stopping, 8, 0, 1, 1)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.groupBox_3 = QGroupBox(flan_generator_form)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.gridLayout_5 = QGridLayout(self.groupBox_3)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.repetition_penalty = SliderWidget(self.groupBox_3)
        self.repetition_penalty.setObjectName(u"repetition_penalty")
        self.repetition_penalty.setProperty("min_slider", 0)
        self.repetition_penalty.setProperty("max_slider", 10000)
        self.repetition_penalty.setProperty("min_spinbox", 0.000000000000000)
        self.repetition_penalty.setProperty("max_spinbox", 100.000000000000000)
        self.repetition_penalty.setProperty("display_as_float", True)
        self.repetition_penalty.setProperty("slider_step", 0)
        self.repetition_penalty.setProperty("slider_page", 1)
        self.repetition_penalty.setProperty("spinbox_step", 1.000000000000000)
        self.repetition_penalty.setProperty("spinbox_page", 10.000000000000000)

        self.gridLayout_5.addWidget(self.repetition_penalty, 0, 0, 1, 1)


        self.horizontalLayout_3.addWidget(self.groupBox_3)

        self.groupBox_4 = QGroupBox(flan_generator_form)
        self.groupBox_4.setObjectName(u"groupBox_4")
        self.gridLayout_6 = QGridLayout(self.groupBox_4)
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.min_length = SliderWidget(self.groupBox_4)
        self.min_length.setObjectName(u"min_length")
        self.min_length.setProperty("min_slider", 1)
        self.min_length.setProperty("max_slider", 2556)
        self.min_length.setProperty("min_spinbox", 1.000000000000000)
        self.min_length.setProperty("max_spinbox", 2556.000000000000000)
        self.min_length.setProperty("display_as_float", False)
        self.min_length.setProperty("slider_step", 1)
        self.min_length.setProperty("slider_page", 2556)
        self.min_length.setProperty("spinbox_step", 1)
        self.min_length.setProperty("spinbox_page", 2556)

        self.gridLayout_6.addWidget(self.min_length, 0, 0, 1, 1)


        self.horizontalLayout_3.addWidget(self.groupBox_4)


        self.gridLayout.addLayout(self.horizontalLayout_3, 2, 0, 1, 1)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.groupBox_7 = QGroupBox(flan_generator_form)
        self.groupBox_7.setObjectName(u"groupBox_7")
        self.gridLayout_9 = QGridLayout(self.groupBox_7)
        self.gridLayout_9.setObjectName(u"gridLayout_9")
        self.ngram_size = SliderWidget(self.groupBox_7)
        self.ngram_size.setObjectName(u"ngram_size")
        self.ngram_size.setProperty("min_slider", 1)
        self.ngram_size.setProperty("max_slider", 100)
        self.ngram_size.setProperty("min_spinbox", 0.000000000000000)
        self.ngram_size.setProperty("max_spinbox", 1.000000000000000)
        self.ngram_size.setProperty("display_as_float", True)
        self.ngram_size.setProperty("slider_step", 1)
        self.ngram_size.setProperty("slider_page", 10)
        self.ngram_size.setProperty("spinbox_step", 0.010000000000000)
        self.ngram_size.setProperty("spinbox_page", 0.100000000000000)

        self.gridLayout_9.addWidget(self.ngram_size, 0, 0, 1, 1)


        self.horizontalLayout_5.addWidget(self.groupBox_7)

        self.groupBox_8 = QGroupBox(flan_generator_form)
        self.groupBox_8.setObjectName(u"groupBox_8")
        self.gridLayout_10 = QGridLayout(self.groupBox_8)
        self.gridLayout_10.setObjectName(u"gridLayout_10")
        self.temperature = SliderWidget(self.groupBox_8)
        self.temperature.setObjectName(u"temperature")
        self.temperature.setProperty("min_slider", 1)
        self.temperature.setProperty("max_slider", 200)
        self.temperature.setProperty("min_spinbox", 0.000000000000000)
        self.temperature.setProperty("max_spinbox", 2.000000000000000)
        self.temperature.setProperty("display_as_float", True)
        self.temperature.setProperty("slider_step", 1)
        self.temperature.setProperty("slider_page", 10)
        self.temperature.setProperty("spinbox_step", 0.010000000000000)
        self.temperature.setProperty("spinbox_page", 0.100000000000000)

        self.gridLayout_10.addWidget(self.temperature, 0, 0, 1, 1)


        self.horizontalLayout_5.addWidget(self.groupBox_8)


        self.gridLayout.addLayout(self.horizontalLayout_5, 4, 0, 1, 1)

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.groupBox_9 = QGroupBox(flan_generator_form)
        self.groupBox_9.setObjectName(u"groupBox_9")
        self.gridLayout_11 = QGridLayout(self.groupBox_9)
        self.gridLayout_11.setObjectName(u"gridLayout_11")
        self.sequences = SliderWidget(self.groupBox_9)
        self.sequences.setObjectName(u"sequences")
        self.sequences.setProperty("min_slider", 1)
        self.sequences.setProperty("max_slider", 100)
        self.sequences.setProperty("min_spinbox", 0.000000000000000)
        self.sequences.setProperty("max_spinbox", 100.000000000000000)
        self.sequences.setProperty("display_as_float", False)
        self.sequences.setProperty("slider_step", 1)
        self.sequences.setProperty("slider_page", 10)
        self.sequences.setProperty("spinbox_step", 0.010000000000000)
        self.sequences.setProperty("spinbox_page", 0.100000000000000)

        self.gridLayout_11.addWidget(self.sequences, 0, 0, 1, 1)


        self.horizontalLayout_6.addWidget(self.groupBox_9)

        self.groupBox_10 = QGroupBox(flan_generator_form)
        self.groupBox_10.setObjectName(u"groupBox_10")
        self.gridLayout_12 = QGridLayout(self.groupBox_10)
        self.gridLayout_12.setObjectName(u"gridLayout_12")
        self.top_k = SliderWidget(self.groupBox_10)
        self.top_k.setObjectName(u"top_k")
        self.top_k.setProperty("min_slider", 1)
        self.top_k.setProperty("max_slider", 256)
        self.top_k.setProperty("min_spinbox", 0.000000000000000)
        self.top_k.setProperty("max_spinbox", 256.000000000000000)
        self.top_k.setProperty("display_as_float", False)
        self.top_k.setProperty("slider_step", 1)
        self.top_k.setProperty("slider_page", 10)
        self.top_k.setProperty("spinbox_step", 1)
        self.top_k.setProperty("spinbox_page", 10)

        self.gridLayout_12.addWidget(self.top_k, 0, 0, 1, 1)


        self.horizontalLayout_6.addWidget(self.groupBox_10)


        self.gridLayout.addLayout(self.horizontalLayout_6, 5, 0, 1, 1)

        self.groupBox_12 = QGroupBox(flan_generator_form)
        self.groupBox_12.setObjectName(u"groupBox_12")
        self.gridLayout_13 = QGridLayout(self.groupBox_12)
        self.gridLayout_13.setObjectName(u"gridLayout_13")
        self.eta_cutoff = SliderWidget(self.groupBox_12)
        self.eta_cutoff.setObjectName(u"eta_cutoff")
        self.eta_cutoff.setProperty("min_slider", 1)
        self.eta_cutoff.setProperty("max_slider", 100)
        self.eta_cutoff.setProperty("min_spinbox", 0.000000000000000)
        self.eta_cutoff.setProperty("max_spinbox", 100.000000000000000)
        self.eta_cutoff.setProperty("display_as_float", True)
        self.eta_cutoff.setProperty("slider_step", 1)
        self.eta_cutoff.setProperty("slider_page", 10)
        self.eta_cutoff.setProperty("spinbox_step", 0.010000000000000)
        self.eta_cutoff.setProperty("spinbox_page", 0.100000000000000)

        self.gridLayout_13.addWidget(self.eta_cutoff, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_12, 6, 0, 1, 1)


        self.retranslateUi(flan_generator_form)
        self.do_sample.toggled.connect(flan_generator_form.do_sample_toggled)
        self.early_stopping.toggled.connect(flan_generator_form.early_stopping_toggled)
        self.random_seed.toggled.connect(flan_generator_form.random_seed_toggled)
        self.seed.textEdited.connect(flan_generator_form.seed_changed)
        self.model_version.currentTextChanged.connect(flan_generator_form.model_changed)

        self.model_version.setCurrentIndex(-1)


        QMetaObject.connectSlotsByName(flan_generator_form)
    # setupUi

    def retranslateUi(self, flan_generator_form):
        flan_generator_form.setWindowTitle(QCoreApplication.translate("flan_generator_form", u"Form", None))
        self.groupBox.setTitle(QCoreApplication.translate("flan_generator_form", u"Top P", None))
        self.top_p.setProperty("property", QCoreApplication.translate("flan_generator_form", u"top_p", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("flan_generator_form", u"Max length", None))
        self.max_length.setProperty("property", QCoreApplication.translate("flan_generator_form", u"max_length", None))
        self.random_seed.setText(QCoreApplication.translate("flan_generator_form", u"Random seed", None))
        self.groupBox_11.setTitle(QCoreApplication.translate("flan_generator_form", u"Seed", None))
        self.groupBox_5.setTitle(QCoreApplication.translate("flan_generator_form", u"Length penalty", None))
        self.length_penalty.setProperty("property", QCoreApplication.translate("flan_generator_form", u"length_penalty", None))
        self.groupBox_6.setTitle(QCoreApplication.translate("flan_generator_form", u"Num beams", None))
        self.num_beams.setProperty("property", QCoreApplication.translate("flan_generator_form", u"num_beams", None))
        self.do_sample.setText(QCoreApplication.translate("flan_generator_form", u"Do sample", None))
        self.early_stopping.setText(QCoreApplication.translate("flan_generator_form", u"Early stopping", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("flan_generator_form", u"Repetition penalty", None))
        self.repetition_penalty.setProperty("property", QCoreApplication.translate("flan_generator_form", u"repetition_penalty", None))
        self.groupBox_4.setTitle(QCoreApplication.translate("flan_generator_form", u"Min length", None))
        self.min_length.setProperty("property", QCoreApplication.translate("flan_generator_form", u"min_length", None))
        self.groupBox_7.setTitle(QCoreApplication.translate("flan_generator_form", u"No repeat ngram size", None))
        self.ngram_size.setProperty("property", QCoreApplication.translate("flan_generator_form", u"ngram", None))
        self.groupBox_8.setTitle(QCoreApplication.translate("flan_generator_form", u"Temperature", None))
        self.temperature.setProperty("property", QCoreApplication.translate("flan_generator_form", u"temperature", None))
        self.groupBox_9.setTitle(QCoreApplication.translate("flan_generator_form", u"Sequences to generate", None))
        self.sequences.setProperty("property", QCoreApplication.translate("flan_generator_form", u"sequences", None))
        self.groupBox_10.setTitle(QCoreApplication.translate("flan_generator_form", u"Top k", None))
        self.top_k.setProperty("property", QCoreApplication.translate("flan_generator_form", u"top_k", None))
        self.groupBox_12.setTitle(QCoreApplication.translate("flan_generator_form", u"ETA Cutoff", None))
        self.eta_cutoff.setProperty("property", QCoreApplication.translate("flan_generator_form", u"eta_cutoff", None))
    # retranslateUi

