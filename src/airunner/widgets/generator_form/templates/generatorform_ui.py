# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'generatorform.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QPlainTextEdit, QProgressBar, QPushButton,
    QScrollArea, QSizePolicy, QSpacerItem, QSplitter,
    QTabWidget, QVBoxLayout, QWidget)

from airunner.widgets.llm.chat_prompt_widget import ChatPromptWidget
import airunner.resources_light_rc
import airunner.resources_dark_rc

class Ui_generator_form(object):
    def setupUi(self, generator_form):
        if not generator_form.objectName():
            generator_form.setObjectName(u"generator_form")
        generator_form.resize(361, 946)
        font = QFont()
        font.setPointSize(8)
        generator_form.setFont(font)
        generator_form.setCursor(QCursor(Qt.PointingHandCursor))
        self.gridLayout_4 = QGridLayout(generator_form)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.gridLayout_4.setContentsMargins(0, 0, 0, 0)
        self.generator_form_tabs = QTabWidget(generator_form)
        self.generator_form_tabs.setObjectName(u"generator_form_tabs")
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.gridLayout_3 = QGridLayout(self.tab)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setContentsMargins(8, 8, 8, 8)
        self.generate_button = QPushButton(self.tab)
        self.generate_button.setObjectName(u"generate_button")

        self.gridLayout_3.addWidget(self.generate_button, 1, 0, 1, 1)

        self.progress_bar = QProgressBar(self.tab)
        self.progress_bar.setObjectName(u"progress_bar")
        self.progress_bar.setValue(0)

        self.gridLayout_3.addWidget(self.progress_bar, 3, 0, 1, 1)

        self.scrollArea = QScrollArea(self.tab)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setFrameShape(QFrame.NoFrame)
        self.scrollArea.setFrameShadow(QFrame.Plain)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 341, 824))
        self.gridLayout = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.splitter = QSplitter(self.scrollAreaWidgetContents)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Vertical)
        self.layoutWidget = QWidget(self.splitter)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.gridLayout_2 = QGridLayout(self.layoutWidget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_6.addItem(self.horizontalSpacer)

        self.pushButton = QPushButton(self.layoutWidget)
        self.pushButton.setObjectName(u"pushButton")

        self.horizontalLayout_6.addWidget(self.pushButton)


        self.gridLayout_2.addLayout(self.horizontalLayout_6, 0, 1, 1, 1)

        self.label = QLabel(self.layoutWidget)
        self.label.setObjectName(u"label")
        font1 = QFont()
        font1.setPointSize(8)
        font1.setBold(True)
        self.label.setFont(font1)

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)

        self.prompt = QPlainTextEdit(self.layoutWidget)
        self.prompt.setObjectName(u"prompt")

        self.gridLayout_2.addWidget(self.prompt, 1, 0, 1, 2)

        self.splitter.addWidget(self.layoutWidget)
        self.layoutWidget1 = QWidget(self.splitter)
        self.layoutWidget1.setObjectName(u"layoutWidget1")
        self.verticalLayout_6 = QVBoxLayout(self.layoutWidget1)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.label_2 = QLabel(self.layoutWidget1)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setFont(font1)

        self.verticalLayout_6.addWidget(self.label_2)

        self.negative_prompt = QPlainTextEdit(self.layoutWidget1)
        self.negative_prompt.setObjectName(u"negative_prompt")

        self.verticalLayout_6.addWidget(self.negative_prompt)

        self.splitter.addWidget(self.layoutWidget1)

        self.gridLayout.addWidget(self.splitter, 0, 1, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_3.addWidget(self.scrollArea, 0, 0, 1, 1)

        self.interrupt_button = QPushButton(self.tab)
        self.interrupt_button.setObjectName(u"interrupt_button")
        self.interrupt_button.setCursor(QCursor(Qt.PointingHandCursor))

        self.gridLayout_3.addWidget(self.interrupt_button, 2, 0, 1, 1)

        self.generator_form_tabs.addTab(self.tab, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        self.gridLayout_5 = QGridLayout(self.tab_2)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.gridLayout_5.setContentsMargins(0, 0, 0, 0)
        self.chat_prompt_widget = ChatPromptWidget(self.tab_2)
        self.chat_prompt_widget.setObjectName(u"chat_prompt_widget")

        self.gridLayout_5.addWidget(self.chat_prompt_widget, 0, 0, 1, 1)

        self.generator_form_tabs.addTab(self.tab_2, "")

        self.gridLayout_4.addWidget(self.generator_form_tabs, 0, 0, 1, 1)


        self.retranslateUi(generator_form)
        self.pushButton.clicked.connect(generator_form.action_clicked_button_save_prompts)
        self.interrupt_button.clicked.connect(generator_form.handle_interrupt_button_clicked)
        self.generate_button.clicked.connect(generator_form.handle_generate_button_clicked)
        self.prompt.textChanged.connect(generator_form.handle_prompt_changed)
        self.negative_prompt.textChanged.connect(generator_form.handle_negative_prompt_changed)

        self.generator_form_tabs.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(generator_form)
    # setupUi

    def retranslateUi(self, generator_form):
        generator_form.setWindowTitle(QCoreApplication.translate("generator_form", u"Form", None))
        self.generate_button.setText(QCoreApplication.translate("generator_form", u"Generate", None))
        self.pushButton.setText(QCoreApplication.translate("generator_form", u"Save Prompts", None))
        self.label.setText(QCoreApplication.translate("generator_form", u"Prompt", None))
        self.prompt.setPlaceholderText(QCoreApplication.translate("generator_form", u"Enter a prompt...", None))
        self.label_2.setText(QCoreApplication.translate("generator_form", u"Negative Prompt", None))
        self.negative_prompt.setPlaceholderText(QCoreApplication.translate("generator_form", u"Enter a negative prompt...", None))
        self.interrupt_button.setText(QCoreApplication.translate("generator_form", u"Interrupt", None))
        self.generator_form_tabs.setTabText(self.generator_form_tabs.indexOf(self.tab), QCoreApplication.translate("generator_form", u"Tab 1", None))
        self.generator_form_tabs.setTabText(self.generator_form_tabs.indexOf(self.tab_2), QCoreApplication.translate("generator_form", u"Tab 2", None))
    # retranslateUi

