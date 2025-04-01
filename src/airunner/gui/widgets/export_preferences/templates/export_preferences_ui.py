# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'export_preferences.ui'
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
    QGridLayout, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QSpacerItem, QWidget)

class Ui_export_preferences(object):
    def setupUi(self, export_preferences):
        if not export_preferences.objectName():
            export_preferences.setObjectName(u"export_preferences")
        export_preferences.resize(705, 602)
        self.gridLayout_2 = QGridLayout(export_preferences)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.actionAuto_export_images = QCheckBox(export_preferences)
        self.actionAuto_export_images.setObjectName(u"actionAuto_export_images")
        font = QFont()
        font.setBold(True)
        self.actionAuto_export_images.setFont(font)

        self.gridLayout_2.addWidget(self.actionAuto_export_images, 0, 0, 1, 1)

        self.line = QFrame(export_preferences)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_2.addWidget(self.line, 1, 0, 1, 2)

        self.label = QLabel(export_preferences)
        self.label.setObjectName(u"label")
        self.label.setFont(font)

        self.gridLayout_2.addWidget(self.label, 2, 0, 1, 1)

        self.label_2 = QLabel(export_preferences)
        self.label_2.setObjectName(u"label_2")
        font1 = QFont()
        font1.setPointSize(10)
        self.label_2.setFont(font1)

        self.gridLayout_2.addWidget(self.label_2, 3, 0, 1, 1)

        self.image_path = QLineEdit(export_preferences)
        self.image_path.setObjectName(u"image_path")

        self.gridLayout_2.addWidget(self.image_path, 4, 0, 1, 1)

        self.image_path_browse_button = QPushButton(export_preferences)
        self.image_path_browse_button.setObjectName(u"image_path_browse_button")

        self.gridLayout_2.addWidget(self.image_path_browse_button, 4, 1, 1, 1)

        self.line_3 = QFrame(export_preferences)
        self.line_3.setObjectName(u"line_3")
        self.line_3.setFrameShape(QFrame.Shape.HLine)
        self.line_3.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_2.addWidget(self.line_3, 5, 0, 1, 2)

        self.label_5 = QLabel(export_preferences)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setFont(font)

        self.gridLayout_2.addWidget(self.label_5, 6, 0, 1, 1)

        self.line_2 = QFrame(export_preferences)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_2.addWidget(self.line_2, 8, 0, 1, 2)

        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.metadata_iterations = QCheckBox(export_preferences)
        self.metadata_iterations.setObjectName(u"metadata_iterations")

        self.gridLayout.addWidget(self.metadata_iterations, 7, 0, 1, 1)

        self.metadata_model_branch = QCheckBox(export_preferences)
        self.metadata_model_branch.setObjectName(u"metadata_model_branch")

        self.gridLayout.addWidget(self.metadata_model_branch, 4, 1, 1, 1)

        self.metadata_seed = QCheckBox(export_preferences)
        self.metadata_seed.setObjectName(u"metadata_seed")

        self.gridLayout.addWidget(self.metadata_seed, 5, 0, 1, 1)

        self.metadata_model = QCheckBox(export_preferences)
        self.metadata_model.setObjectName(u"metadata_model")

        self.gridLayout.addWidget(self.metadata_model, 3, 1, 1, 1)

        self.label_3 = QLabel(export_preferences)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setFont(font)

        self.gridLayout.addWidget(self.label_3, 0, 0, 1, 1)

        self.metadata_scheduler = QCheckBox(export_preferences)
        self.metadata_scheduler.setObjectName(u"metadata_scheduler")

        self.gridLayout.addWidget(self.metadata_scheduler, 5, 1, 1, 1)

        self.export_metadata = QCheckBox(export_preferences)
        self.export_metadata.setObjectName(u"export_metadata")

        self.gridLayout.addWidget(self.export_metadata, 0, 1, 1, 1)

        self.metadata_samples = QCheckBox(export_preferences)
        self.metadata_samples.setObjectName(u"metadata_samples")

        self.gridLayout.addWidget(self.metadata_samples, 2, 1, 1, 1)

        self.verticalSpacer = QSpacerItem(17, 37, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 8, 0, 1, 1)

        self.metadata_scale = QCheckBox(export_preferences)
        self.metadata_scale.setObjectName(u"metadata_scale")

        self.gridLayout.addWidget(self.metadata_scale, 4, 0, 1, 1)

        self.metadata_negative_prompt = QCheckBox(export_preferences)
        self.metadata_negative_prompt.setObjectName(u"metadata_negative_prompt")

        self.gridLayout.addWidget(self.metadata_negative_prompt, 3, 0, 1, 1)

        self.metadata_ddim_eta = QCheckBox(export_preferences)
        self.metadata_ddim_eta.setObjectName(u"metadata_ddim_eta")

        self.gridLayout.addWidget(self.metadata_ddim_eta, 6, 1, 1, 1)

        self.metadata_prompt = QCheckBox(export_preferences)
        self.metadata_prompt.setObjectName(u"metadata_prompt")

        self.gridLayout.addWidget(self.metadata_prompt, 2, 0, 1, 1)

        self.metadata_steps = QCheckBox(export_preferences)
        self.metadata_steps.setObjectName(u"metadata_steps")

        self.gridLayout.addWidget(self.metadata_steps, 6, 0, 1, 1)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer, 0, 2, 1, 1)

        self.metadata_clip_skip = QCheckBox(export_preferences)
        self.metadata_clip_skip.setObjectName(u"metadata_clip_skip")

        self.gridLayout.addWidget(self.metadata_clip_skip, 2, 2, 1, 1)

        self.metadata_version = QCheckBox(export_preferences)
        self.metadata_version.setObjectName(u"metadata_version")

        self.gridLayout.addWidget(self.metadata_version, 3, 2, 1, 1)

        self.metadata_lora = QCheckBox(export_preferences)
        self.metadata_lora.setObjectName(u"metadata_lora")

        self.gridLayout.addWidget(self.metadata_lora, 4, 2, 1, 1)

        self.metadata_embeddings = QCheckBox(export_preferences)
        self.metadata_embeddings.setObjectName(u"metadata_embeddings")

        self.gridLayout.addWidget(self.metadata_embeddings, 5, 2, 1, 1)

        self.metadata_timestamp = QCheckBox(export_preferences)
        self.metadata_timestamp.setObjectName(u"metadata_timestamp")

        self.gridLayout.addWidget(self.metadata_timestamp, 6, 2, 1, 1)

        self.metadata_strength = QCheckBox(export_preferences)
        self.metadata_strength.setObjectName(u"metadata_strength")

        self.gridLayout.addWidget(self.metadata_strength, 7, 1, 1, 1)

        self.metadata_controlnet = QCheckBox(export_preferences)
        self.metadata_controlnet.setObjectName(u"metadata_controlnet")

        self.gridLayout.addWidget(self.metadata_controlnet, 7, 2, 1, 1)

        self.label_4 = QLabel(export_preferences)
        self.label_4.setObjectName(u"label_4")
        font2 = QFont()
        font2.setPointSize(10)
        font2.setBold(True)
        self.label_4.setFont(font2)

        self.gridLayout.addWidget(self.label_4, 1, 0, 1, 3)


        self.gridLayout_2.addLayout(self.gridLayout, 9, 0, 1, 2)

        self.image_type_dropdown = QComboBox(export_preferences)
        self.image_type_dropdown.setObjectName(u"image_type_dropdown")

        self.gridLayout_2.addWidget(self.image_type_dropdown, 7, 0, 1, 2)


        self.retranslateUi(export_preferences)
        self.actionAuto_export_images.toggled.connect(export_preferences.action_toggle_automatically_export_images)
        self.image_path.textEdited.connect(export_preferences.image_export_path_text_edited)
        self.image_path_browse_button.clicked.connect(export_preferences.action_clicked_button_browse)
        self.image_type_dropdown.currentTextChanged.connect(export_preferences.action_image_type_text_changed)
        self.export_metadata.toggled.connect(export_preferences.action_toggled_export_metadata)
        self.metadata_prompt.toggled.connect(export_preferences.action_toggled_prompt)
        self.metadata_negative_prompt.toggled.connect(export_preferences.action_toggled_negative_prompt)
        self.metadata_scale.toggled.connect(export_preferences.action_toggled_scale)
        self.metadata_seed.toggled.connect(export_preferences.action_toggled_seed)
        self.metadata_steps.toggled.connect(export_preferences.action_toggled_steps)
        self.metadata_iterations.toggled.connect(export_preferences.action_toggled_iterations)
        self.metadata_samples.toggled.connect(export_preferences.action_toggled_samples)
        self.metadata_model.toggled.connect(export_preferences.action_toggled_model)
        self.metadata_model_branch.toggled.connect(export_preferences.action_toggled_model_branch)
        self.metadata_scheduler.toggled.connect(export_preferences.action_toggled_scheduler)
        self.metadata_ddim_eta.toggled.connect(export_preferences.action_toggled_ddim)
        self.metadata_strength.toggled.connect(export_preferences.action_toggled_strength)
        self.metadata_clip_skip.toggled.connect(export_preferences.action_toggled_clip_skip)
        self.metadata_version.toggled.connect(export_preferences.action_toggled_version)
        self.metadata_lora.toggled.connect(export_preferences.action_toggled_lora)
        self.metadata_embeddings.toggled.connect(export_preferences.action_toggled_embeddings)
        self.metadata_timestamp.toggled.connect(export_preferences.action_toggled_timestamp)
        self.metadata_controlnet.toggled.connect(export_preferences.action_toggled_controlnet)

        QMetaObject.connectSlotsByName(export_preferences)
    # setupUi

    def retranslateUi(self, export_preferences):
        export_preferences.setWindowTitle(QCoreApplication.translate("export_preferences", u"Form", None))
        self.actionAuto_export_images.setText(QCoreApplication.translate("export_preferences", u"Automatically export images", None))
        self.label.setText(QCoreApplication.translate("export_preferences", u"Image export folder", None))
        self.label_2.setText(QCoreApplication.translate("export_preferences", u"Folder to auto export images to", None))
        self.image_path_browse_button.setText(QCoreApplication.translate("export_preferences", u"Browse", None))
        self.label_5.setText(QCoreApplication.translate("export_preferences", u"Image type", None))
        self.metadata_iterations.setText(QCoreApplication.translate("export_preferences", u"Iterations", None))
        self.metadata_model_branch.setText(QCoreApplication.translate("export_preferences", u"Model Branch", None))
        self.metadata_seed.setText(QCoreApplication.translate("export_preferences", u"Seed", None))
        self.metadata_model.setText(QCoreApplication.translate("export_preferences", u"Model", None))
        self.label_3.setText(QCoreApplication.translate("export_preferences", u"Metadata", None))
        self.metadata_scheduler.setText(QCoreApplication.translate("export_preferences", u"Scheduler", None))
#if QT_CONFIG(tooltip)
        self.export_metadata.setToolTip(QCoreApplication.translate("export_preferences", u"<html><head/><body><p>Export metadata along with images. </p><p>Only works with PNG files.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.export_metadata.setText(QCoreApplication.translate("export_preferences", u"Export metadata", None))
        self.metadata_samples.setText(QCoreApplication.translate("export_preferences", u"Samples", None))
        self.metadata_scale.setText(QCoreApplication.translate("export_preferences", u"Scale", None))
        self.metadata_negative_prompt.setText(QCoreApplication.translate("export_preferences", u"Negative prompt", None))
        self.metadata_ddim_eta.setText(QCoreApplication.translate("export_preferences", u"DDIM ETA", None))
        self.metadata_prompt.setText(QCoreApplication.translate("export_preferences", u"Prompt", None))
        self.metadata_steps.setText(QCoreApplication.translate("export_preferences", u"Steps", None))
        self.metadata_clip_skip.setText(QCoreApplication.translate("export_preferences", u"Clip Skip", None))
        self.metadata_version.setText(QCoreApplication.translate("export_preferences", u"Version", None))
        self.metadata_lora.setText(QCoreApplication.translate("export_preferences", u"LoRA", None))
        self.metadata_embeddings.setText(QCoreApplication.translate("export_preferences", u"Embeddings", None))
        self.metadata_timestamp.setText(QCoreApplication.translate("export_preferences", u"Timestamp", None))
        self.metadata_strength.setText(QCoreApplication.translate("export_preferences", u"Strength", None))
        self.metadata_controlnet.setText(QCoreApplication.translate("export_preferences", u"Controlnet", None))
        self.label_4.setText(QCoreApplication.translate("export_preferences", u"Choose which metadata to include with exported images", None))
    # retranslateUi

