# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'stablediffusion_generator_form.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
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
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QPlainTextEdit, QProgressBar, QPushButton,
    QScrollArea, QSizePolicy, QSpacerItem, QSplitter,
    QVBoxLayout, QWidget)

from airunner.components.application.gui.widgets.slider.slider_widget import SliderWidget
import airunner.feather_rc

class Ui_stablediffusion_generator_form(object):
    def setupUi(self, stablediffusion_generator_form):
        if not stablediffusion_generator_form.objectName():
            stablediffusion_generator_form.setObjectName(u"stablediffusion_generator_form")
        stablediffusion_generator_form.resize(568, 825)
        font = QFont()
        font.setPointSize(8)
        stablediffusion_generator_form.setFont(font)
        stablediffusion_generator_form.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.gridLayout_4 = QGridLayout(stablediffusion_generator_form)
        self.gridLayout_4.setSpacing(0)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.gridLayout_4.setContentsMargins(0, 0, 0, 0)
        self.generator_form_tabs = QWidget(stablediffusion_generator_form)
        self.generator_form_tabs.setObjectName(u"generator_form_tabs")
        self.gridLayout_3 = QGridLayout(self.generator_form_tabs)
        self.gridLayout_3.setSpacing(0)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.stable_diffusion_generator_form = QScrollArea(self.generator_form_tabs)
        self.stable_diffusion_generator_form.setObjectName(u"stable_diffusion_generator_form")
        self.stable_diffusion_generator_form.setFrameShape(QFrame.Shape.NoFrame)
        self.stable_diffusion_generator_form.setFrameShadow(QFrame.Shadow.Plain)
        self.stable_diffusion_generator_form.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 568, 775))
        self.gridLayout = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(0)
        self.gridLayout.setVerticalSpacing(10)
        self.gridLayout.setContentsMargins(10, 0, 10, 0)
        self.sdxl_settings_container = QWidget(self.scrollAreaWidgetContents)
        self.sdxl_settings_container.setObjectName(u"sdxl_settings_container")
        self.sdxl_settings = QVBoxLayout(self.sdxl_settings_container)
        self.sdxl_settings.setObjectName(u"sdxl_settings")
        self.sdxl_settings.setContentsMargins(0, 0, 0, 0)
        self.n_samples = SliderWidget(self.sdxl_settings_container)
        self.n_samples.setObjectName(u"n_samples")
        self.n_samples.setProperty(u"current_value", 1)
        self.n_samples.setProperty(u"slider_maximum", 1000)
        self.n_samples.setProperty(u"spinbox_maximum", 1000)
        self.n_samples.setProperty(u"display_as_float", False)
        self.n_samples.setProperty(u"spinbox_single_step", 1)
        self.n_samples.setProperty(u"spinbox_page_step", 1)
        self.n_samples.setProperty(u"spinbox_minimum", 1)
        self.n_samples.setProperty(u"slider_minimum", 1)

        self.sdxl_settings.addWidget(self.n_samples)

        self.horizontalLayout_14 = QHBoxLayout()
        self.horizontalLayout_14.setObjectName(u"horizontalLayout_14")
        self.images_per_batch = SliderWidget(self.sdxl_settings_container)
        self.images_per_batch.setObjectName(u"images_per_batch")
        self.images_per_batch.setProperty(u"current_value", 1)
        self.images_per_batch.setProperty(u"slider_maximum", 6)
        self.images_per_batch.setProperty(u"spinbox_maximum", 6)
        self.images_per_batch.setProperty(u"display_as_float", False)
        self.images_per_batch.setProperty(u"spinbox_single_step", 1)
        self.images_per_batch.setProperty(u"spinbox_page_step", 1)
        self.images_per_batch.setProperty(u"spinbox_minimum", 1)
        self.images_per_batch.setProperty(u"slider_minimum", 1)

        self.horizontalLayout_14.addWidget(self.images_per_batch)

        self.infinite_images_button = QPushButton(self.sdxl_settings_container)
        self.infinite_images_button.setObjectName(u"infinite_images_button")
        self.infinite_images_button.setMinimumSize(QSize(30, 30))
        self.infinite_images_button.setMaximumSize(QSize(30, 30))
        icon = QIcon()
        icon.addFile(u":/light/icons/feather/light/circle.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.infinite_images_button.setIcon(icon)
        self.infinite_images_button.setCheckable(True)
        self.infinite_images_button.setChecked(False)

        self.horizontalLayout_14.addWidget(self.infinite_images_button)


        self.sdxl_settings.addLayout(self.horizontalLayout_14)


        self.gridLayout.addWidget(self.sdxl_settings_container, 2, 0, 1, 1)

        self.generator_form_splitter = QSplitter(self.scrollAreaWidgetContents)
        self.generator_form_splitter.setObjectName(u"generator_form_splitter")
        self.generator_form_splitter.setOrientation(Qt.Orientation.Vertical)
        self.generator_form_splitter.setChildrenCollapsible(False)
        self.layoutWidget = QWidget(self.generator_form_splitter)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.prompt_container_layout = QGridLayout(self.layoutWidget)
        self.prompt_container_layout.setObjectName(u"prompt_container_layout")
        self.prompt_container_layout.setContentsMargins(0, 0, 0, 9)
        self.add_prompt_button = QPushButton(self.layoutWidget)
        self.add_prompt_button.setObjectName(u"add_prompt_button")

        self.prompt_container_layout.addWidget(self.add_prompt_button, 3, 0, 1, 1)

        self.additional_prompts_container_layout = QVBoxLayout()
        self.additional_prompts_container_layout.setObjectName(u"additional_prompts_container_layout")

        self.prompt_container_layout.addLayout(self.additional_prompts_container_layout, 2, 0, 1, 2)

        self.label = QLabel(self.layoutWidget)
        self.label.setObjectName(u"label")
        font1 = QFont()
        font1.setPointSize(8)
        font1.setBold(True)
        self.label.setFont(font1)

        self.prompt_container_layout.addWidget(self.label, 0, 0, 1, 1)

        self.prompt_container = QHBoxLayout()
        self.prompt_container.setObjectName(u"prompt_container")
        self.prompt = QPlainTextEdit(self.layoutWidget)
        self.prompt.setObjectName(u"prompt")

        self.prompt_container.addWidget(self.prompt)

        self.secondary_prompt = QPlainTextEdit(self.layoutWidget)
        self.secondary_prompt.setObjectName(u"secondary_prompt")

        self.prompt_container.addWidget(self.secondary_prompt)


        self.prompt_container_layout.addLayout(self.prompt_container, 1, 0, 1, 2)

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.horizontalLayout_6.setContentsMargins(-1, 10, -1, -1)
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_6.addItem(self.horizontalSpacer)

        self.save_prompts_button = QPushButton(self.layoutWidget)
        self.save_prompts_button.setObjectName(u"save_prompts_button")

        self.horizontalLayout_6.addWidget(self.save_prompts_button)


        self.prompt_container_layout.addLayout(self.horizontalLayout_6, 0, 1, 1, 1)

        self.generator_form_splitter.addWidget(self.layoutWidget)
        self.layoutWidget1 = QWidget(self.generator_form_splitter)
        self.layoutWidget1.setObjectName(u"layoutWidget1")
        self.negative_prompt_container = QVBoxLayout(self.layoutWidget1)
        self.negative_prompt_container.setObjectName(u"negative_prompt_container")
        self.negative_prompt_container.setContentsMargins(0, 5, 0, 0)
        self.negative_prompt_label = QLabel(self.layoutWidget1)
        self.negative_prompt_label.setObjectName(u"negative_prompt_label")
        self.negative_prompt_label.setFont(font1)

        self.negative_prompt_container.addWidget(self.negative_prompt_label)

        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.negative_prompt = QPlainTextEdit(self.layoutWidget1)
        self.negative_prompt.setObjectName(u"negative_prompt")

        self.horizontalLayout_8.addWidget(self.negative_prompt)

        self.secondary_negative_prompt = QPlainTextEdit(self.layoutWidget1)
        self.secondary_negative_prompt.setObjectName(u"secondary_negative_prompt")

        self.horizontalLayout_8.addWidget(self.secondary_negative_prompt)


        self.negative_prompt_container.addLayout(self.horizontalLayout_8)

        self.generator_form_splitter.addWidget(self.layoutWidget1)

        self.gridLayout.addWidget(self.generator_form_splitter, 0, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.enable_torch_compile = QPushButton(self.scrollAreaWidgetContents)
        self.enable_torch_compile.setObjectName(u"enable_torch_compile")
        self.enable_torch_compile.setMinimumSize(QSize(30, 30))
        self.enable_torch_compile.setMaximumSize(QSize(30, 30))
        icon1 = QIcon()
        icon1.addFile(u":/dark/icons/feather/dark/box.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.enable_torch_compile.setIcon(icon1)
        self.enable_torch_compile.setCheckable(True)

        self.horizontalLayout.addWidget(self.enable_torch_compile)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)


        self.gridLayout.addLayout(self.horizontalLayout, 1, 0, 1, 1)

        self.stable_diffusion_generator_form.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_3.addWidget(self.stable_diffusion_generator_form, 0, 0, 1, 1)

        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.horizontalLayout_7.setContentsMargins(10, 10, 10, 10)
        self.progress_bar = QProgressBar(self.generator_form_tabs)
        self.progress_bar.setObjectName(u"progress_bar")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.progress_bar.sizePolicy().hasHeightForWidth())
        self.progress_bar.setSizePolicy(sizePolicy)
        self.progress_bar.setMinimumSize(QSize(0, 30))
        self.progress_bar.setValue(0)

        self.horizontalLayout_7.addWidget(self.progress_bar)

        self.generate_button = QPushButton(self.generator_form_tabs)
        self.generate_button.setObjectName(u"generate_button")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.generate_button.sizePolicy().hasHeightForWidth())
        self.generate_button.setSizePolicy(sizePolicy1)
        self.generate_button.setMinimumSize(QSize(30, 30))
        self.generate_button.setMaximumSize(QSize(30, 30))
        icon2 = QIcon()
        icon2.addFile(u":/light/icons/feather/light/chevron-up.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.generate_button.setIcon(icon2)

        self.horizontalLayout_7.addWidget(self.generate_button)

        self.interrupt_button = QPushButton(self.generator_form_tabs)
        self.interrupt_button.setObjectName(u"interrupt_button")
        sizePolicy1.setHeightForWidth(self.interrupt_button.sizePolicy().hasHeightForWidth())
        self.interrupt_button.setSizePolicy(sizePolicy1)
        self.interrupt_button.setMinimumSize(QSize(30, 30))
        self.interrupt_button.setMaximumSize(QSize(30, 30))
        self.interrupt_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon3 = QIcon()
        icon3.addFile(u":/light/icons/feather/light/x.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.interrupt_button.setIcon(icon3)

        self.horizontalLayout_7.addWidget(self.interrupt_button)


        self.gridLayout_3.addLayout(self.horizontalLayout_7, 1, 0, 1, 1)


        self.gridLayout_4.addWidget(self.generator_form_tabs, 0, 0, 1, 1)

        QWidget.setTabOrder(self.prompt, self.secondary_prompt)
        QWidget.setTabOrder(self.secondary_prompt, self.add_prompt_button)
        QWidget.setTabOrder(self.add_prompt_button, self.negative_prompt)
        QWidget.setTabOrder(self.negative_prompt, self.secondary_negative_prompt)
        QWidget.setTabOrder(self.secondary_negative_prompt, self.generate_button)
        QWidget.setTabOrder(self.generate_button, self.interrupt_button)
        QWidget.setTabOrder(self.interrupt_button, self.save_prompts_button)
        QWidget.setTabOrder(self.save_prompts_button, self.stable_diffusion_generator_form)

        self.retranslateUi(stablediffusion_generator_form)

        QMetaObject.connectSlotsByName(stablediffusion_generator_form)
    # setupUi

    def retranslateUi(self, stablediffusion_generator_form):
        stablediffusion_generator_form.setWindowTitle(QCoreApplication.translate("stablediffusion_generator_form", u"Form", None))
        self.n_samples.setProperty(u"label_text", QCoreApplication.translate("stablediffusion_generator_form", u"Batches", None))
        self.n_samples.setProperty(u"settings_property", QCoreApplication.translate("stablediffusion_generator_form", u"generator_settings.n_samples", None))
        self.images_per_batch.setProperty(u"label_text", QCoreApplication.translate("stablediffusion_generator_form", u"Images Per Batch", None))
        self.images_per_batch.setProperty(u"settings_property", QCoreApplication.translate("stablediffusion_generator_form", u"generator_settings.images_per_batch", None))
#if QT_CONFIG(tooltip)
        self.infinite_images_button.setToolTip(QCoreApplication.translate("stablediffusion_generator_form", u"Toggle infinite image generation", None))
#endif // QT_CONFIG(tooltip)
        self.infinite_images_button.setText("")
        self.add_prompt_button.setText(QCoreApplication.translate("stablediffusion_generator_form", u"Add Prompt", None))
        self.label.setText(QCoreApplication.translate("stablediffusion_generator_form", u"Prompt", None))
        self.prompt.setPlaceholderText(QCoreApplication.translate("stablediffusion_generator_form", u"Prompt", None))
        self.secondary_prompt.setPlaceholderText(QCoreApplication.translate("stablediffusion_generator_form", u"Second prompt", None))
        self.save_prompts_button.setText(QCoreApplication.translate("stablediffusion_generator_form", u"Save Prompts", None))
        self.negative_prompt_label.setText(QCoreApplication.translate("stablediffusion_generator_form", u"Negative Prompt", None))
        self.negative_prompt.setPlaceholderText(QCoreApplication.translate("stablediffusion_generator_form", u"Negative prompt", None))
        self.secondary_negative_prompt.setPlaceholderText(QCoreApplication.translate("stablediffusion_generator_form", u"Second negative prompt", None))
#if QT_CONFIG(tooltip)
        self.enable_torch_compile.setToolTip(QCoreApplication.translate("stablediffusion_generator_form", u"Use torch compile (slow first generation, fast subsequent)", None))
#endif // QT_CONFIG(tooltip)
        self.enable_torch_compile.setText("")
#if QT_CONFIG(tooltip)
        self.generate_button.setToolTip(QCoreApplication.translate("stablediffusion_generator_form", u"Generate image", None))
#endif // QT_CONFIG(tooltip)
        self.generate_button.setText("")
#if QT_CONFIG(tooltip)
        self.interrupt_button.setToolTip(QCoreApplication.translate("stablediffusion_generator_form", u"Cancel image generation", None))
#endif // QT_CONFIG(tooltip)
        self.interrupt_button.setText("")
    # retranslateUi

