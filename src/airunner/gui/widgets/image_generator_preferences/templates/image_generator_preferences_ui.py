# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'image_generator_preferences.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QGroupBox,
    QLabel, QSizePolicy, QSpacerItem, QWidget)

from airunner.gui.widgets.stablediffusion.stable_diffusion_settings_widget import StableDiffusionSettingsWidget

class Ui_image_generator_preferences(object):
    def setupUi(self, image_generator_preferences):
        if not image_generator_preferences.objectName():
            image_generator_preferences.setObjectName(u"image_generator_preferences")
        image_generator_preferences.resize(496, 416)
        self.gridLayout = QGridLayout(image_generator_preferences)
        self.gridLayout.setObjectName(u"gridLayout")
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 1, 0, 1, 1)

        self.groupBox = QGroupBox(image_generator_preferences)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout_2 = QGridLayout(self.groupBox)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label_4 = QLabel(self.groupBox)
        self.label_4.setObjectName(u"label_4")

        self.gridLayout_2.addWidget(self.label_4, 7, 0, 1, 1)

        self.action = QComboBox(self.groupBox)
        self.action.setObjectName(u"action")

        self.gridLayout_2.addWidget(self.action, 8, 0, 1, 1)

        self.pipeline = QComboBox(self.groupBox)
        self.pipeline.setObjectName(u"pipeline")

        self.gridLayout_2.addWidget(self.pipeline, 4, 0, 1, 1)

        self.label = QLabel(self.groupBox)
        self.label.setObjectName(u"label")

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)

        self.label_2 = QLabel(self.groupBox)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout_2.addWidget(self.label_2, 3, 0, 1, 1)

        self.category = QComboBox(self.groupBox)
        self.category.setObjectName(u"category")

        self.gridLayout_2.addWidget(self.category, 1, 0, 1, 1)

        self.generator_form = StableDiffusionSettingsWidget(self.groupBox)
        self.generator_form.setObjectName(u"generator_form")

        self.gridLayout_2.addWidget(self.generator_form, 9, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)


        self.retranslateUi(image_generator_preferences)
        self.category.currentTextChanged.connect(image_generator_preferences.category_changed)
        self.pipeline.currentTextChanged.connect(image_generator_preferences.pipeline_changed)
        self.action.currentTextChanged.connect(image_generator_preferences.action_changed)

        QMetaObject.connectSlotsByName(image_generator_preferences)
    # setupUi

    def retranslateUi(self, image_generator_preferences):
        image_generator_preferences.setWindowTitle(QCoreApplication.translate("image_generator_preferences", u"Form", None))
        self.groupBox.setTitle("")
        self.label_4.setText(QCoreApplication.translate("image_generator_preferences", u"Action", None))
        self.label.setText(QCoreApplication.translate("image_generator_preferences", u"Category", None))
        self.label_2.setText(QCoreApplication.translate("image_generator_preferences", u"Pipeline", None))
    # retranslateUi

