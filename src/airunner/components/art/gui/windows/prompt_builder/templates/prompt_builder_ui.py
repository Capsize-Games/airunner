# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'prompt_builder.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QPlainTextEdit, QPushButton, QScrollArea,
    QSizePolicy, QSpacerItem, QSpinBox, QVBoxLayout,
    QWidget)

class Ui_prompt_builder(object):
    def setupUi(self, prompt_builder):
        if not prompt_builder.objectName():
            prompt_builder.setObjectName(u"prompt_builder")
        prompt_builder.resize(720, 780)
        prompt_builder.setMinimumSize(QSize(600, 600))
        self.verticalLayout_root = QVBoxLayout(prompt_builder)
        self.verticalLayout_root.setObjectName(u"verticalLayout_root")
        self.horizontalLayout_target = QHBoxLayout()
        self.horizontalLayout_target.setObjectName(u"horizontalLayout_target")
        self.label_target = QLabel(prompt_builder)
        self.label_target.setObjectName(u"label_target")

        self.horizontalLayout_target.addWidget(self.label_target)

        self.target_generator = QComboBox(prompt_builder)
        self.target_generator.addItem("")
        self.target_generator.addItem("")
        self.target_generator.setObjectName(u"target_generator")

        self.horizontalLayout_target.addWidget(self.target_generator)

        self.horizontalSpacer_target = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_target.addItem(self.horizontalSpacer_target)

        self.randomize_checkbox = QCheckBox(prompt_builder)
        self.randomize_checkbox.setObjectName(u"randomize_checkbox")
        self.randomize_checkbox.setChecked(True)

        self.horizontalLayout_target.addWidget(self.randomize_checkbox)

        self.random_seed_checkbox = QCheckBox(prompt_builder)
        self.random_seed_checkbox.setObjectName(u"random_seed_checkbox")
        self.random_seed_checkbox.setChecked(True)

        self.horizontalLayout_target.addWidget(self.random_seed_checkbox)

        self.label_seed = QLabel(prompt_builder)
        self.label_seed.setObjectName(u"label_seed")

        self.horizontalLayout_target.addWidget(self.label_seed)

        self.seed_spinbox = QSpinBox(prompt_builder)
        self.seed_spinbox.setObjectName(u"seed_spinbox")
        self.seed_spinbox.setMaximum(2147483647)

        self.horizontalLayout_target.addWidget(self.seed_spinbox)


        self.verticalLayout_root.addLayout(self.horizontalLayout_target)

        self.scrollArea = QScrollArea(prompt_builder)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 688, 480))
        self.verticalLayout_scroll = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_scroll.setObjectName(u"verticalLayout_scroll")
        self.groupBox_subject = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_subject.setObjectName(u"groupBox_subject")
        self.gridLayout_subject = QGridLayout(self.groupBox_subject)
        self.gridLayout_subject.setObjectName(u"gridLayout_subject")
        self.label_subject = QLabel(self.groupBox_subject)
        self.label_subject.setObjectName(u"label_subject")

        self.gridLayout_subject.addWidget(self.label_subject, 0, 0, 1, 1)

        self.subject = QComboBox(self.groupBox_subject)
        self.subject.setObjectName(u"subject")

        self.gridLayout_subject.addWidget(self.subject, 0, 1, 1, 1)

        self.label_age = QLabel(self.groupBox_subject)
        self.label_age.setObjectName(u"label_age")

        self.gridLayout_subject.addWidget(self.label_age, 1, 0, 1, 1)

        self.attribute_age = QComboBox(self.groupBox_subject)
        self.attribute_age.setObjectName(u"attribute_age")

        self.gridLayout_subject.addWidget(self.attribute_age, 1, 1, 1, 1)

        self.label_skin = QLabel(self.groupBox_subject)
        self.label_skin.setObjectName(u"label_skin")

        self.gridLayout_subject.addWidget(self.label_skin, 2, 0, 1, 1)

        self.attribute_skin = QComboBox(self.groupBox_subject)
        self.attribute_skin.setObjectName(u"attribute_skin")

        self.gridLayout_subject.addWidget(self.attribute_skin, 2, 1, 1, 1)

        self.label_hair = QLabel(self.groupBox_subject)
        self.label_hair.setObjectName(u"label_hair")

        self.gridLayout_subject.addWidget(self.label_hair, 3, 0, 1, 1)

        self.attribute_hair = QComboBox(self.groupBox_subject)
        self.attribute_hair.setObjectName(u"attribute_hair")

        self.gridLayout_subject.addWidget(self.attribute_hair, 3, 1, 1, 1)

        self.label_wardrobe = QLabel(self.groupBox_subject)
        self.label_wardrobe.setObjectName(u"label_wardrobe")

        self.gridLayout_subject.addWidget(self.label_wardrobe, 4, 0, 1, 1)

        self.attribute_wardrobe = QComboBox(self.groupBox_subject)
        self.attribute_wardrobe.setObjectName(u"attribute_wardrobe")

        self.gridLayout_subject.addWidget(self.attribute_wardrobe, 4, 1, 1, 1)

        self.label_expression = QLabel(self.groupBox_subject)
        self.label_expression.setObjectName(u"label_expression")

        self.gridLayout_subject.addWidget(self.label_expression, 5, 0, 1, 1)

        self.attribute_expression = QComboBox(self.groupBox_subject)
        self.attribute_expression.setObjectName(u"attribute_expression")

        self.gridLayout_subject.addWidget(self.attribute_expression, 5, 1, 1, 1)

        self.label_accessory = QLabel(self.groupBox_subject)
        self.label_accessory.setObjectName(u"label_accessory")

        self.gridLayout_subject.addWidget(self.label_accessory, 6, 0, 1, 1)

        self.attribute_accessory = QComboBox(self.groupBox_subject)
        self.attribute_accessory.setObjectName(u"attribute_accessory")

        self.gridLayout_subject.addWidget(self.attribute_accessory, 6, 1, 1, 1)

        self.label_action = QLabel(self.groupBox_subject)
        self.label_action.setObjectName(u"label_action")

        self.gridLayout_subject.addWidget(self.label_action, 7, 0, 1, 1)

        self.action = QComboBox(self.groupBox_subject)
        self.action.setObjectName(u"action")

        self.gridLayout_subject.addWidget(self.action, 7, 1, 1, 1)

        self.label_object = QLabel(self.groupBox_subject)
        self.label_object.setObjectName(u"label_object")

        self.gridLayout_subject.addWidget(self.label_object, 8, 0, 1, 1)

        self.object = QComboBox(self.groupBox_subject)
        self.object.setObjectName(u"object")

        self.gridLayout_subject.addWidget(self.object, 8, 1, 1, 1)

        self.custom_subject = QLineEdit(self.groupBox_subject)
        self.custom_subject.setObjectName(u"custom_subject")

        self.gridLayout_subject.addWidget(self.custom_subject, 9, 0, 1, 2)


        self.verticalLayout_scroll.addWidget(self.groupBox_subject)

        self.groupBox_scene = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_scene.setObjectName(u"groupBox_scene")
        self.gridLayout_scene = QGridLayout(self.groupBox_scene)
        self.gridLayout_scene.setObjectName(u"gridLayout_scene")
        self.label_scene = QLabel(self.groupBox_scene)
        self.label_scene.setObjectName(u"label_scene")

        self.gridLayout_scene.addWidget(self.label_scene, 0, 0, 1, 1)

        self.scene = QComboBox(self.groupBox_scene)
        self.scene.setObjectName(u"scene")

        self.gridLayout_scene.addWidget(self.scene, 0, 1, 1, 1)

        self.label_time_of_day = QLabel(self.groupBox_scene)
        self.label_time_of_day.setObjectName(u"label_time_of_day")

        self.gridLayout_scene.addWidget(self.label_time_of_day, 1, 0, 1, 1)

        self.time_of_day = QComboBox(self.groupBox_scene)
        self.time_of_day.setObjectName(u"time_of_day")

        self.gridLayout_scene.addWidget(self.time_of_day, 1, 1, 1, 1)

        self.label_weather = QLabel(self.groupBox_scene)
        self.label_weather.setObjectName(u"label_weather")

        self.gridLayout_scene.addWidget(self.label_weather, 2, 0, 1, 1)

        self.weather = QComboBox(self.groupBox_scene)
        self.weather.setObjectName(u"weather")

        self.gridLayout_scene.addWidget(self.weather, 2, 1, 1, 1)

        self.custom_scene = QLineEdit(self.groupBox_scene)
        self.custom_scene.setObjectName(u"custom_scene")

        self.gridLayout_scene.addWidget(self.custom_scene, 3, 0, 1, 2)


        self.verticalLayout_scroll.addWidget(self.groupBox_scene)

        self.groupBox_composition = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_composition.setObjectName(u"groupBox_composition")
        self.gridLayout_composition = QGridLayout(self.groupBox_composition)
        self.gridLayout_composition.setObjectName(u"gridLayout_composition")
        self.label_shot_type = QLabel(self.groupBox_composition)
        self.label_shot_type.setObjectName(u"label_shot_type")

        self.gridLayout_composition.addWidget(self.label_shot_type, 0, 0, 1, 1)

        self.shot_type = QComboBox(self.groupBox_composition)
        self.shot_type.setObjectName(u"shot_type")

        self.gridLayout_composition.addWidget(self.shot_type, 0, 1, 1, 1)

        self.label_lens = QLabel(self.groupBox_composition)
        self.label_lens.setObjectName(u"label_lens")

        self.gridLayout_composition.addWidget(self.label_lens, 1, 0, 1, 1)

        self.lens = QComboBox(self.groupBox_composition)
        self.lens.setObjectName(u"lens")

        self.gridLayout_composition.addWidget(self.lens, 1, 1, 1, 1)

        self.label_composition = QLabel(self.groupBox_composition)
        self.label_composition.setObjectName(u"label_composition")

        self.gridLayout_composition.addWidget(self.label_composition, 2, 0, 1, 1)

        self.composition = QComboBox(self.groupBox_composition)
        self.composition.setObjectName(u"composition")

        self.gridLayout_composition.addWidget(self.composition, 2, 1, 1, 1)


        self.verticalLayout_scroll.addWidget(self.groupBox_composition)

        self.groupBox_lighting = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_lighting.setObjectName(u"groupBox_lighting")
        self.gridLayout_lighting = QGridLayout(self.groupBox_lighting)
        self.gridLayout_lighting.setObjectName(u"gridLayout_lighting")
        self.label_lighting = QLabel(self.groupBox_lighting)
        self.label_lighting.setObjectName(u"label_lighting")

        self.gridLayout_lighting.addWidget(self.label_lighting, 0, 0, 1, 1)

        self.lighting = QComboBox(self.groupBox_lighting)
        self.lighting.setObjectName(u"lighting")

        self.gridLayout_lighting.addWidget(self.lighting, 0, 1, 1, 1)


        self.verticalLayout_scroll.addWidget(self.groupBox_lighting)

        self.groupBox_style = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_style.setObjectName(u"groupBox_style")
        self.gridLayout_style = QGridLayout(self.groupBox_style)
        self.gridLayout_style.setObjectName(u"gridLayout_style")
        self.label_style_group = QLabel(self.groupBox_style)
        self.label_style_group.setObjectName(u"label_style_group")

        self.gridLayout_style.addWidget(self.label_style_group, 0, 0, 1, 1)

        self.style_group = QComboBox(self.groupBox_style)
        self.style_group.setObjectName(u"style_group")

        self.gridLayout_style.addWidget(self.style_group, 0, 1, 1, 1)

        self.label_style_detail = QLabel(self.groupBox_style)
        self.label_style_detail.setObjectName(u"label_style_detail")

        self.gridLayout_style.addWidget(self.label_style_detail, 1, 0, 1, 1)

        self.style_detail = QComboBox(self.groupBox_style)
        self.style_detail.setObjectName(u"style_detail")

        self.gridLayout_style.addWidget(self.style_detail, 1, 1, 1, 1)

        self.label_color_palette = QLabel(self.groupBox_style)
        self.label_color_palette.setObjectName(u"label_color_palette")

        self.gridLayout_style.addWidget(self.label_color_palette, 2, 0, 1, 1)

        self.color_palette = QComboBox(self.groupBox_style)
        self.color_palette.setObjectName(u"color_palette")

        self.gridLayout_style.addWidget(self.color_palette, 2, 1, 1, 1)

        self.custom_style = QLineEdit(self.groupBox_style)
        self.custom_style.setObjectName(u"custom_style")

        self.gridLayout_style.addWidget(self.custom_style, 3, 0, 1, 2)


        self.verticalLayout_scroll.addWidget(self.groupBox_style)

        self.groupBox_polish = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_polish.setObjectName(u"groupBox_polish")
        self.gridLayout_polish = QGridLayout(self.groupBox_polish)
        self.gridLayout_polish.setObjectName(u"gridLayout_polish")
        self.label_quality = QLabel(self.groupBox_polish)
        self.label_quality.setObjectName(u"label_quality")

        self.gridLayout_polish.addWidget(self.label_quality, 0, 0, 1, 1)

        self.quality = QComboBox(self.groupBox_polish)
        self.quality.setObjectName(u"quality")

        self.gridLayout_polish.addWidget(self.quality, 0, 1, 1, 1)

        self.label_custom_negative = QLabel(self.groupBox_polish)
        self.label_custom_negative.setObjectName(u"label_custom_negative")

        self.gridLayout_polish.addWidget(self.label_custom_negative, 1, 0, 1, 1)

        self.custom_negative = QLineEdit(self.groupBox_polish)
        self.custom_negative.setObjectName(u"custom_negative")

        self.gridLayout_polish.addWidget(self.custom_negative, 1, 1, 1, 1)


        self.verticalLayout_scroll.addWidget(self.groupBox_polish)

        self.groupBox_prefix = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_prefix.setObjectName(u"groupBox_prefix")
        self.horizontalLayout_prefix = QHBoxLayout(self.groupBox_prefix)
        self.horizontalLayout_prefix.setObjectName(u"horizontalLayout_prefix")
        self.prefix = QLineEdit(self.groupBox_prefix)
        self.prefix.setObjectName(u"prefix")

        self.horizontalLayout_prefix.addWidget(self.prefix)

        self.suffix = QLineEdit(self.groupBox_prefix)
        self.suffix.setObjectName(u"suffix")

        self.horizontalLayout_prefix.addWidget(self.suffix)


        self.verticalLayout_scroll.addWidget(self.groupBox_prefix)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout_root.addWidget(self.scrollArea)

        self.groupBox_preview = QGroupBox(prompt_builder)
        self.groupBox_preview.setObjectName(u"groupBox_preview")
        self.verticalLayout_preview = QVBoxLayout(self.groupBox_preview)
        self.verticalLayout_preview.setObjectName(u"verticalLayout_preview")
        self.prompt_preview = QPlainTextEdit(self.groupBox_preview)
        self.prompt_preview.setObjectName(u"prompt_preview")
        self.prompt_preview.setReadOnly(False)

        self.verticalLayout_preview.addWidget(self.prompt_preview)

        self.negative_prompt_label = QLabel(self.groupBox_preview)
        self.negative_prompt_label.setObjectName(u"negative_prompt_label")

        self.verticalLayout_preview.addWidget(self.negative_prompt_label)

        self.negative_prompt_preview = QPlainTextEdit(self.groupBox_preview)
        self.negative_prompt_preview.setObjectName(u"negative_prompt_preview")
        self.negative_prompt_preview.setReadOnly(False)

        self.verticalLayout_preview.addWidget(self.negative_prompt_preview)


        self.verticalLayout_root.addWidget(self.groupBox_preview)

        self.horizontalLayout_buttons = QHBoxLayout()
        self.horizontalLayout_buttons.setObjectName(u"horizontalLayout_buttons")
        self.word_count_label = QLabel(prompt_builder)
        self.word_count_label.setObjectName(u"word_count_label")

        self.horizontalLayout_buttons.addWidget(self.word_count_label)

        self.horizontalSpacer_buttons = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_buttons.addItem(self.horizontalSpacer_buttons)

        self.randomize_button = QPushButton(prompt_builder)
        self.randomize_button.setObjectName(u"randomize_button")

        self.horizontalLayout_buttons.addWidget(self.randomize_button)

        self.generate_button = QPushButton(prompt_builder)
        self.generate_button.setObjectName(u"generate_button")

        self.horizontalLayout_buttons.addWidget(self.generate_button)

        self.generate_image_button = QPushButton(prompt_builder)
        self.generate_image_button.setObjectName(u"generate_image_button")

        self.horizontalLayout_buttons.addWidget(self.generate_image_button)


        self.verticalLayout_root.addLayout(self.horizontalLayout_buttons)


        self.retranslateUi(prompt_builder)

        QMetaObject.connectSlotsByName(prompt_builder)
    # setupUi

    def retranslateUi(self, prompt_builder):
        prompt_builder.setWindowTitle(QCoreApplication.translate("prompt_builder", u"Prompt Builder", None))
        self.label_target.setText(QCoreApplication.translate("prompt_builder", u"Target Model", None))
        self.target_generator.setItemText(0, QCoreApplication.translate("prompt_builder", u"zimage", None))
        self.target_generator.setItemText(1, QCoreApplication.translate("prompt_builder", u"stablediffusion", None))

        self.randomize_checkbox.setText(QCoreApplication.translate("prompt_builder", u"Randomize unfilled slots", None))
        self.random_seed_checkbox.setText(QCoreApplication.translate("prompt_builder", u"Random seed", None))
#if QT_CONFIG(tooltip)
        self.random_seed_checkbox.setToolTip(QCoreApplication.translate("prompt_builder", u"Use a fresh seed for every build so repeated generates differ. Uncheck to pin the seed below for reproducible prompts.", None))
#endif // QT_CONFIG(tooltip)
        self.label_seed.setText(QCoreApplication.translate("prompt_builder", u"Seed", None))
        self.groupBox_subject.setTitle(QCoreApplication.translate("prompt_builder", u"Subject", None))
        self.label_subject.setText(QCoreApplication.translate("prompt_builder", u"Subject", None))
        self.label_age.setText(QCoreApplication.translate("prompt_builder", u"Age", None))
        self.label_skin.setText(QCoreApplication.translate("prompt_builder", u"Skin", None))
        self.label_hair.setText(QCoreApplication.translate("prompt_builder", u"Hair", None))
        self.label_wardrobe.setText(QCoreApplication.translate("prompt_builder", u"Wardrobe", None))
        self.label_expression.setText(QCoreApplication.translate("prompt_builder", u"Expression", None))
        self.label_accessory.setText(QCoreApplication.translate("prompt_builder", u"Accessory", None))
        self.label_action.setText(QCoreApplication.translate("prompt_builder", u"Action", None))
        self.label_object.setText(QCoreApplication.translate("prompt_builder", u"Object", None))
        self.custom_subject.setPlaceholderText(QCoreApplication.translate("prompt_builder", u"Custom subject (overrides the dropdowns)", None))
        self.groupBox_scene.setTitle(QCoreApplication.translate("prompt_builder", u"Scene & Environment", None))
        self.label_scene.setText(QCoreApplication.translate("prompt_builder", u"Location", None))
        self.label_time_of_day.setText(QCoreApplication.translate("prompt_builder", u"Time of Day", None))
        self.label_weather.setText(QCoreApplication.translate("prompt_builder", u"Weather", None))
        self.custom_scene.setPlaceholderText(QCoreApplication.translate("prompt_builder", u"Custom scene (overrides the dropdowns)", None))
        self.groupBox_composition.setTitle(QCoreApplication.translate("prompt_builder", u"Composition & Framing", None))
        self.label_shot_type.setText(QCoreApplication.translate("prompt_builder", u"Shot Type", None))
        self.label_lens.setText(QCoreApplication.translate("prompt_builder", u"Lens", None))
        self.label_composition.setText(QCoreApplication.translate("prompt_builder", u"Composition", None))
        self.groupBox_lighting.setTitle(QCoreApplication.translate("prompt_builder", u"Lighting", None))
        self.label_lighting.setText(QCoreApplication.translate("prompt_builder", u"Lighting", None))
        self.groupBox_style.setTitle(QCoreApplication.translate("prompt_builder", u"Style & Medium", None))
        self.label_style_group.setText(QCoreApplication.translate("prompt_builder", u"Style Family", None))
        self.label_style_detail.setText(QCoreApplication.translate("prompt_builder", u"Style Detail", None))
        self.label_color_palette.setText(QCoreApplication.translate("prompt_builder", u"Color Palette", None))
        self.custom_style.setPlaceholderText(QCoreApplication.translate("prompt_builder", u"Custom style (appended to the style section)", None))
        self.groupBox_polish.setTitle(QCoreApplication.translate("prompt_builder", u"Constraints & Polish", None))
        self.label_quality.setText(QCoreApplication.translate("prompt_builder", u"Quality Phrase", None))
        self.label_custom_negative.setText(QCoreApplication.translate("prompt_builder", u"Custom Negative Terms", None))
        self.custom_negative.setPlaceholderText(QCoreApplication.translate("prompt_builder", u"Extra negative terms (SDXL only, comma separated)", None))
        self.groupBox_prefix.setTitle(QCoreApplication.translate("prompt_builder", u"Prefix / Suffix", None))
        self.prefix.setPlaceholderText(QCoreApplication.translate("prompt_builder", u"Prefix", None))
        self.suffix.setPlaceholderText(QCoreApplication.translate("prompt_builder", u"Suffix", None))
        self.groupBox_preview.setTitle(QCoreApplication.translate("prompt_builder", u"Prompt Preview", None))
        self.prompt_preview.setPlaceholderText(QCoreApplication.translate("prompt_builder", u"Generated prompt appears here...", None))
        self.negative_prompt_label.setText(QCoreApplication.translate("prompt_builder", u"Negative Prompt (SDXL only)", None))
        self.word_count_label.setText(QCoreApplication.translate("prompt_builder", u"0 words", None))
        self.randomize_button.setText(QCoreApplication.translate("prompt_builder", u"Randomize All", None))
        self.generate_button.setText(QCoreApplication.translate("prompt_builder", u"Generate Prompt", None))
        self.generate_image_button.setText(QCoreApplication.translate("prompt_builder", u"Generate Image", None))
    # retranslateUi

