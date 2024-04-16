# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'confirmation_page.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QGridLayout,
    QGroupBox, QLabel, QScrollArea, QSizePolicy,
    QSpacerItem, QWidget)

class Ui_confirmation_page(object):
    def setupUi(self, confirmation_page):
        if not confirmation_page.objectName():
            confirmation_page.setObjectName(u"confirmation_page")
        confirmation_page.resize(468, 521)
        self.gridLayout_2 = QGridLayout(confirmation_page)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.scrollArea = QScrollArea(confirmation_page)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 448, 501))
        self.gridLayout = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout.setObjectName(u"gridLayout")
        self.download_llm_checkbox = QCheckBox(self.scrollAreaWidgetContents)
        self.download_llm_checkbox.setObjectName(u"download_llm_checkbox")

        self.gridLayout.addWidget(self.download_llm_checkbox, 8, 0, 1, 1)

        self.compile_with_pyinstaller_checkbox = QCheckBox(self.scrollAreaWidgetContents)
        self.compile_with_pyinstaller_checkbox.setObjectName(u"compile_with_pyinstaller_checkbox")

        self.gridLayout.addWidget(self.compile_with_pyinstaller_checkbox, 2, 0, 1, 1)

        self.download_controlnet_checkbox = QCheckBox(self.scrollAreaWidgetContents)
        self.download_controlnet_checkbox.setObjectName(u"download_controlnet_checkbox")

        self.gridLayout.addWidget(self.download_controlnet_checkbox, 7, 0, 1, 1)

        self.line_2 = QFrame(self.scrollAreaWidgetContents)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line_2, 1, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 12, 0, 1, 1)

        self.download_sd_checkbox = QCheckBox(self.scrollAreaWidgetContents)
        self.download_sd_checkbox.setObjectName(u"download_sd_checkbox")

        self.gridLayout.addWidget(self.download_sd_checkbox, 6, 0, 1, 1)

        self.required_libraries_groupbox = QGroupBox(self.scrollAreaWidgetContents)
        self.required_libraries_groupbox.setObjectName(u"required_libraries_groupbox")
        self.required_libraries_groupbox.setCheckable(True)
        self.required_libraries_groupbox.setChecked(True)
        self.gridLayout_3 = QGridLayout(self.required_libraries_groupbox)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.required_libraries = QScrollArea(self.required_libraries_groupbox)
        self.required_libraries.setObjectName(u"required_libraries")
        self.required_libraries.setWidgetResizable(True)
        self.scrollAreaWidgetContents_2 = QWidget()
        self.scrollAreaWidgetContents_2.setObjectName(u"scrollAreaWidgetContents_2")
        self.scrollAreaWidgetContents_2.setGeometry(QRect(0, 0, 404, 128))
        self.gridLayout_4 = QGridLayout(self.scrollAreaWidgetContents_2)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.required_libraries.setWidget(self.scrollAreaWidgetContents_2)

        self.gridLayout_3.addWidget(self.required_libraries, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.required_libraries_groupbox, 3, 0, 1, 1)

        self.line = QFrame(self.scrollAreaWidgetContents)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 4, 0, 1, 1)

        self.download_ai_runner_checkbox = QCheckBox(self.scrollAreaWidgetContents)
        self.download_ai_runner_checkbox.setObjectName(u"download_ai_runner_checkbox")

        self.gridLayout.addWidget(self.download_ai_runner_checkbox, 5, 0, 1, 1)

        self.download_stt_checkbox = QCheckBox(self.scrollAreaWidgetContents)
        self.download_stt_checkbox.setObjectName(u"download_stt_checkbox")

        self.gridLayout.addWidget(self.download_stt_checkbox, 10, 0, 1, 1)

        self.label = QLabel(self.scrollAreaWidgetContents)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        self.label.setFont(font)
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.download_tts_checkbox = QCheckBox(self.scrollAreaWidgetContents)
        self.download_tts_checkbox.setObjectName(u"download_tts_checkbox")

        self.gridLayout.addWidget(self.download_tts_checkbox, 9, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_2.addWidget(self.scrollArea, 0, 0, 1, 1)


        self.retranslateUi(confirmation_page)
        self.download_ai_runner_checkbox.toggled.connect(confirmation_page.toggle_download_ai_runner)
        self.download_sd_checkbox.toggled.connect(confirmation_page.toggle_download_sd)
        self.download_controlnet_checkbox.toggled.connect(confirmation_page.toggle_download_controlnet)
        self.download_llm_checkbox.toggled.connect(confirmation_page.toggle_download_llm)
        self.download_tts_checkbox.toggled.connect(confirmation_page.toggle_download_tts)
        self.download_stt_checkbox.toggled.connect(confirmation_page.toggle_download_stt)
        self.required_libraries_groupbox.toggled.connect(confirmation_page.toggle_all_required)
        self.compile_with_pyinstaller_checkbox.toggled.connect(confirmation_page.toggle_compile_with_pyinstaller)

        QMetaObject.connectSlotsByName(confirmation_page)
    # setupUi

    def retranslateUi(self, confirmation_page):
        confirmation_page.setWindowTitle(QCoreApplication.translate("confirmation_page", u"Form", None))
        self.download_llm_checkbox.setText(QCoreApplication.translate("confirmation_page", u"Download LLM", None))
        self.compile_with_pyinstaller_checkbox.setText(QCoreApplication.translate("confirmation_page", u"Compile with Pyinstaller", None))
        self.download_controlnet_checkbox.setText(QCoreApplication.translate("confirmation_page", u"Download Controlnet models", None))
        self.download_sd_checkbox.setText(QCoreApplication.translate("confirmation_page", u"Download Stable Diffusion models", None))
        self.required_libraries_groupbox.setTitle(QCoreApplication.translate("confirmation_page", u"Install required libraries (linux)", None))
        self.download_ai_runner_checkbox.setText(QCoreApplication.translate("confirmation_page", u"Download AI Runner", None))
        self.download_stt_checkbox.setText(QCoreApplication.translate("confirmation_page", u"Download Speech to Text models", None))
        self.label.setText(QCoreApplication.translate("confirmation_page", u"Confirm your settings and click next to install AI Runner", None))
        self.download_tts_checkbox.setText(QCoreApplication.translate("confirmation_page", u"Download Text to Speech models", None))
    # retranslateUi

