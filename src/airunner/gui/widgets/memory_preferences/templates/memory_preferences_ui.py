# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'memory_preferences.ui'
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
    QGridLayout, QGroupBox, QLabel, QPushButton,
    QSizePolicy, QSpacerItem, QVBoxLayout, QWidget)

from airunner.gui.widgets.slider.slider_widget import SliderWidget

class Ui_memory_preferences(object):
    def setupUi(self, memory_preferences):
        if not memory_preferences.objectName():
            memory_preferences.setObjectName(u"memory_preferences")
        memory_preferences.resize(1007, 1050)
        self.gridLayout = QGridLayout(memory_preferences)
        self.gridLayout.setObjectName(u"gridLayout")
        self.line_7 = QFrame(memory_preferences)
        self.line_7.setObjectName(u"line_7")
        self.line_7.setFrameShape(QFrame.Shape.HLine)
        self.line_7.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line_7, 5, 0, 1, 5)

        self.line_2 = QFrame(memory_preferences)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line_2, 28, 0, 1, 5)

        self.line_8 = QFrame(memory_preferences)
        self.line_8.setObjectName(u"line_8")
        self.line_8.setFrameShape(QFrame.Shape.HLine)
        self.line_8.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line_8, 12, 0, 1, 5)

        self.line = QFrame(memory_preferences)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 25, 0, 1, 5)

        self.enable_model_cpu_offload = QCheckBox(memory_preferences)
        self.enable_model_cpu_offload.setObjectName(u"enable_model_cpu_offload")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.enable_model_cpu_offload.setFont(font)

        self.gridLayout.addWidget(self.enable_model_cpu_offload, 29, 0, 1, 3)

        self.use_enable_vae_slicing = QCheckBox(memory_preferences)
        self.use_enable_vae_slicing.setObjectName(u"use_enable_vae_slicing")
        self.use_enable_vae_slicing.setFont(font)

        self.gridLayout.addWidget(self.use_enable_vae_slicing, 35, 0, 1, 2)

        self.use_attention_slicing = QCheckBox(memory_preferences)
        self.use_attention_slicing.setObjectName(u"use_attention_slicing")
        self.use_attention_slicing.setFont(font)

        self.gridLayout.addWidget(self.use_attention_slicing, 14, 0, 2, 2)

        self.use_tiled_vae = QCheckBox(memory_preferences)
        self.use_tiled_vae.setObjectName(u"use_tiled_vae")
        self.use_tiled_vae.setFont(font)

        self.gridLayout.addWidget(self.use_tiled_vae, 38, 0, 1, 2)

        self.label_6 = QLabel(memory_preferences)
        self.label_6.setObjectName(u"label_6")
        font1 = QFont()
        font1.setPointSize(10)
        font1.setItalic(False)
        self.label_6.setFont(font1)
        self.label_6.setIndent(-1)

        self.gridLayout.addWidget(self.label_6, 36, 0, 1, 2)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.groupBox = QGroupBox(memory_preferences)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout_3 = QGridLayout(self.groupBox)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.sd_combobox = QComboBox(self.groupBox)
        self.sd_combobox.setObjectName(u"sd_combobox")

        self.gridLayout_3.addWidget(self.sd_combobox, 0, 0, 1, 1)


        self.verticalLayout.addWidget(self.groupBox)

        self.groupBox_4 = QGroupBox(memory_preferences)
        self.groupBox_4.setObjectName(u"groupBox_4")
        self.gridLayout_6 = QGridLayout(self.groupBox_4)
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.stt_combobox = QComboBox(self.groupBox_4)
        self.stt_combobox.setObjectName(u"stt_combobox")

        self.gridLayout_6.addWidget(self.stt_combobox, 0, 0, 1, 1)


        self.verticalLayout.addWidget(self.groupBox_4)

        self.groupBox_3 = QGroupBox(memory_preferences)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.gridLayout_5 = QGridLayout(self.groupBox_3)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.tts_combobox = QComboBox(self.groupBox_3)
        self.tts_combobox.setObjectName(u"tts_combobox")

        self.gridLayout_5.addWidget(self.tts_combobox, 0, 0, 1, 1)


        self.verticalLayout.addWidget(self.groupBox_3)

        self.groupBox_2 = QGroupBox(memory_preferences)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.gridLayout_4 = QGridLayout(self.groupBox_2)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.llm_combobox = QComboBox(self.groupBox_2)
        self.llm_combobox.setObjectName(u"llm_combobox")

        self.gridLayout_4.addWidget(self.llm_combobox, 0, 0, 1, 1)


        self.verticalLayout.addWidget(self.groupBox_2)


        self.gridLayout.addLayout(self.verticalLayout, 2, 0, 1, 5)

        self.label_11 = QLabel(memory_preferences)
        self.label_11.setObjectName(u"label_11")
        font2 = QFont()
        font2.setPointSize(12)
        font2.setBold(True)
        self.label_11.setFont(font2)

        self.gridLayout.addWidget(self.label_11, 1, 0, 1, 5)

        self.label_9 = QLabel(memory_preferences)
        self.label_9.setObjectName(u"label_9")
        font3 = QFont()
        font3.setPointSize(10)
        self.label_9.setFont(font3)

        self.gridLayout.addWidget(self.label_9, 10, 0, 1, 5)

        self.use_lastchannels = QCheckBox(memory_preferences)
        self.use_lastchannels.setObjectName(u"use_lastchannels")
        self.use_lastchannels.setFont(font)

        self.gridLayout.addWidget(self.use_lastchannels, 20, 0, 2, 4)

        self.use_tf32 = QCheckBox(memory_preferences)
        self.use_tf32.setObjectName(u"use_tf32")
        self.use_tf32.setFont(font)

        self.gridLayout.addWidget(self.use_tf32, 32, 0, 1, 2)

        self.label = QLabel(memory_preferences)
        self.label.setObjectName(u"label")
        self.label.setFont(font1)
        self.label.setIndent(-1)

        self.gridLayout.addWidget(self.label, 27, 0, 1, 5)

        self.label_2 = QLabel(memory_preferences)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setFont(font1)
        self.label_2.setIndent(-1)

        self.gridLayout.addWidget(self.label_2, 30, 0, 1, 5)

        self.use_accelerated_transformers = QCheckBox(memory_preferences)
        self.use_accelerated_transformers.setObjectName(u"use_accelerated_transformers")
        self.use_accelerated_transformers.setFont(font)

        self.gridLayout.addWidget(self.use_accelerated_transformers, 6, 0, 1, 5)

        self.line_9 = QFrame(memory_preferences)
        self.line_9.setObjectName(u"line_9")
        self.line_9.setFrameShape(QFrame.Shape.HLine)
        self.line_9.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line_9, 40, 0, 1, 5)

        self.label_7 = QLabel(memory_preferences)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setFont(font1)
        self.label_7.setIndent(-1)

        self.gridLayout.addWidget(self.label_7, 39, 0, 1, 2)

        self.line_4 = QFrame(memory_preferences)
        self.line_4.setObjectName(u"line_4")
        self.line_4.setFrameShape(QFrame.Shape.HLine)
        self.line_4.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line_4, 19, 0, 1, 5)

        self.prevent_unload_on_llm_image_generation = QCheckBox(memory_preferences)
        self.prevent_unload_on_llm_image_generation.setObjectName(u"prevent_unload_on_llm_image_generation")
        font4 = QFont()
        font4.setBold(True)
        self.prevent_unload_on_llm_image_generation.setFont(font4)

        self.gridLayout.addWidget(self.prevent_unload_on_llm_image_generation, 3, 0, 1, 1)

        self.use_enable_sequential_cpu_offload = QCheckBox(memory_preferences)
        self.use_enable_sequential_cpu_offload.setObjectName(u"use_enable_sequential_cpu_offload")
        self.use_enable_sequential_cpu_offload.setFont(font)

        self.gridLayout.addWidget(self.use_enable_sequential_cpu_offload, 26, 0, 1, 5)

        self.use_tome = QGroupBox(memory_preferences)
        self.use_tome.setObjectName(u"use_tome")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(75)
        sizePolicy.setHeightForWidth(self.use_tome.sizePolicy().hasHeightForWidth())
        self.use_tome.setSizePolicy(sizePolicy)
        self.use_tome.setCheckable(True)
        self.gridLayout_2 = QGridLayout(self.use_tome)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.tome_sd_ratio = SliderWidget(self.use_tome)
        self.tome_sd_ratio.setObjectName(u"tome_sd_ratio")
        self.tome_sd_ratio.setMinimumSize(QSize(0, 20))
        self.tome_sd_ratio.setProperty("slider_callback", u"tome_sd_ratio_value_change")
        self.tome_sd_ratio.setProperty("current_value", 1000)
        self.tome_sd_ratio.setProperty("slider_maximum", 1000)
        self.tome_sd_ratio.setProperty("spinbox_maximum", 1.000000000000000)
        self.tome_sd_ratio.setProperty("display_as_float", True)
        self.tome_sd_ratio.setProperty("spinbox_single_step", 0.010000000000000)
        self.tome_sd_ratio.setProperty("spinbox_page_step", 0.100000000000000)
        self.tome_sd_ratio.setProperty("spinbox_minimum", 0.000000000000000)
        self.tome_sd_ratio.setProperty("slider_minimum", 0)

        self.gridLayout_2.addWidget(self.tome_sd_ratio, 1, 0, 1, 1)

        self.label_10 = QLabel(self.use_tome)
        self.label_10.setObjectName(u"label_10")
        self.label_10.setFont(font3)

        self.gridLayout_2.addWidget(self.label_10, 0, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(624, 13, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer, 2, 0, 1, 1)


        self.gridLayout.addWidget(self.use_tome, 41, 0, 1, 5)

        self.label_8 = QLabel(memory_preferences)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setFont(font1)
        self.label_8.setIndent(-1)

        self.gridLayout.addWidget(self.label_8, 8, 0, 1, 5)

        self.label_4 = QLabel(memory_preferences)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setFont(font1)
        self.label_4.setIndent(-1)

        self.gridLayout.addWidget(self.label_4, 17, 0, 1, 5)

        self.label_3 = QLabel(memory_preferences)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setFont(font1)
        self.label_3.setIndent(-1)

        self.gridLayout.addWidget(self.label_3, 23, 0, 1, 5)

        self.line_5 = QFrame(memory_preferences)
        self.line_5.setObjectName(u"line_5")
        self.line_5.setFrameShape(QFrame.Shape.HLine)
        self.line_5.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line_5, 34, 0, 1, 5)

        self.label_5 = QLabel(memory_preferences)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setFont(font1)
        self.label_5.setIndent(-1)

        self.gridLayout.addWidget(self.label_5, 33, 0, 1, 5)

        self.line_3 = QFrame(memory_preferences)
        self.line_3.setObjectName(u"line_3")
        self.line_3.setFrameShape(QFrame.Shape.HLine)
        self.line_3.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line_3, 31, 0, 1, 5)

        self.line_6 = QFrame(memory_preferences)
        self.line_6.setObjectName(u"line_6")
        self.line_6.setFrameShape(QFrame.Shape.HLine)
        self.line_6.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line_6, 37, 0, 1, 5)

        self.optimize_memory_button = QPushButton(memory_preferences)
        self.optimize_memory_button.setObjectName(u"optimize_memory_button")

        self.gridLayout.addWidget(self.optimize_memory_button, 0, 0, 1, 5)

        self.label_12 = QLabel(memory_preferences)
        self.label_12.setObjectName(u"label_12")
        self.label_12.setFont(font3)

        self.gridLayout.addWidget(self.label_12, 4, 0, 1, 5)


        self.retranslateUi(memory_preferences)
        self.use_enable_vae_slicing.toggled.connect(memory_preferences.action_toggled_vae_slicing)
        self.use_tiled_vae.toggled.connect(memory_preferences.action_toggled_tile_vae)
        self.use_tf32.toggled.connect(memory_preferences.action_toggled_tf32)
        self.use_enable_sequential_cpu_offload.toggled.connect(memory_preferences.action_toggled_sequential_cpu_offload)
        self.use_accelerated_transformers.toggled.connect(memory_preferences.action_toggled_accelerated_transformers)
        self.optimize_memory_button.clicked.connect(memory_preferences.action_button_clicked_optimize_memory_settings)
        self.use_lastchannels.toggled.connect(memory_preferences.action_toggled_last_memory)
        self.use_attention_slicing.toggled.connect(memory_preferences.action_toggled_attention_slicing)
        self.enable_model_cpu_offload.toggled.connect(memory_preferences.action_toggled_model_cpu_offload)
        self.sd_combobox.currentTextChanged.connect(memory_preferences.action_changed_sd_combobox)
        self.llm_combobox.currentTextChanged.connect(memory_preferences.action_changed_llm_combobox)
        self.tts_combobox.currentTextChanged.connect(memory_preferences.action_changed_tts_combobox)
        self.stt_combobox.currentTextChanged.connect(memory_preferences.action_changed_stt_combobox)
        self.use_tome.toggled.connect(memory_preferences.action_toggled_tome)

        QMetaObject.connectSlotsByName(memory_preferences)
    # setupUi

    def retranslateUi(self, memory_preferences):
        memory_preferences.setWindowTitle(QCoreApplication.translate("memory_preferences", u"Form", None))
#if QT_CONFIG(tooltip)
        self.enable_model_cpu_offload.setToolTip(QCoreApplication.translate("memory_preferences", u"<html><head/><body><p><span style=\" font-weight:400;\">Use with attention slicing for lower memory consumption.</span></p><p><span style=\" font-weight:400;\">Moves whole models to the GPU, instead of handling each model\u2019s constituent </span><span style=\" font-weight:400; font-style:italic;\">modules</span><span style=\" font-weight:400;\">. This results in a negligible impact on inference time (compared with moving the pipeline to </span><span style=\" font-family:'monospace'; font-weight:400;\">cuda</span><span style=\" font-weight:400;\">), while still providing some memory savings.</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.enable_model_cpu_offload.setText(QCoreApplication.translate("memory_preferences", u"Model CPU offload", None))
#if QT_CONFIG(tooltip)
        self.use_enable_vae_slicing.setToolTip(QCoreApplication.translate("memory_preferences", u"<html><head/><body><p><span style=\" font-weight:400;\">Use with Attention Slicing or Xformers</span></p><p><span style=\" font-weight:400;\">Decode large batches of images with limited VRAM, or to enable batches with 32 images or more.</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.use_enable_vae_slicing.setText(QCoreApplication.translate("memory_preferences", u"Vae Slicing", None))
#if QT_CONFIG(tooltip)
        self.use_attention_slicing.setToolTip(QCoreApplication.translate("memory_preferences", u"<html><head/><body><p><span style=\" font-weight:400;\">Perform computation in steps instead of all at once.</span></p><p><span style=\" font-weight:400;\">About 10% slower inference times.</span></p><p><span style=\" font-weight:400;\">Uses as little as 3.2 GB of VRAM.</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.use_attention_slicing.setText(QCoreApplication.translate("memory_preferences", u"Attention Slicing", None))
#if QT_CONFIG(tooltip)
        self.use_tiled_vae.setToolTip(QCoreApplication.translate("memory_preferences", u"<html><head/><body><p><span style=\" font-weight:400;\">Use with Attention Slicing or Xformers</span></p><p><span style=\" font-weight:400;\">Makes it possible to work with large images on limited VRAM. Splits image into overlapping tiles, decodes tiles, blends outputs to make final image.</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.use_tiled_vae.setText(QCoreApplication.translate("memory_preferences", u"Tile vae", None))
        self.label_6.setText(QCoreApplication.translate("memory_preferences", u"Work with large batches", None))
        self.groupBox.setTitle(QCoreApplication.translate("memory_preferences", u"Art Model", None))
        self.groupBox_4.setTitle(QCoreApplication.translate("memory_preferences", u"Speech to text", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("memory_preferences", u"Text to speech", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("memory_preferences", u"Text Generator", None))
        self.label_11.setText(QCoreApplication.translate("memory_preferences", u"Assign models to available cards", None))
        self.label_9.setText(QCoreApplication.translate("memory_preferences", u"Keep this checked to take advantage of torch 2.0", None))
#if QT_CONFIG(tooltip)
        self.use_lastchannels.setToolTip(QCoreApplication.translate("memory_preferences", u"<html><head/><body><p><span style=\" font-weight:400;\">Alternative way of ordering NCHW tensors in memory preserving dimensions ordering. Channels last tensors ordered in such a way that channels become the densest dimension (aka storing images pixel-per-pixel). </span></p><p><span style=\" font-weight:400;\">Since not all operators currently support channels last format it may result in a worst performance, so it\u2019s better to try it and see if it works for your model.</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.use_lastchannels.setText(QCoreApplication.translate("memory_preferences", u"Channels last memory", None))
#if QT_CONFIG(tooltip)
        self.use_tf32.setToolTip(QCoreApplication.translate("memory_preferences", u"<html><head/><body><p><span style=\" font-weight:400;\">On Ampere and later CUDA devices matrix multiplications and convolutions can use the TensorFloat32 (TF32) mode for faster but slightly less accurate computations.</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.use_tf32.setText(QCoreApplication.translate("memory_preferences", u"TF32", None))
        self.label.setText(QCoreApplication.translate("memory_preferences", u"Less VRAM usage, slower inference", None))
        self.label_2.setText(QCoreApplication.translate("memory_preferences", u"Less VRAM usage, slight inference impact", None))
#if QT_CONFIG(tooltip)
        self.use_accelerated_transformers.setToolTip(QCoreApplication.translate("memory_preferences", u"<html><head/><body><p><span style=\" font-weight:400;\">Optimized and memory-efficient attention implementation.</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.use_accelerated_transformers.setText(QCoreApplication.translate("memory_preferences", u"Accelerated Transformers", None))
        self.label_7.setText(QCoreApplication.translate("memory_preferences", u"Work with large images", None))
        self.prevent_unload_on_llm_image_generation.setText(QCoreApplication.translate("memory_preferences", u"Disable automatic model management", None))
#if QT_CONFIG(tooltip)
        self.use_enable_sequential_cpu_offload.setToolTip(QCoreApplication.translate("memory_preferences", u"<html><head/><body><p><span style=\" font-weight:400;\">Use with </span>attention slicing<span style=\" font-weight:400;\"> for lower memory consumption.</span></p><p><span style=\" font-weight:400;\">Offloads the weights to CPU and only load them to GPU when performing the forward pass for memory savings.</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.use_enable_sequential_cpu_offload.setText(QCoreApplication.translate("memory_preferences", u"Sequential CPU offload", None))
#if QT_CONFIG(tooltip)
        self.use_tome.setToolTip(QCoreApplication.translate("memory_preferences", u"Merge redundant tokens for faster inference. May result in slight reduction in image quality.", None))
#endif // QT_CONFIG(tooltip)
        self.use_tome.setTitle(QCoreApplication.translate("memory_preferences", u"ToMe Token Merging", None))
        self.tome_sd_ratio.setProperty("label_text", QCoreApplication.translate("memory_preferences", u"Ratio", None))
        self.tome_sd_ratio.setProperty("settings_property", QCoreApplication.translate("memory_preferences", u"memory_settings.tome_sd_ratio", None))
        self.label_10.setText(QCoreApplication.translate("memory_preferences", u"Faster inference, slight image impact", None))
        self.label_8.setText(QCoreApplication.translate("memory_preferences", u"Faster inference, lower VRAM usage", None))
        self.label_4.setText(QCoreApplication.translate("memory_preferences", u"Less VRAM usage, slight inference impact", None))
        self.label_3.setText(QCoreApplication.translate("memory_preferences", u"May slow inference on some models, speed up on others", None))
        self.label_5.setText(QCoreApplication.translate("memory_preferences", u"faster matrix multiplications on ampere achitecture", None))
        self.optimize_memory_button.setText(QCoreApplication.translate("memory_preferences", u"Optimize Memory Settings", None))
        self.label_12.setText(QCoreApplication.translate("memory_preferences", u"Models will auto load / unload when generating images with the chatbot.", None))
    # retranslateUi

