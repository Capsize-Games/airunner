# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'stablediffusion_generator_form.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (
    QCoreApplication,
    QDate,
    QDateTime,
    QLocale,
    QMetaObject,
    QObject,
    QPoint,
    QRect,
    QSize,
    QTime,
    QUrl,
    Qt,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QCursor,
    QFont,
    QFontDatabase,
    QGradient,
    QIcon,
    QImage,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPalette,
    QPixmap,
    QRadialGradient,
    QTransform,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from airunner.gui.widgets.slider.slider_widget import SliderWidget
import airunner.feather_rc


class Ui_stablediffusion_generator_form(object):
    def setupUi(self, stablediffusion_generator_form):
        if not stablediffusion_generator_form.objectName():
            stablediffusion_generator_form.setObjectName(
                "stablediffusion_generator_form"
            )
        stablediffusion_generator_form.resize(597, 825)
        font = QFont()
        font.setPointSize(8)
        stablediffusion_generator_form.setFont(font)
        stablediffusion_generator_form.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.gridLayout_4 = QGridLayout(stablediffusion_generator_form)
        self.gridLayout_4.setSpacing(0)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.gridLayout_4.setContentsMargins(0, 0, 0, 0)
        self.generator_form_tabs = QWidget(stablediffusion_generator_form)
        self.generator_form_tabs.setObjectName("generator_form_tabs")
        self.gridLayout_3 = QGridLayout(self.generator_form_tabs)
        self.gridLayout_3.setSpacing(0)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.stable_diffusion_generator_form = QScrollArea(self.generator_form_tabs)
        self.stable_diffusion_generator_form.setObjectName(
            "stable_diffusion_generator_form"
        )
        self.stable_diffusion_generator_form.setFrameShape(QFrame.Shape.NoFrame)
        self.stable_diffusion_generator_form.setFrameShadow(QFrame.Shadow.Plain)
        self.stable_diffusion_generator_form.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 597, 775))
        self.gridLayout = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout.setObjectName("gridLayout")
        self.gridLayout.setHorizontalSpacing(0)
        self.gridLayout.setVerticalSpacing(10)
        self.gridLayout.setContentsMargins(10, 0, 10, 0)
        self.generator_form_splitter = QSplitter(self.scrollAreaWidgetContents)
        self.generator_form_splitter.setObjectName("generator_form_splitter")
        self.generator_form_splitter.setOrientation(Qt.Orientation.Vertical)
        self.generator_form_splitter.setChildrenCollapsible(False)
        self.layoutWidget = QWidget(self.generator_form_splitter)
        self.layoutWidget.setObjectName("layoutWidget")
        self.prompt_container_layout = QGridLayout(self.layoutWidget)
        self.prompt_container_layout.setObjectName("prompt_container_layout")
        self.prompt_container_layout.setContentsMargins(0, 0, 0, 9)
        self.add_prompt_button = QPushButton(self.layoutWidget)
        self.add_prompt_button.setObjectName("add_prompt_button")

        self.prompt_container_layout.addWidget(self.add_prompt_button, 3, 0, 1, 1)

        self.additional_prompts_container_layout = QVBoxLayout()
        self.additional_prompts_container_layout.setObjectName(
            "additional_prompts_container_layout"
        )

        self.prompt_container_layout.addLayout(
            self.additional_prompts_container_layout, 2, 0, 1, 2
        )

        self.label = QLabel(self.layoutWidget)
        self.label.setObjectName("label")
        font1 = QFont()
        font1.setPointSize(8)
        font1.setBold(True)
        self.label.setFont(font1)

        self.prompt_container_layout.addWidget(self.label, 0, 0, 1, 1)

        self.prompt_container = QHBoxLayout()
        self.prompt_container.setObjectName("prompt_container")
        self.prompt = QPlainTextEdit(self.layoutWidget)
        self.prompt.setObjectName("prompt")

        self.prompt_container.addWidget(self.prompt)

        self.secondary_prompt = QPlainTextEdit(self.layoutWidget)
        self.secondary_prompt.setObjectName("secondary_prompt")

        self.prompt_container.addWidget(self.secondary_prompt)

        self.prompt_container_layout.addLayout(self.prompt_container, 1, 0, 1, 2)

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.horizontalLayout_6.setContentsMargins(-1, 10, -1, -1)
        self.horizontalSpacer = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )

        self.horizontalLayout_6.addItem(self.horizontalSpacer)

        self.pushButton = QPushButton(self.layoutWidget)
        self.pushButton.setObjectName("pushButton")

        self.horizontalLayout_6.addWidget(self.pushButton)

        self.prompt_container_layout.addLayout(self.horizontalLayout_6, 0, 1, 1, 1)

        self.generator_form_splitter.addWidget(self.layoutWidget)
        self.layoutWidget1 = QWidget(self.generator_form_splitter)
        self.layoutWidget1.setObjectName("layoutWidget1")
        self.negative_prompt_container = QVBoxLayout(self.layoutWidget1)
        self.negative_prompt_container.setObjectName("negative_prompt_container")
        self.negative_prompt_container.setContentsMargins(0, 5, 0, 0)
        self.negative_prompt_label = QLabel(self.layoutWidget1)
        self.negative_prompt_label.setObjectName("negative_prompt_label")
        self.negative_prompt_label.setFont(font1)

        self.negative_prompt_container.addWidget(self.negative_prompt_label)

        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        self.negative_prompt = QPlainTextEdit(self.layoutWidget1)
        self.negative_prompt.setObjectName("negative_prompt")

        self.horizontalLayout_8.addWidget(self.negative_prompt)

        self.secondary_negative_prompt = QPlainTextEdit(self.layoutWidget1)
        self.secondary_negative_prompt.setObjectName("secondary_negative_prompt")

        self.horizontalLayout_8.addWidget(self.secondary_negative_prompt)

        self.negative_prompt_container.addLayout(self.horizontalLayout_8)

        self.generator_form_splitter.addWidget(self.layoutWidget1)

        self.gridLayout.addWidget(self.generator_form_splitter, 0, 0, 1, 1)

        self.sdxl_settings_container = QWidget(self.scrollAreaWidgetContents)
        self.sdxl_settings_container.setObjectName("sdxl_settings_container")
        self.sdxl_settings = QVBoxLayout(self.sdxl_settings_container)
        self.sdxl_settings.setObjectName("sdxl_settings")
        self.sdxl_settings.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.label_2 = QLabel(self.sdxl_settings_container)
        self.label_2.setObjectName("label_2")

        self.verticalLayout.addWidget(self.label_2)

        self.image_presets = QComboBox(self.sdxl_settings_container)
        self.image_presets.setObjectName("image_presets")

        self.verticalLayout.addWidget(self.image_presets)

        self.line_2 = QFrame(self.sdxl_settings_container)
        self.line_2.setObjectName("line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout.addWidget(self.line_2)

        self.horizontalLayout.addLayout(self.verticalLayout)

        self.quality_effects_container = QVBoxLayout()
        self.quality_effects_container.setObjectName("quality_effects_container")
        self.label_3 = QLabel(self.sdxl_settings_container)
        self.label_3.setObjectName("label_3")

        self.quality_effects_container.addWidget(self.label_3)

        self.quality_effects = QComboBox(self.sdxl_settings_container)
        self.quality_effects.addItem("")
        self.quality_effects.addItem("")
        self.quality_effects.addItem("")
        self.quality_effects.addItem("")
        self.quality_effects.setObjectName("quality_effects")

        self.quality_effects_container.addWidget(self.quality_effects)

        self.line = QFrame(self.sdxl_settings_container)
        self.line.setObjectName("line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.quality_effects_container.addWidget(self.line)

        self.horizontalLayout.addLayout(self.quality_effects_container)

        self.sdxl_settings.addLayout(self.horizontalLayout)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.groupBox = QGroupBox(self.sdxl_settings_container)
        self.groupBox.setObjectName("groupBox")
        self.horizontalLayout_3 = QHBoxLayout(self.groupBox)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.original_size_width = QLineEdit(self.groupBox)
        self.original_size_width.setObjectName("original_size_width")

        self.horizontalLayout_3.addWidget(self.original_size_width)

        self.original_size_height = QLineEdit(self.groupBox)
        self.original_size_height.setObjectName("original_size_height")

        self.horizontalLayout_3.addWidget(self.original_size_height)

        self.horizontalLayout_5.addWidget(self.groupBox)

        self.groupBox_3 = QGroupBox(self.sdxl_settings_container)
        self.groupBox_3.setObjectName("groupBox_3")
        self.horizontalLayout_9 = QHBoxLayout(self.groupBox_3)
        self.horizontalLayout_9.setObjectName("horizontalLayout_9")
        self.negative_original_size_width = QLineEdit(self.groupBox_3)
        self.negative_original_size_width.setObjectName("negative_original_size_width")

        self.horizontalLayout_9.addWidget(self.negative_original_size_width)

        self.negative_original_size_height = QLineEdit(self.groupBox_3)
        self.negative_original_size_height.setObjectName(
            "negative_original_size_height"
        )

        self.horizontalLayout_9.addWidget(self.negative_original_size_height)

        self.horizontalLayout_5.addWidget(self.groupBox_3)

        self.sdxl_settings.addLayout(self.horizontalLayout_5)

        self.horizontalLayout_10 = QHBoxLayout()
        self.horizontalLayout_10.setObjectName("horizontalLayout_10")
        self.groupBox_4 = QGroupBox(self.sdxl_settings_container)
        self.groupBox_4.setObjectName("groupBox_4")
        self.horizontalLayout_11 = QHBoxLayout(self.groupBox_4)
        self.horizontalLayout_11.setObjectName("horizontalLayout_11")
        self.target_size_width = QLineEdit(self.groupBox_4)
        self.target_size_width.setObjectName("target_size_width")

        self.horizontalLayout_11.addWidget(self.target_size_width)

        self.target_size_height = QLineEdit(self.groupBox_4)
        self.target_size_height.setObjectName("target_size_height")

        self.horizontalLayout_11.addWidget(self.target_size_height)

        self.horizontalLayout_10.addWidget(self.groupBox_4)

        self.groupBox_2 = QGroupBox(self.sdxl_settings_container)
        self.groupBox_2.setObjectName("groupBox_2")
        self.horizontalLayout_4 = QHBoxLayout(self.groupBox_2)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.negative_target_size_width = QLineEdit(self.groupBox_2)
        self.negative_target_size_width.setObjectName("negative_target_size_width")

        self.horizontalLayout_4.addWidget(self.negative_target_size_width)

        self.negative_target_size_height = QLineEdit(self.groupBox_2)
        self.negative_target_size_height.setObjectName("negative_target_size_height")

        self.horizontalLayout_4.addWidget(self.negative_target_size_height)

        self.horizontalLayout_10.addWidget(self.groupBox_2)

        self.sdxl_settings.addLayout(self.horizontalLayout_10)

        self.horizontalLayout_12 = QHBoxLayout()
        self.horizontalLayout_12.setObjectName("horizontalLayout_12")
        self.croops_coord_top_left_groupbox = QGroupBox(self.sdxl_settings_container)
        self.croops_coord_top_left_groupbox.setObjectName(
            "croops_coord_top_left_groupbox"
        )
        self.horizontalLayout_2 = QHBoxLayout(self.croops_coord_top_left_groupbox)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(9, 9, 9, 9)
        self.crops_coords_top_left_x = QLineEdit(self.croops_coord_top_left_groupbox)
        self.crops_coords_top_left_x.setObjectName("crops_coords_top_left_x")

        self.horizontalLayout_2.addWidget(self.crops_coords_top_left_x)

        self.crops_coords_top_left_y = QLineEdit(self.croops_coord_top_left_groupbox)
        self.crops_coords_top_left_y.setObjectName("crops_coords_top_left_y")

        self.horizontalLayout_2.addWidget(self.crops_coords_top_left_y)

        self.horizontalLayout_12.addWidget(self.croops_coord_top_left_groupbox)

        self.groupBox_5 = QGroupBox(self.sdxl_settings_container)
        self.groupBox_5.setObjectName("groupBox_5")
        self.horizontalLayout_13 = QHBoxLayout(self.groupBox_5)
        self.horizontalLayout_13.setObjectName("horizontalLayout_13")
        self.negative_crops_coord_top_left_x = QLineEdit(self.groupBox_5)
        self.negative_crops_coord_top_left_x.setObjectName(
            "negative_crops_coord_top_left_x"
        )

        self.horizontalLayout_13.addWidget(self.negative_crops_coord_top_left_x)

        self.negative_crops_coord_top_left_y = QLineEdit(self.groupBox_5)
        self.negative_crops_coord_top_left_y.setObjectName(
            "negative_crops_coord_top_left_y"
        )

        self.horizontalLayout_13.addWidget(self.negative_crops_coord_top_left_y)

        self.horizontalLayout_12.addWidget(self.groupBox_5)

        self.sdxl_settings.addLayout(self.horizontalLayout_12)

        self.n_samples = SliderWidget(self.sdxl_settings_container)
        self.n_samples.setObjectName("n_samples")
        self.n_samples.setProperty("current_value", 1)
        self.n_samples.setProperty("slider_maximum", 1000)
        self.n_samples.setProperty("spinbox_maximum", 1000)
        self.n_samples.setProperty("display_as_float", False)
        self.n_samples.setProperty("spinbox_single_step", 1)
        self.n_samples.setProperty("spinbox_page_step", 1)
        self.n_samples.setProperty("spinbox_minimum", 1)
        self.n_samples.setProperty("slider_minimum", 1)

        self.sdxl_settings.addWidget(self.n_samples)

        self.horizontalLayout_14 = QHBoxLayout()
        self.horizontalLayout_14.setObjectName("horizontalLayout_14")
        self.images_per_batch = SliderWidget(self.sdxl_settings_container)
        self.images_per_batch.setObjectName("images_per_batch")
        self.images_per_batch.setProperty("current_value", 1)
        self.images_per_batch.setProperty("slider_maximum", 6)
        self.images_per_batch.setProperty("spinbox_maximum", 6)
        self.images_per_batch.setProperty("display_as_float", False)
        self.images_per_batch.setProperty("spinbox_single_step", 1)
        self.images_per_batch.setProperty("spinbox_page_step", 1)
        self.images_per_batch.setProperty("spinbox_minimum", 1)
        self.images_per_batch.setProperty("slider_minimum", 1)

        self.horizontalLayout_14.addWidget(self.images_per_batch)

        self.infinite_images_button = QPushButton(self.sdxl_settings_container)
        self.infinite_images_button.setObjectName("infinite_images_button")
        self.infinite_images_button.setMinimumSize(QSize(30, 30))
        self.infinite_images_button.setMaximumSize(QSize(30, 30))
        icon = QIcon()
        icon.addFile(
            ":/light/icons/feather/light/circle.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.infinite_images_button.setIcon(icon)
        self.infinite_images_button.setCheckable(True)
        self.infinite_images_button.setChecked(False)

        self.horizontalLayout_14.addWidget(self.infinite_images_button)

        self.sdxl_settings.addLayout(self.horizontalLayout_14)

        self.gridLayout.addWidget(self.sdxl_settings_container, 2, 0, 1, 1)

        self.stable_diffusion_generator_form.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_3.addWidget(self.stable_diffusion_generator_form, 0, 0, 1, 1)

        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.horizontalLayout_7.setContentsMargins(10, 10, 10, 10)
        self.progress_bar = QProgressBar(self.generator_form_tabs)
        self.progress_bar.setObjectName("progress_bar")
        sizePolicy = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.progress_bar.sizePolicy().hasHeightForWidth())
        self.progress_bar.setSizePolicy(sizePolicy)
        self.progress_bar.setMinimumSize(QSize(0, 30))
        self.progress_bar.setValue(0)

        self.horizontalLayout_7.addWidget(self.progress_bar)

        self.generate_button = QPushButton(self.generator_form_tabs)
        self.generate_button.setObjectName("generate_button")
        sizePolicy1 = QSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum
        )
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(
            self.generate_button.sizePolicy().hasHeightForWidth()
        )
        self.generate_button.setSizePolicy(sizePolicy1)
        self.generate_button.setMinimumSize(QSize(30, 30))
        self.generate_button.setMaximumSize(QSize(30, 30))
        icon1 = QIcon()
        icon1.addFile(
            ":/light/icons/feather/light/chevron-up.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.generate_button.setIcon(icon1)

        self.horizontalLayout_7.addWidget(self.generate_button)

        self.interrupt_button = QPushButton(self.generator_form_tabs)
        self.interrupt_button.setObjectName("interrupt_button")
        sizePolicy1.setHeightForWidth(
            self.interrupt_button.sizePolicy().hasHeightForWidth()
        )
        self.interrupt_button.setSizePolicy(sizePolicy1)
        self.interrupt_button.setMinimumSize(QSize(30, 30))
        self.interrupt_button.setMaximumSize(QSize(30, 30))
        self.interrupt_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon2 = QIcon()
        icon2.addFile(
            ":/light/icons/feather/light/x.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.interrupt_button.setIcon(icon2)

        self.horizontalLayout_7.addWidget(self.interrupt_button)

        self.gridLayout_3.addLayout(self.horizontalLayout_7, 1, 0, 1, 1)

        self.gridLayout_4.addWidget(self.generator_form_tabs, 0, 0, 1, 1)

        QWidget.setTabOrder(self.prompt, self.secondary_prompt)
        QWidget.setTabOrder(self.secondary_prompt, self.add_prompt_button)
        QWidget.setTabOrder(self.add_prompt_button, self.negative_prompt)
        QWidget.setTabOrder(self.negative_prompt, self.secondary_negative_prompt)
        QWidget.setTabOrder(self.secondary_negative_prompt, self.image_presets)
        QWidget.setTabOrder(self.image_presets, self.quality_effects)
        QWidget.setTabOrder(self.quality_effects, self.original_size_width)
        QWidget.setTabOrder(self.original_size_width, self.original_size_height)
        QWidget.setTabOrder(
            self.original_size_height, self.negative_original_size_width
        )
        QWidget.setTabOrder(
            self.negative_original_size_width, self.negative_original_size_height
        )
        QWidget.setTabOrder(self.negative_original_size_height, self.target_size_width)
        QWidget.setTabOrder(self.target_size_width, self.target_size_height)
        QWidget.setTabOrder(self.target_size_height, self.negative_target_size_width)
        QWidget.setTabOrder(
            self.negative_target_size_width, self.negative_target_size_height
        )
        QWidget.setTabOrder(
            self.negative_target_size_height, self.crops_coords_top_left_x
        )
        QWidget.setTabOrder(self.crops_coords_top_left_x, self.crops_coords_top_left_y)
        QWidget.setTabOrder(
            self.crops_coords_top_left_y, self.negative_crops_coord_top_left_x
        )
        QWidget.setTabOrder(
            self.negative_crops_coord_top_left_x, self.negative_crops_coord_top_left_y
        )
        QWidget.setTabOrder(self.negative_crops_coord_top_left_y, self.generate_button)
        QWidget.setTabOrder(self.generate_button, self.interrupt_button)
        QWidget.setTabOrder(self.interrupt_button, self.pushButton)
        QWidget.setTabOrder(self.pushButton, self.stable_diffusion_generator_form)

        self.retranslateUi(stablediffusion_generator_form)
        self.pushButton.clicked.connect(
            stablediffusion_generator_form.action_clicked_button_save_prompts
        )
        self.image_presets.currentTextChanged.connect(
            stablediffusion_generator_form.handle_image_presets_changed
        )
        self.quality_effects.currentTextChanged.connect(
            stablediffusion_generator_form.handle_quality_effects_changed
        )
        self.prompt.textChanged.connect(
            stablediffusion_generator_form.handle_prompt_changed
        )
        self.secondary_prompt.textChanged.connect(
            stablediffusion_generator_form.handle_second_prompt_changed
        )
        self.negative_prompt.textChanged.connect(
            stablediffusion_generator_form.handle_negative_prompt_changed
        )
        self.secondary_negative_prompt.textChanged.connect(
            stablediffusion_generator_form.handle_second_negative_prompt_changed
        )

        QMetaObject.connectSlotsByName(stablediffusion_generator_form)

    # setupUi

    def retranslateUi(self, stablediffusion_generator_form):
        stablediffusion_generator_form.setWindowTitle(
            QCoreApplication.translate("stablediffusion_generator_form", "Form", None)
        )
        self.add_prompt_button.setText(
            QCoreApplication.translate(
                "stablediffusion_generator_form", "Add Prompt", None
            )
        )
        self.label.setText(
            QCoreApplication.translate("stablediffusion_generator_form", "Prompt", None)
        )
        self.prompt.setPlaceholderText(
            QCoreApplication.translate("stablediffusion_generator_form", "Prompt", None)
        )
        self.secondary_prompt.setPlaceholderText(
            QCoreApplication.translate(
                "stablediffusion_generator_form", "Second prompt", None
            )
        )
        self.pushButton.setText(
            QCoreApplication.translate(
                "stablediffusion_generator_form", "Save Prompts", None
            )
        )
        self.negative_prompt_label.setText(
            QCoreApplication.translate(
                "stablediffusion_generator_form", "Negative Prompt", None
            )
        )
        self.negative_prompt.setPlaceholderText(
            QCoreApplication.translate(
                "stablediffusion_generator_form", "Negative prompt", None
            )
        )
        self.secondary_negative_prompt.setPlaceholderText(
            QCoreApplication.translate(
                "stablediffusion_generator_form", "Second negative prompt", None
            )
        )
        self.label_2.setText(
            QCoreApplication.translate(
                "stablediffusion_generator_form", "Presets", None
            )
        )
        self.label_3.setText(
            QCoreApplication.translate(
                "stablediffusion_generator_form", "Quality Effects", None
            )
        )
        self.quality_effects.setItemText(0, "")
        self.quality_effects.setItemText(
            1,
            QCoreApplication.translate(
                "stablediffusion_generator_form", "Normal", None
            ),
        )
        self.quality_effects.setItemText(
            2,
            QCoreApplication.translate(
                "stablediffusion_generator_form", "Upscaled", None
            ),
        )
        self.quality_effects.setItemText(
            3,
            QCoreApplication.translate(
                "stablediffusion_generator_form", "Downscaled", None
            ),
        )

        self.groupBox.setTitle(
            QCoreApplication.translate(
                "stablediffusion_generator_form", "Original size", None
            )
        )
        self.original_size_width.setPlaceholderText(
            QCoreApplication.translate("stablediffusion_generator_form", "width", None)
        )
        self.original_size_height.setPlaceholderText(
            QCoreApplication.translate("stablediffusion_generator_form", "height", None)
        )
        self.groupBox_3.setTitle(
            QCoreApplication.translate(
                "stablediffusion_generator_form", "Negative original size", None
            )
        )
        self.negative_original_size_width.setPlaceholderText(
            QCoreApplication.translate("stablediffusion_generator_form", "width", None)
        )
        self.negative_original_size_height.setPlaceholderText(
            QCoreApplication.translate("stablediffusion_generator_form", "height", None)
        )
        self.groupBox_4.setTitle(
            QCoreApplication.translate(
                "stablediffusion_generator_form", "Target size", None
            )
        )
        self.target_size_width.setPlaceholderText(
            QCoreApplication.translate("stablediffusion_generator_form", "width", None)
        )
        self.target_size_height.setPlaceholderText(
            QCoreApplication.translate("stablediffusion_generator_form", "height", None)
        )
        self.groupBox_2.setTitle(
            QCoreApplication.translate(
                "stablediffusion_generator_form", "Negative target size", None
            )
        )
        self.negative_target_size_width.setPlaceholderText(
            QCoreApplication.translate("stablediffusion_generator_form", "width", None)
        )
        self.negative_target_size_height.setPlaceholderText(
            QCoreApplication.translate("stablediffusion_generator_form", "height", None)
        )
        self.croops_coord_top_left_groupbox.setTitle(
            QCoreApplication.translate(
                "stablediffusion_generator_form", "Crops top left", None
            )
        )
        self.crops_coords_top_left_x.setPlaceholderText(
            QCoreApplication.translate(
                "stablediffusion_generator_form", "x position", None
            )
        )
        self.crops_coords_top_left_y.setPlaceholderText(
            QCoreApplication.translate(
                "stablediffusion_generator_form", "y position", None
            )
        )
        self.groupBox_5.setTitle(
            QCoreApplication.translate(
                "stablediffusion_generator_form", "Negative crops top left", None
            )
        )
        self.negative_crops_coord_top_left_x.setPlaceholderText(
            QCoreApplication.translate(
                "stablediffusion_generator_form", "x position", None
            )
        )
        self.negative_crops_coord_top_left_y.setPlaceholderText(
            QCoreApplication.translate(
                "stablediffusion_generator_form", "y position", None
            )
        )
        self.n_samples.setProperty(
            "label_text",
            QCoreApplication.translate(
                "stablediffusion_generator_form", "Batches", None
            ),
        )
        self.n_samples.setProperty(
            "settings_property",
            QCoreApplication.translate(
                "stablediffusion_generator_form", "generator_settings.n_samples", None
            ),
        )
        self.images_per_batch.setProperty(
            "label_text",
            QCoreApplication.translate(
                "stablediffusion_generator_form", "Images Per Batch", None
            ),
        )
        self.images_per_batch.setProperty(
            "settings_property",
            QCoreApplication.translate(
                "stablediffusion_generator_form",
                "generator_settings.images_per_batch",
                None,
            ),
        )
        # if QT_CONFIG(tooltip)
        self.infinite_images_button.setToolTip(
            QCoreApplication.translate(
                "stablediffusion_generator_form",
                "Toggle infinite image generation",
                None,
            )
        )
        # endif // QT_CONFIG(tooltip)
        self.infinite_images_button.setText("")
        # if QT_CONFIG(tooltip)
        self.generate_button.setToolTip(
            QCoreApplication.translate(
                "stablediffusion_generator_form", "Generate image", None
            )
        )
        # endif // QT_CONFIG(tooltip)
        self.generate_button.setText("")
        # if QT_CONFIG(tooltip)
        self.interrupt_button.setToolTip(
            QCoreApplication.translate(
                "stablediffusion_generator_form", "Cancel image generation", None
            )
        )
        # endif // QT_CONFIG(tooltip)
        self.interrupt_button.setText("")

    # retranslateUi
