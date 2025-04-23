# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'choose_models.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QScrollArea, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)

class Ui_install_success_page(object):
    def setupUi(self, install_success_page):
        if not install_success_page.objectName():
            install_success_page.setObjectName(u"install_success_page")
        install_success_page.resize(615, 853)
        self.gridLayout = QGridLayout(install_success_page)
        self.gridLayout.setObjectName(u"gridLayout")
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 8, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.page_title = QLabel(install_success_page)
        self.page_title.setObjectName(u"page_title")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.page_title.setFont(font)

        self.horizontalLayout.addWidget(self.page_title)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.total_size_label = QLabel(install_success_page)
        self.total_size_label.setObjectName(u"total_size_label")

        self.horizontalLayout.addWidget(self.total_size_label)


        self.gridLayout.addLayout(self.horizontalLayout, 1, 0, 1, 1)

        self.groupBox = QGroupBox(install_success_page)
        self.groupBox.setObjectName(u"groupBox")
        font1 = QFont()
        font1.setBold(True)
        self.groupBox.setFont(font1)
        self.groupBox.setCheckable(True)
        self.gridLayout_2 = QGridLayout(self.groupBox)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.stable_diffusion_scrollarea = QScrollArea(self.groupBox)
        self.stable_diffusion_scrollarea.setObjectName(u"stable_diffusion_scrollarea")
        self.stable_diffusion_scrollarea.setWidgetResizable(True)
        self.stable_diffusion_layout = QWidget()
        self.stable_diffusion_layout.setObjectName(u"stable_diffusion_layout")
        self.stable_diffusion_layout.setGeometry(QRect(0, 0, 571, 294))
        self.verticalLayout = QVBoxLayout(self.stable_diffusion_layout)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.stable_diffusion_scrollarea.setWidget(self.stable_diffusion_layout)

        self.gridLayout_2.addWidget(self.stable_diffusion_scrollarea, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox, 2, 0, 1, 1)

        self.speecht5_checkbox = QCheckBox(install_success_page)
        self.speecht5_checkbox.setObjectName(u"speecht5_checkbox")
        self.speecht5_checkbox.setChecked(True)

        self.gridLayout.addWidget(self.speecht5_checkbox, 5, 0, 1, 1)

        self.ministral_checkbox = QCheckBox(install_success_page)
        self.ministral_checkbox.setObjectName(u"ministral_checkbox")
        self.ministral_checkbox.setChecked(True)

        self.gridLayout.addWidget(self.ministral_checkbox, 3, 0, 1, 1)

        self.whisper_checkbox = QCheckBox(install_success_page)
        self.whisper_checkbox.setObjectName(u"whisper_checkbox")
        self.whisper_checkbox.setChecked(True)

        self.gridLayout.addWidget(self.whisper_checkbox, 6, 0, 1, 1)

        self.checkBox = QCheckBox(install_success_page)
        self.checkBox.setObjectName(u"checkBox")
        self.checkBox.setChecked(True)

        self.gridLayout.addWidget(self.checkBox, 4, 0, 1, 1)


        self.retranslateUi(install_success_page)
        self.ministral_checkbox.toggled.connect(install_success_page.ministral_toggled)
        self.speecht5_checkbox.toggled.connect(install_success_page.speecht5_toggled)
        self.whisper_checkbox.toggled.connect(install_success_page.whisper_toggled)
        self.groupBox.toggled.connect(install_success_page.stable_diffusion_toggled)
        self.checkBox.toggled.connect(install_success_page.embedding_model_toggled)

        QMetaObject.connectSlotsByName(install_success_page)
    # setupUi

    def retranslateUi(self, install_success_page):
        install_success_page.setWindowTitle(QCoreApplication.translate("install_success_page", u"Form", None))
        self.page_title.setText(QCoreApplication.translate("install_success_page", u"Choose models to download", None))
        self.total_size_label.setText(QCoreApplication.translate("install_success_page", u"0MB", None))
        self.groupBox.setTitle(QCoreApplication.translate("install_success_page", u"Stable Diffusion Controlnet", None))
        self.speecht5_checkbox.setText(QCoreApplication.translate("install_success_page", u"SpeechT5: Text-to-Speech", None))
        self.ministral_checkbox.setText(QCoreApplication.translate("install_success_page", u"Ministral 8B Instruct 4bit: Large Language Model (LLM)", None))
        self.whisper_checkbox.setText(QCoreApplication.translate("install_success_page", u"Whisper: Speech-to-Text (voice conversations)", None))
        self.checkBox.setText(QCoreApplication.translate("install_success_page", u"e5 Large: Embedding model (RAG search)", None))
    # retranslateUi

