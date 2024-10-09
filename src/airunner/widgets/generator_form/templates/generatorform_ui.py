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
from airunner.widgets.llm.llm_history_widget import LLMHistoryWidget
import airunner.resources_light_rc
import airunner.resources_dark_rc

class Ui_generator_form(object):
    def setupUi(self, generator_form):
        if not generator_form.objectName():
            generator_form.setObjectName(u"generator_form")
        generator_form.resize(620, 946)
        font = QFont()
        font.setPointSize(8)
        generator_form.setFont(font)
        generator_form.setCursor(QCursor(Qt.PointingHandCursor))
        self.gridLayout_4 = QGridLayout(generator_form)
        self.gridLayout_4.setSpacing(0)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.gridLayout_4.setContentsMargins(0, 0, 0, 0)
        self.generator_form_tabs = QTabWidget(generator_form)
        self.generator_form_tabs.setObjectName(u"generator_form_tabs")
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.gridLayout_3 = QGridLayout(self.tab)
        self.gridLayout_3.setSpacing(0)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.stable_diffusion_generator_form = QScrollArea(self.tab)
        self.stable_diffusion_generator_form.setObjectName(u"stable_diffusion_generator_form")
        self.stable_diffusion_generator_form.setFrameShape(QFrame.Shape.NoFrame)
        self.stable_diffusion_generator_form.setFrameShadow(QFrame.Shadow.Plain)
        self.stable_diffusion_generator_form.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 616, 870))
        self.gridLayout = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(0)
        self.gridLayout.setVerticalSpacing(10)
        self.gridLayout.setContentsMargins(10, 0, 10, 0)
        self.croops_coord_top_left_groupbox = QGroupBox(self.scrollAreaWidgetContents)
        self.croops_coord_top_left_groupbox.setObjectName(u"croops_coord_top_left_groupbox")
        self.horizontalLayout_2 = QHBoxLayout(self.croops_coord_top_left_groupbox)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(2, 2, 2, 2)
        self.crops_coord_top_left_x = QLineEdit(self.croops_coord_top_left_groupbox)
        self.crops_coord_top_left_x.setObjectName(u"crops_coord_top_left_x")

        self.horizontalLayout_2.addWidget(self.crops_coord_top_left_x)

        self.crops_coord_top_left_y = QLineEdit(self.croops_coord_top_left_groupbox)
        self.crops_coord_top_left_y.setObjectName(u"crops_coord_top_left_y")

        self.horizontalLayout_2.addWidget(self.crops_coord_top_left_y)


        self.gridLayout.addWidget(self.croops_coord_top_left_groupbox, 11, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label_2 = QLabel(self.scrollAreaWidgetContents)
        self.label_2.setObjectName(u"label_2")

        self.verticalLayout.addWidget(self.label_2)

        self.image_presets = QComboBox(self.scrollAreaWidgetContents)
        self.image_presets.setObjectName(u"image_presets")

        self.verticalLayout.addWidget(self.image_presets)

        self.line_2 = QFrame(self.scrollAreaWidgetContents)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout.addWidget(self.line_2)


        self.horizontalLayout.addLayout(self.verticalLayout)

        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.label_3 = QLabel(self.scrollAreaWidgetContents)
        self.label_3.setObjectName(u"label_3")

        self.verticalLayout_2.addWidget(self.label_3)

        self.quality_effects = QComboBox(self.scrollAreaWidgetContents)
        self.quality_effects.addItem("")
        self.quality_effects.addItem("")
        self.quality_effects.addItem("")
        self.quality_effects.addItem("")
        self.quality_effects.setObjectName(u"quality_effects")

        self.verticalLayout_2.addWidget(self.quality_effects)

        self.line = QFrame(self.scrollAreaWidgetContents)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout_2.addWidget(self.line)


        self.horizontalLayout.addLayout(self.verticalLayout_2)


        self.gridLayout.addLayout(self.horizontalLayout, 2, 0, 1, 1)

        self.generator_form_splitter = QSplitter(self.scrollAreaWidgetContents)
        self.generator_form_splitter.setObjectName(u"generator_form_splitter")
        self.generator_form_splitter.setOrientation(Qt.Orientation.Vertical)
        self.generator_form_splitter.setChildrenCollapsible(False)
        self.layoutWidget = QWidget(self.generator_form_splitter)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.gridLayout_2 = QGridLayout(self.layoutWidget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 9)
        self.prompt = QPlainTextEdit(self.layoutWidget)
        self.prompt.setObjectName(u"prompt")

        self.gridLayout_2.addWidget(self.prompt, 1, 0, 1, 2)

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.horizontalLayout_6.setContentsMargins(-1, 10, -1, -1)
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_6.addItem(self.horizontalSpacer)

        self.pushButton = QPushButton(self.layoutWidget)
        self.pushButton.setObjectName(u"pushButton")

        self.horizontalLayout_6.addWidget(self.pushButton)


        self.gridLayout_2.addLayout(self.horizontalLayout_6, 0, 1, 1, 1)

        self.secondary_prompt = QPlainTextEdit(self.layoutWidget)
        self.secondary_prompt.setObjectName(u"secondary_prompt")

        self.gridLayout_2.addWidget(self.secondary_prompt, 2, 0, 1, 2)

        self.label = QLabel(self.layoutWidget)
        self.label.setObjectName(u"label")
        font1 = QFont()
        font1.setPointSize(8)
        font1.setBold(True)
        self.label.setFont(font1)

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)

        self.generator_form_splitter.addWidget(self.layoutWidget)
        self.layoutWidget1 = QWidget(self.generator_form_splitter)
        self.layoutWidget1.setObjectName(u"layoutWidget1")
        self.negative_prompt_container = QVBoxLayout(self.layoutWidget1)
        self.negative_prompt_container.setObjectName(u"negative_prompt_container")
        self.negative_prompt_container.setContentsMargins(0, 5, 0, 0)
        self.negative_prompt_label = QLabel(self.layoutWidget1)
        self.negative_prompt_label.setObjectName(u"negative_prompt_label")
        self.negative_prompt_label.setFont(font1)

        self.negative_prompt_container.addWidget(self.negative_prompt_label)

        self.negative_prompt = QPlainTextEdit(self.layoutWidget1)
        self.negative_prompt.setObjectName(u"negative_prompt")

        self.negative_prompt_container.addWidget(self.negative_prompt)

        self.secondary_negative_prompt = QPlainTextEdit(self.layoutWidget1)
        self.secondary_negative_prompt.setObjectName(u"secondary_negative_prompt")

        self.negative_prompt_container.addWidget(self.secondary_negative_prompt)

        self.generator_form_splitter.addWidget(self.layoutWidget1)

        self.gridLayout.addWidget(self.generator_form_splitter, 0, 0, 1, 1)

        self.stable_diffusion_generator_form.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_3.addWidget(self.stable_diffusion_generator_form, 0, 0, 1, 1)

        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.horizontalLayout_7.setContentsMargins(10, 10, 10, 10)
        self.progress_bar = QProgressBar(self.tab)
        self.progress_bar.setObjectName(u"progress_bar")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.progress_bar.sizePolicy().hasHeightForWidth())
        self.progress_bar.setSizePolicy(sizePolicy)
        self.progress_bar.setMinimumSize(QSize(0, 30))
        self.progress_bar.setValue(0)

        self.horizontalLayout_7.addWidget(self.progress_bar)

        self.generate_button = QPushButton(self.tab)
        self.generate_button.setObjectName(u"generate_button")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.generate_button.sizePolicy().hasHeightForWidth())
        self.generate_button.setSizePolicy(sizePolicy1)
        self.generate_button.setMinimumSize(QSize(30, 30))
        self.generate_button.setMaximumSize(QSize(30, 30))
        icon = QIcon(QIcon.fromTheme(u"go-up"))
        self.generate_button.setIcon(icon)

        self.horizontalLayout_7.addWidget(self.generate_button)

        self.interrupt_button = QPushButton(self.tab)
        self.interrupt_button.setObjectName(u"interrupt_button")
        sizePolicy1.setHeightForWidth(self.interrupt_button.sizePolicy().hasHeightForWidth())
        self.interrupt_button.setSizePolicy(sizePolicy1)
        self.interrupt_button.setMinimumSize(QSize(30, 30))
        self.interrupt_button.setMaximumSize(QSize(30, 30))
        self.interrupt_button.setCursor(QCursor(Qt.PointingHandCursor))
        icon1 = QIcon(QIcon.fromTheme(u"application-exit"))
        self.interrupt_button.setIcon(icon1)

        self.horizontalLayout_7.addWidget(self.interrupt_button)


        self.gridLayout_3.addLayout(self.horizontalLayout_7, 1, 0, 1, 1)

        self.generator_form_tabs.addTab(self.tab, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        self.gridLayout_5 = QGridLayout(self.tab_2)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.gridLayout_7 = QGridLayout()
        self.gridLayout_7.setObjectName(u"gridLayout_7")
        self.gridLayout_7.setHorizontalSpacing(0)
        self.gridLayout_7.setVerticalSpacing(10)
        self.chat_prompt_widget = ChatPromptWidget(self.tab_2)
        self.chat_prompt_widget.setObjectName(u"chat_prompt_widget")

        self.gridLayout_7.addWidget(self.chat_prompt_widget, 0, 0, 1, 1)


        self.gridLayout_5.addLayout(self.gridLayout_7, 0, 0, 1, 1)

        self.generator_form_tabs.addTab(self.tab_2, "")
        self.llm_history_widget_tab = QWidget()
        self.llm_history_widget_tab.setObjectName(u"llm_history_widget_tab")
        self.gridLayout_6 = QGridLayout(self.llm_history_widget_tab)
        self.gridLayout_6.setSpacing(0)
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.gridLayout_6.setContentsMargins(0, 0, 0, 0)
        self.llm_history_widget = LLMHistoryWidget(self.llm_history_widget_tab)
        self.llm_history_widget.setObjectName(u"llm_history_widget")

        self.gridLayout_6.addWidget(self.llm_history_widget, 0, 0, 1, 1)

        self.generator_form_tabs.addTab(self.llm_history_widget_tab, "")
        self.chatbot_mood_tab = QWidget()
        self.chatbot_mood_tab.setObjectName(u"chatbot_mood_tab")
        self.gridLayout_8 = QGridLayout(self.chatbot_mood_tab)
        self.gridLayout_8.setSpacing(0)
        self.gridLayout_8.setObjectName(u"gridLayout_8")
        self.gridLayout_8.setContentsMargins(0, 0, 0, 0)
        self.scrollArea = QScrollArea(self.chatbot_mood_tab)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents_2 = QWidget()
        self.scrollAreaWidgetContents_2.setObjectName(u"scrollAreaWidgetContents_2")
        self.scrollAreaWidgetContents_2.setGeometry(QRect(0, 0, 614, 918))
        self.gridLayout_9 = QGridLayout(self.scrollAreaWidgetContents_2)
        self.gridLayout_9.setObjectName(u"gridLayout_9")
        self.mood_label = QLabel(self.scrollAreaWidgetContents_2)
        self.mood_label.setObjectName(u"mood_label")
        self.mood_label.setWordWrap(True)

        self.gridLayout_9.addWidget(self.mood_label, 0, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_9.addItem(self.verticalSpacer, 1, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents_2)

        self.gridLayout_8.addWidget(self.scrollArea, 0, 0, 1, 1)

        self.generator_form_tabs.addTab(self.chatbot_mood_tab, "")

        self.gridLayout_4.addWidget(self.generator_form_tabs, 0, 0, 1, 1)

        QWidget.setTabOrder(self.generator_form_tabs, self.stable_diffusion_generator_form)
        QWidget.setTabOrder(self.stable_diffusion_generator_form, self.prompt)
        QWidget.setTabOrder(self.prompt, self.secondary_prompt)
        QWidget.setTabOrder(self.secondary_prompt, self.negative_prompt)
        QWidget.setTabOrder(self.negative_prompt, self.secondary_negative_prompt)
        QWidget.setTabOrder(self.secondary_negative_prompt, self.pushButton)
        QWidget.setTabOrder(self.pushButton, self.crops_coord_top_left_x)
        QWidget.setTabOrder(self.crops_coord_top_left_x, self.crops_coord_top_left_y)
        QWidget.setTabOrder(self.crops_coord_top_left_y, self.generate_button)
        QWidget.setTabOrder(self.generate_button, self.interrupt_button)

        self.retranslateUi(generator_form)
        self.pushButton.clicked.connect(generator_form.action_clicked_button_save_prompts)
        self.interrupt_button.clicked.connect(generator_form.handle_interrupt_button_clicked)
        self.generate_button.clicked.connect(generator_form.handle_generate_button_clicked)
        self.prompt.textChanged.connect(generator_form.handle_prompt_changed)
        self.negative_prompt.textChanged.connect(generator_form.handle_negative_prompt_changed)
        self.image_presets.currentTextChanged.connect(generator_form.handle_image_presets_changed)
        self.secondary_prompt.textChanged.connect(generator_form.handle_second_prompt_changed)
        self.secondary_negative_prompt.textChanged.connect(generator_form.handle_second_prompt_changed)
        self.quality_effects.textActivated.connect(generator_form.handle_quality_effects_changed)

        self.generator_form_tabs.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(generator_form)
    # setupUi

    def retranslateUi(self, generator_form):
        generator_form.setWindowTitle(QCoreApplication.translate("generator_form", u"Form", None))
        self.croops_coord_top_left_groupbox.setTitle(QCoreApplication.translate("generator_form", u"Crops Coord (top left)", None))
        self.crops_coord_top_left_x.setPlaceholderText(QCoreApplication.translate("generator_form", u"x position", None))
        self.crops_coord_top_left_y.setPlaceholderText(QCoreApplication.translate("generator_form", u"y position", None))
        self.label_2.setText(QCoreApplication.translate("generator_form", u"Presets", None))
        self.label_3.setText(QCoreApplication.translate("generator_form", u"Quality Effects", None))
        self.quality_effects.setItemText(0, "")
        self.quality_effects.setItemText(1, QCoreApplication.translate("generator_form", u"Normal", None))
        self.quality_effects.setItemText(2, QCoreApplication.translate("generator_form", u"Upscaled", None))
        self.quality_effects.setItemText(3, QCoreApplication.translate("generator_form", u"Downscaled", None))

        self.prompt.setPlaceholderText(QCoreApplication.translate("generator_form", u"Enter a prompt...", None))
        self.pushButton.setText(QCoreApplication.translate("generator_form", u"Save Prompts", None))
        self.secondary_prompt.setPlaceholderText(QCoreApplication.translate("generator_form", u"Enter a second prompt...", None))
        self.label.setText(QCoreApplication.translate("generator_form", u"Prompt", None))
        self.negative_prompt_label.setText(QCoreApplication.translate("generator_form", u"Negative Prompt", None))
        self.negative_prompt.setPlaceholderText(QCoreApplication.translate("generator_form", u"Enter a negative prompt...", None))
        self.secondary_negative_prompt.setPlaceholderText(QCoreApplication.translate("generator_form", u"Enter a second negative prompt...", None))
#if QT_CONFIG(tooltip)
        self.generate_button.setToolTip(QCoreApplication.translate("generator_form", u"Generate image", None))
#endif // QT_CONFIG(tooltip)
        self.generate_button.setText("")
#if QT_CONFIG(tooltip)
        self.interrupt_button.setToolTip(QCoreApplication.translate("generator_form", u"Cancel image generation", None))
#endif // QT_CONFIG(tooltip)
        self.interrupt_button.setText("")
        self.generator_form_tabs.setTabText(self.generator_form_tabs.indexOf(self.tab), QCoreApplication.translate("generator_form", u"AI Art", None))
        self.generator_form_tabs.setTabText(self.generator_form_tabs.indexOf(self.tab_2), QCoreApplication.translate("generator_form", u"Chat", None))
        self.generator_form_tabs.setTabText(self.generator_form_tabs.indexOf(self.llm_history_widget_tab), QCoreApplication.translate("generator_form", u"Chat History", None))
        self.mood_label.setText(QCoreApplication.translate("generator_form", u"TextLabel", None))
        self.generator_form_tabs.setTabText(self.generator_form_tabs.indexOf(self.chatbot_mood_tab), QCoreApplication.translate("generator_form", u"Chatbot mood", None))
    # retranslateUi

