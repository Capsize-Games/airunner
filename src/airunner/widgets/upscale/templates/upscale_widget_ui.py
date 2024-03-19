# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'upscale_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGridLayout,
    QGroupBox, QHBoxLayout, QPushButton, QSizePolicy,
    QSpacerItem, QWidget)

class Ui_upscale_widget(object):
    def setupUi(self, upscale_widget):
        if not upscale_widget.objectName():
            upscale_widget.setObjectName(u"upscale_widget")
        upscale_widget.resize(408, 300)
        self.gridLayout = QGridLayout(upscale_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.groupBox = QGroupBox(upscale_widget)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout_2 = QGridLayout(self.groupBox)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.upscale_model_2 = QComboBox(self.groupBox)
        self.upscale_model_2.addItem("")
        self.upscale_model_2.addItem("")
        self.upscale_model_2.addItem("")
        self.upscale_model_2.addItem("")
        self.upscale_model_2.addItem("")
        self.upscale_model_2.addItem("")
        self.upscale_model_2.setObjectName(u"upscale_model_2")

        self.horizontalLayout_8.addWidget(self.upscale_model_2)

        self.face_enhance_2 = QCheckBox(self.groupBox)
        self.face_enhance_2.setObjectName(u"face_enhance_2")

        self.horizontalLayout_8.addWidget(self.face_enhance_2)


        self.gridLayout_2.addLayout(self.horizontalLayout_8, 0, 0, 1, 1)

        self.horizontalLayout_9 = QHBoxLayout()
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.comboBox_2 = QComboBox(self.groupBox)
        self.comboBox_2.addItem("")
        self.comboBox_2.addItem("")
        self.comboBox_2.setObjectName(u"comboBox_2")

        self.horizontalLayout_9.addWidget(self.comboBox_2)

        self.upscale_2x_2 = QPushButton(self.groupBox)
        self.upscale_2x_2.setObjectName(u"upscale_2x_2")
        self.upscale_2x_2.setCursor(QCursor(Qt.PointingHandCursor))

        self.horizontalLayout_9.addWidget(self.upscale_2x_2)


        self.gridLayout_2.addLayout(self.horizontalLayout_9, 1, 0, 1, 1)

        self.verticalSpacer_3 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer_3, 2, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)


        self.retranslateUi(upscale_widget)
        self.comboBox_2.currentTextChanged.connect(upscale_widget.upscale_amount_changed)
        self.upscale_2x_2.clicked.connect(upscale_widget.upscale_clicked)
        self.upscale_model_2.currentTextChanged.connect(upscale_widget.model_changed)
        self.face_enhance_2.toggled.connect(upscale_widget.face_enhance_toggled)

        QMetaObject.connectSlotsByName(upscale_widget)
    # setupUi

    def retranslateUi(self, upscale_widget):
        upscale_widget.setWindowTitle(QCoreApplication.translate("upscale_widget", u"Form", None))
        self.groupBox.setTitle(QCoreApplication.translate("upscale_widget", u"Upscale", None))
        self.upscale_model_2.setItemText(0, QCoreApplication.translate("upscale_widget", u"RealESRGAN_x4plus", None))
        self.upscale_model_2.setItemText(1, QCoreApplication.translate("upscale_widget", u"RealESRNet_x4plus", None))
        self.upscale_model_2.setItemText(2, QCoreApplication.translate("upscale_widget", u"RealESRGAN_x4plus_anime_6B", None))
        self.upscale_model_2.setItemText(3, QCoreApplication.translate("upscale_widget", u"RealESRGAN_x2plus", None))
        self.upscale_model_2.setItemText(4, QCoreApplication.translate("upscale_widget", u"realesr-animevideov3", None))
        self.upscale_model_2.setItemText(5, QCoreApplication.translate("upscale_widget", u"realesr-general-x4v3", None))

        self.face_enhance_2.setText(QCoreApplication.translate("upscale_widget", u"Face enhance", None))
        self.comboBox_2.setItemText(0, QCoreApplication.translate("upscale_widget", u"2x", None))
        self.comboBox_2.setItemText(1, QCoreApplication.translate("upscale_widget", u"4x", None))

        self.upscale_2x_2.setText(QCoreApplication.translate("upscale_widget", u"Upscale", None))
    # retranslateUi

