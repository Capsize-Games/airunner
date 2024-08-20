# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'generatorform.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QPlainTextEdit, QProgressBar, QPushButton, QScrollArea,
    QSizePolicy, QSpacerItem, QSplitter, QTabWidget,
    QVBoxLayout, QWidget)

from airunner.widgets.llm.chat_prompt_widget import ChatPromptWidget
import airunner.resources_light_rc
import airunner.resources_dark_rc

class Ui_generator_form(object):
    def setupUi(self, generator_form):
        if not generator_form.objectName():
            generator_form.setObjectName(u"generator_form")
        generator_form.resize(665, 946)
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
        self.interrupt_button = QPushButton(self.tab)
        self.interrupt_button.setObjectName(u"interrupt_button")
        self.interrupt_button.setCursor(QCursor(Qt.PointingHandCursor))

        self.gridLayout_3.addWidget(self.interrupt_button, 11, 0, 1, 1)

        self.scrollArea = QScrollArea(self.tab)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setFrameShape(QFrame.Shape.NoFrame)
        self.scrollArea.setFrameShadow(QFrame.Shadow.Plain)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 645, 461))
        self.gridLayout = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.splitter = QSplitter(self.scrollAreaWidgetContents)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Vertical)
        self.layoutWidget = QWidget(self.splitter)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.gridLayout_2 = QGridLayout(self.layoutWidget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
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

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_6.addItem(self.horizontalSpacer)

        self.pushButton = QPushButton(self.layoutWidget)
        self.pushButton.setObjectName(u"pushButton")

        self.horizontalLayout_6.addWidget(self.pushButton)


        self.gridLayout_2.addLayout(self.horizontalLayout_6, 0, 1, 1, 1)

        self.secondary_prompt = QPlainTextEdit(self.layoutWidget)
        self.secondary_prompt.setObjectName(u"secondary_prompt")

        self.gridLayout_2.addWidget(self.secondary_prompt, 2, 0, 1, 2)

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

        self.secondary_negative_prompt = QPlainTextEdit(self.layoutWidget1)
        self.secondary_negative_prompt.setObjectName(u"secondary_negative_prompt")

        self.verticalLayout_6.addWidget(self.secondary_negative_prompt)

        self.splitter.addWidget(self.layoutWidget1)

        self.gridLayout.addWidget(self.splitter, 0, 1, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_3.addWidget(self.scrollArea, 1, 0, 1, 1)

        self.image_presets = QComboBox(self.tab)
        self.image_presets.setObjectName(u"image_presets")

        self.gridLayout_3.addWidget(self.image_presets, 0, 0, 1, 1)

        self.groupBox_2 = QGroupBox(self.tab)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.horizontalLayout_4 = QHBoxLayout(self.groupBox_2)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.original_size_x = QLineEdit(self.groupBox_2)
        self.original_size_x.setObjectName(u"original_size_x")

        self.horizontalLayout_4.addWidget(self.original_size_x)

        self.original_size_y = QLineEdit(self.groupBox_2)
        self.original_size_y.setObjectName(u"original_size_y")

        self.horizontalLayout_4.addWidget(self.original_size_y)


        self.gridLayout_3.addWidget(self.groupBox_2, 3, 0, 1, 1)

        self.groupBox_3 = QGroupBox(self.tab)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.horizontalLayout_5 = QHBoxLayout(self.groupBox_3)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.negative_original_size_x = QLineEdit(self.groupBox_3)
        self.negative_original_size_x.setObjectName(u"negative_original_size_x")

        self.horizontalLayout_5.addWidget(self.negative_original_size_x)

        self.negative_original_size_y = QLineEdit(self.groupBox_3)
        self.negative_original_size_y.setObjectName(u"negative_original_size_y")

        self.horizontalLayout_5.addWidget(self.negative_original_size_y)


        self.gridLayout_3.addWidget(self.groupBox_3, 5, 0, 1, 1)

        self.groupBox_4 = QGroupBox(self.tab)
        self.groupBox_4.setObjectName(u"groupBox_4")
        self.horizontalLayout = QHBoxLayout(self.groupBox_4)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.negative_target_size_x = QLineEdit(self.groupBox_4)
        self.negative_target_size_x.setObjectName(u"negative_target_size_x")

        self.horizontalLayout.addWidget(self.negative_target_size_x)

        self.negative_target_size_y = QLineEdit(self.groupBox_4)
        self.negative_target_size_y.setObjectName(u"negative_target_size_y")

        self.horizontalLayout.addWidget(self.negative_target_size_y)


        self.gridLayout_3.addWidget(self.groupBox_4, 6, 0, 1, 1)

        self.progress_bar = QProgressBar(self.tab)
        self.progress_bar.setObjectName(u"progress_bar")
        self.progress_bar.setValue(0)

        self.gridLayout_3.addWidget(self.progress_bar, 12, 0, 1, 1)

        self.generate_button = QPushButton(self.tab)
        self.generate_button.setObjectName(u"generate_button")

        self.gridLayout_3.addWidget(self.generate_button, 10, 0, 1, 1)

        self.groupBox = QGroupBox(self.tab)
        self.groupBox.setObjectName(u"groupBox")
        self.horizontalLayout_2 = QHBoxLayout(self.groupBox)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.crops_coord_top_left_x = QLineEdit(self.groupBox)
        self.crops_coord_top_left_x.setObjectName(u"crops_coord_top_left_x")

        self.horizontalLayout_2.addWidget(self.crops_coord_top_left_x)

        self.crops_coord_top_left_y = QLineEdit(self.groupBox)
        self.crops_coord_top_left_y.setObjectName(u"crops_coord_top_left_y")

        self.horizontalLayout_2.addWidget(self.crops_coord_top_left_y)


        self.gridLayout_3.addWidget(self.groupBox, 2, 0, 1, 1)

        self.groupBox_5 = QGroupBox(self.tab)
        self.groupBox_5.setObjectName(u"groupBox_5")
        self.horizontalLayout_3 = QHBoxLayout(self.groupBox_5)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.target_size_x = QLineEdit(self.groupBox_5)
        self.target_size_x.setObjectName(u"target_size_x")

        self.horizontalLayout_3.addWidget(self.target_size_x)

        self.target_size_y = QLineEdit(self.groupBox_5)
        self.target_size_y.setObjectName(u"target_size_y")

        self.horizontalLayout_3.addWidget(self.target_size_y)


        self.gridLayout_3.addWidget(self.groupBox_5, 4, 0, 1, 1)

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
        self.image_presets.currentTextChanged.connect(generator_form.handle_image_presets_changed)
        self.secondary_prompt.textChanged.connect(generator_form.handle_second_prompt_changed)
        self.secondary_negative_prompt.textChanged.connect(generator_form.handle_second_prompt_changed)

        self.generator_form_tabs.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(generator_form)
    # setupUi

    def retranslateUi(self, generator_form):
        generator_form.setWindowTitle(QCoreApplication.translate("generator_form", u"Form", None))
        self.interrupt_button.setText(QCoreApplication.translate("generator_form", u"Interrupt", None))
        self.label.setText(QCoreApplication.translate("generator_form", u"Prompt", None))
        self.prompt.setPlaceholderText(QCoreApplication.translate("generator_form", u"Enter a prompt...", None))
        self.pushButton.setText(QCoreApplication.translate("generator_form", u"Save Prompts", None))
        self.secondary_prompt.setPlaceholderText(QCoreApplication.translate("generator_form", u"Enter a second prompt...", None))
        self.label_2.setText(QCoreApplication.translate("generator_form", u"Negative Prompt", None))
        self.negative_prompt.setPlaceholderText(QCoreApplication.translate("generator_form", u"Enter a negative prompt...", None))
        self.secondary_negative_prompt.setPlaceholderText(QCoreApplication.translate("generator_form", u"Enter a second negative prompt...", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("generator_form", u"Original Size", None))
        self.original_size_x.setPlaceholderText(QCoreApplication.translate("generator_form", u"width", None))
        self.original_size_y.setPlaceholderText(QCoreApplication.translate("generator_form", u"height", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("generator_form", u"Negative Original Size", None))
        self.negative_original_size_x.setPlaceholderText(QCoreApplication.translate("generator_form", u"width", None))
        self.negative_original_size_y.setPlaceholderText(QCoreApplication.translate("generator_form", u"height", None))
        self.groupBox_4.setTitle(QCoreApplication.translate("generator_form", u"Negative Target Size", None))
        self.negative_target_size_x.setPlaceholderText(QCoreApplication.translate("generator_form", u"width", None))
        self.negative_target_size_y.setPlaceholderText(QCoreApplication.translate("generator_form", u"height", None))
        self.generate_button.setText(QCoreApplication.translate("generator_form", u"Generate", None))
        self.groupBox.setTitle(QCoreApplication.translate("generator_form", u"Crops Coord (top left)", None))
        self.crops_coord_top_left_x.setPlaceholderText(QCoreApplication.translate("generator_form", u"x position", None))
        self.crops_coord_top_left_y.setPlaceholderText(QCoreApplication.translate("generator_form", u"y position", None))
        self.groupBox_5.setTitle(QCoreApplication.translate("generator_form", u"Target Size", None))
        self.target_size_x.setPlaceholderText(QCoreApplication.translate("generator_form", u"width", None))
        self.target_size_y.setPlaceholderText(QCoreApplication.translate("generator_form", u"height", None))
        self.generator_form_tabs.setTabText(self.generator_form_tabs.indexOf(self.tab), QCoreApplication.translate("generator_form", u"Tab 1", None))
        self.generator_form_tabs.setTabText(self.generator_form_tabs.indexOf(self.tab_2), QCoreApplication.translate("generator_form", u"Tab 2", None))
    # retranslateUi

