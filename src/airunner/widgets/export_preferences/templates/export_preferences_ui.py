# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'export_preferences.ui'
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
    QGridLayout, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QSpacerItem, QWidget)

class Ui_export_preferences(object):
    def setupUi(self, export_preferences):
        if not export_preferences.objectName():
            export_preferences.setObjectName(u"export_preferences")
        export_preferences.resize(457, 429)
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
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)

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
        self.line_3.setFrameShape(QFrame.HLine)
        self.line_3.setFrameShadow(QFrame.Sunken)

        self.gridLayout_2.addWidget(self.line_3, 5, 0, 1, 2)

        self.label_5 = QLabel(export_preferences)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setFont(font)

        self.gridLayout_2.addWidget(self.label_5, 6, 0, 1, 1)

        self.line_2 = QFrame(export_preferences)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.HLine)
        self.line_2.setFrameShadow(QFrame.Sunken)

        self.gridLayout_2.addWidget(self.line_2, 8, 0, 1, 2)

        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_3 = QLabel(export_preferences)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setFont(font)

        self.gridLayout.addWidget(self.label_3, 0, 0, 1, 1)

        self.export_metadata = QCheckBox(export_preferences)
        self.export_metadata.setObjectName(u"export_metadata")

        self.gridLayout.addWidget(self.export_metadata, 0, 1, 1, 1)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer, 0, 3, 1, 1)

        self.label_4 = QLabel(export_preferences)
        self.label_4.setObjectName(u"label_4")
        font2 = QFont()
        font2.setPointSize(10)
        font2.setBold(True)
        self.label_4.setFont(font2)

        self.gridLayout.addWidget(self.label_4, 1, 0, 1, 2)

        self.metadata_prompt = QCheckBox(export_preferences)
        self.metadata_prompt.setObjectName(u"metadata_prompt")

        self.gridLayout.addWidget(self.metadata_prompt, 2, 0, 1, 1)

        self.metadata_samples = QCheckBox(export_preferences)
        self.metadata_samples.setObjectName(u"metadata_samples")

        self.gridLayout.addWidget(self.metadata_samples, 2, 1, 1, 1)

        self.metadata_negative_prompt = QCheckBox(export_preferences)
        self.metadata_negative_prompt.setObjectName(u"metadata_negative_prompt")

        self.gridLayout.addWidget(self.metadata_negative_prompt, 3, 0, 1, 1)

        self.metadata_model = QCheckBox(export_preferences)
        self.metadata_model.setObjectName(u"metadata_model")

        self.gridLayout.addWidget(self.metadata_model, 3, 1, 1, 1)

        self.metadata_scale = QCheckBox(export_preferences)
        self.metadata_scale.setObjectName(u"metadata_scale")

        self.gridLayout.addWidget(self.metadata_scale, 4, 0, 1, 1)

        self.metadata_model_branch = QCheckBox(export_preferences)
        self.metadata_model_branch.setObjectName(u"metadata_model_branch")

        self.gridLayout.addWidget(self.metadata_model_branch, 4, 1, 1, 1)

        self.metadata_seed = QCheckBox(export_preferences)
        self.metadata_seed.setObjectName(u"metadata_seed")

        self.gridLayout.addWidget(self.metadata_seed, 5, 0, 1, 1)

        self.metadata_scheduler = QCheckBox(export_preferences)
        self.metadata_scheduler.setObjectName(u"metadata_scheduler")

        self.gridLayout.addWidget(self.metadata_scheduler, 5, 1, 1, 1)

        self.metadata_steps = QCheckBox(export_preferences)
        self.metadata_steps.setObjectName(u"metadata_steps")

        self.gridLayout.addWidget(self.metadata_steps, 6, 0, 1, 1)

        self.metadata_ddim_eta = QCheckBox(export_preferences)
        self.metadata_ddim_eta.setObjectName(u"metadata_ddim_eta")

        self.gridLayout.addWidget(self.metadata_ddim_eta, 6, 1, 1, 1)

        self.metadata_iterations = QCheckBox(export_preferences)
        self.metadata_iterations.setObjectName(u"metadata_iterations")

        self.gridLayout.addWidget(self.metadata_iterations, 7, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(17, 37, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 8, 0, 1, 1)


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

        QMetaObject.connectSlotsByName(export_preferences)
    # setupUi

    def retranslateUi(self, export_preferences):
        export_preferences.setWindowTitle(QCoreApplication.translate("export_preferences", u"Form", None))
        self.actionAuto_export_images.setText(QCoreApplication.translate("export_preferences", u"Automatically export images", None))
        self.label.setText(QCoreApplication.translate("export_preferences", u"Image export folder", None))
        self.label_2.setText(QCoreApplication.translate("export_preferences", u"Folder to auto export images to", None))
        self.image_path_browse_button.setText(QCoreApplication.translate("export_preferences", u"Browse", None))
        self.label_5.setText(QCoreApplication.translate("export_preferences", u"Image type", None))
        self.label_3.setText(QCoreApplication.translate("export_preferences", u"Metadata", None))
#if QT_CONFIG(tooltip)
        self.export_metadata.setToolTip(QCoreApplication.translate("export_preferences", u"<html><head/><body><p>Export metadata along with images. </p><p>Only works with PNG files.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.export_metadata.setText(QCoreApplication.translate("export_preferences", u"Export metadata", None))
        self.label_4.setText(QCoreApplication.translate("export_preferences", u"Choose which metadata to include with exported images", None))
        self.metadata_prompt.setText(QCoreApplication.translate("export_preferences", u"Prompt", None))
        self.metadata_samples.setText(QCoreApplication.translate("export_preferences", u"Samples", None))
        self.metadata_negative_prompt.setText(QCoreApplication.translate("export_preferences", u"Negative prompt", None))
        self.metadata_model.setText(QCoreApplication.translate("export_preferences", u"Model", None))
        self.metadata_scale.setText(QCoreApplication.translate("export_preferences", u"Scale", None))
        self.metadata_model_branch.setText(QCoreApplication.translate("export_preferences", u"Model Branch", None))
        self.metadata_seed.setText(QCoreApplication.translate("export_preferences", u"Seed", None))
        self.metadata_scheduler.setText(QCoreApplication.translate("export_preferences", u"Scheduler", None))
        self.metadata_steps.setText(QCoreApplication.translate("export_preferences", u"Steps", None))
        self.metadata_ddim_eta.setText(QCoreApplication.translate("export_preferences", u"DDIM ETA", None))
        self.metadata_iterations.setText(QCoreApplication.translate("export_preferences", u"Iterations", None))
    # retranslateUi

