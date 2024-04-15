# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'model_setup.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QGridLayout, QLabel,
    QScrollArea, QSizePolicy, QSpacerItem, QWidget)

class Ui_model_setup_page(object):
    def setupUi(self, model_setup_page):
        if not model_setup_page.objectName():
            model_setup_page.setObjectName(u"model_setup_page")
        model_setup_page.resize(530, 546)
        self.gridLayout = QGridLayout(model_setup_page)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_2 = QLabel(model_setup_page)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setWordWrap(True)

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.label = QLabel(model_setup_page)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.scrollArea = QScrollArea(model_setup_page)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 510, 475))
        self.gridLayout_2 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer_2, 7, 0, 1, 1)

        self.checkBox_3 = QCheckBox(self.scrollAreaWidgetContents)
        self.checkBox_3.setObjectName(u"checkBox_3")
        font1 = QFont()
        font1.setBold(True)
        self.checkBox_3.setFont(font1)
        self.checkBox_3.setChecked(True)

        self.gridLayout_2.addWidget(self.checkBox_3, 4, 0, 1, 1)

        self.checkBox = QCheckBox(self.scrollAreaWidgetContents)
        self.checkBox.setObjectName(u"checkBox")
        font2 = QFont()
        font2.setPointSize(10)
        font2.setBold(True)
        self.checkBox.setFont(font2)
        self.checkBox.setChecked(True)

        self.gridLayout_2.addWidget(self.checkBox, 3, 0, 1, 1)

        self.checkBox_5 = QCheckBox(self.scrollAreaWidgetContents)
        self.checkBox_5.setObjectName(u"checkBox_5")
        self.checkBox_5.setFont(font1)
        self.checkBox_5.setChecked(True)

        self.gridLayout_2.addWidget(self.checkBox_5, 6, 0, 1, 1)

        self.checkBox_4 = QCheckBox(self.scrollAreaWidgetContents)
        self.checkBox_4.setObjectName(u"checkBox_4")
        self.checkBox_4.setFont(font1)
        self.checkBox_4.setChecked(True)

        self.gridLayout_2.addWidget(self.checkBox_4, 5, 0, 1, 1)

        self.checkBox_2 = QCheckBox(self.scrollAreaWidgetContents)
        self.checkBox_2.setObjectName(u"checkBox_2")
        self.checkBox_2.setFont(font2)
        self.checkBox_2.setChecked(True)

        self.gridLayout_2.addWidget(self.checkBox_2, 2, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout.addWidget(self.scrollArea, 2, 0, 1, 1)


        self.retranslateUi(model_setup_page)
        self.checkBox_2.toggled.connect(model_setup_page.toggle_download_sd_models)
        self.checkBox.toggled.connect(model_setup_page.toggle_download_controlnet_models)
        self.checkBox_3.toggled.connect(model_setup_page.toggle_download_llms)
        self.checkBox_4.toggled.connect(model_setup_page.toggle_download_tts_models)
        self.checkBox_5.toggled.connect(model_setup_page.toggle_download_stt_models)

        QMetaObject.connectSlotsByName(model_setup_page)
    # setupUi

    def retranslateUi(self, model_setup_page):
        model_setup_page.setWindowTitle(QCoreApplication.translate("model_setup_page", u"Form", None))
        self.label_2.setText(QCoreApplication.translate("model_setup_page", u"Choose which models to download. Options will be presented on subsequent screens.", None))
        self.label.setText(QCoreApplication.translate("model_setup_page", u"Model Setup", None))
        self.checkBox_3.setText(QCoreApplication.translate("model_setup_page", u"Large language models", None))
        self.checkBox.setText(QCoreApplication.translate("model_setup_page", u"Controlnet models", None))
        self.checkBox_5.setText(QCoreApplication.translate("model_setup_page", u"Speech-to-Text models", None))
        self.checkBox_4.setText(QCoreApplication.translate("model_setup_page", u"Text-to-Speech models", None))
        self.checkBox_2.setText(QCoreApplication.translate("model_setup_page", u"Stable Diffusion models", None))
    # retranslateUi

