# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'model_merger_model.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QDoubleSpinBox, QGridLayout,
    QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QSlider, QSpacerItem, QWidget)

class Ui_model_merger_model(object):
    def setupUi(self, model_merger_model):
        if not model_merger_model.objectName():
            model_merger_model.setObjectName(u"model_merger_model")
        model_merger_model.resize(335, 279)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(model_merger_model.sizePolicy().hasHeightForWidth())
        model_merger_model.setSizePolicy(sizePolicy)
        model_merger_model.setMinimumSize(QSize(0, 100))
        self.gridLayout = QGridLayout(model_merger_model)
        self.gridLayout.setObjectName(u"gridLayout")
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 9, 0, 1, 1)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.text_encoder_weight_slider = QSlider(model_merger_model)
        self.text_encoder_weight_slider.setObjectName(u"text_encoder_weight_slider")
        self.text_encoder_weight_slider.setMaximum(100)
        self.text_encoder_weight_slider.setOrientation(Qt.Horizontal)

        self.horizontalLayout_3.addWidget(self.text_encoder_weight_slider)

        self.text_encoder_weight_spinbox = QDoubleSpinBox(model_merger_model)
        self.text_encoder_weight_spinbox.setObjectName(u"text_encoder_weight_spinbox")
        self.text_encoder_weight_spinbox.setMaximum(1.000000000000000)

        self.horizontalLayout_3.addWidget(self.text_encoder_weight_spinbox)


        self.gridLayout.addLayout(self.horizontalLayout_3, 7, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.vae_weight_slider = QSlider(model_merger_model)
        self.vae_weight_slider.setObjectName(u"vae_weight_slider")
        self.vae_weight_slider.setMaximum(100)
        self.vae_weight_slider.setOrientation(Qt.Horizontal)

        self.horizontalLayout.addWidget(self.vae_weight_slider)

        self.vae_weight_spinbox = QDoubleSpinBox(model_merger_model)
        self.vae_weight_spinbox.setObjectName(u"vae_weight_spinbox")
        self.vae_weight_spinbox.setMaximum(1.000000000000000)

        self.horizontalLayout.addWidget(self.vae_weight_spinbox)


        self.gridLayout.addLayout(self.horizontalLayout, 3, 0, 1, 1)

        self.model_label = QLabel(model_merger_model)
        self.model_label.setObjectName(u"model_label")
        font = QFont()
        font.setBold(True)
        self.model_label.setFont(font)

        self.gridLayout.addWidget(self.model_label, 0, 0, 1, 1)

        self.models = QComboBox(model_merger_model)
        self.models.setObjectName(u"models")

        self.gridLayout.addWidget(self.models, 1, 0, 1, 1)

        self.model_delete_button = QPushButton(model_merger_model)
        self.model_delete_button.setObjectName(u"model_delete_button")

        self.gridLayout.addWidget(self.model_delete_button, 8, 0, 1, 1)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.unet_weight_slider = QSlider(model_merger_model)
        self.unet_weight_slider.setObjectName(u"unet_weight_slider")
        self.unet_weight_slider.setMaximum(100)
        self.unet_weight_slider.setOrientation(Qt.Horizontal)

        self.horizontalLayout_2.addWidget(self.unet_weight_slider)

        self.unet_weight_spinbox = QDoubleSpinBox(model_merger_model)
        self.unet_weight_spinbox.setObjectName(u"unet_weight_spinbox")
        self.unet_weight_spinbox.setMaximum(1.000000000000000)

        self.horizontalLayout_2.addWidget(self.unet_weight_spinbox)


        self.gridLayout.addLayout(self.horizontalLayout_2, 5, 0, 1, 1)

        self.label_2 = QLabel(model_merger_model)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setFont(font)

        self.gridLayout.addWidget(self.label_2, 4, 0, 1, 1)

        self.label = QLabel(model_merger_model)
        self.label.setObjectName(u"label")
        self.label.setFont(font)

        self.gridLayout.addWidget(self.label, 2, 0, 1, 1)

        self.label_3 = QLabel(model_merger_model)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setFont(font)

        self.gridLayout.addWidget(self.label_3, 6, 0, 1, 1)


        self.retranslateUi(model_merger_model)

        QMetaObject.connectSlotsByName(model_merger_model)
    # setupUi

    def retranslateUi(self, model_merger_model):
        model_merger_model.setWindowTitle(QCoreApplication.translate("model_merger_model", u"Form", None))
        self.model_label.setText(QCoreApplication.translate("model_merger_model", u"Model", None))
        self.model_delete_button.setText(QCoreApplication.translate("model_merger_model", u"Remove Model", None))
        self.label_2.setText(QCoreApplication.translate("model_merger_model", u"Unet weight", None))
        self.label.setText(QCoreApplication.translate("model_merger_model", u"Vae weight", None))
        self.label_3.setText(QCoreApplication.translate("model_merger_model", u"Text Encoder Weight", None))
    # retranslateUi

