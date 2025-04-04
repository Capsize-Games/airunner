# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'bot_preferences.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QPlainTextEdit, QPushButton, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_bot_preferences(object):
    def setupUi(self, bot_preferences):
        if not bot_preferences.objectName():
            bot_preferences.setObjectName(u"bot_preferences")
        bot_preferences.resize(828, 1092)
        self.gridLayout_4 = QGridLayout(bot_preferences)
        self.gridLayout_4.setSpacing(0)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.gridLayout_4.setContentsMargins(0, 0, 0, 0)
        self.scrollArea = QScrollArea(bot_preferences)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents_2 = QWidget()
        self.scrollAreaWidgetContents_2.setObjectName(u"scrollAreaWidgetContents_2")
        self.scrollAreaWidgetContents_2.setGeometry(QRect(0, -242, 812, 1332))
        self.gridLayout = QGridLayout(self.scrollAreaWidgetContents_2)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setVerticalSpacing(10)
        self.gridLayout.setContentsMargins(10, 10, 10, 10)
        self.system_instructions_groupbox = QGroupBox(self.scrollAreaWidgetContents_2)
        self.system_instructions_groupbox.setObjectName(u"system_instructions_groupbox")
        self.system_instructions_groupbox.setCheckable(True)
        self.verticalLayout_3 = QVBoxLayout(self.system_instructions_groupbox)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.system_instructions = QPlainTextEdit(self.system_instructions_groupbox)
        self.system_instructions.setObjectName(u"system_instructions")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.system_instructions.sizePolicy().hasHeightForWidth())
        self.system_instructions.setSizePolicy(sizePolicy)
        self.system_instructions.setMinimumSize(QSize(0, 150))

        self.verticalLayout_3.addWidget(self.system_instructions)


        self.gridLayout.addWidget(self.system_instructions_groupbox, 10, 0, 1, 1)

        self.names_groupbox = QGroupBox(self.scrollAreaWidgetContents_2)
        self.names_groupbox.setObjectName(u"names_groupbox")
        self.names_groupbox.setCheckable(True)
        self.horizontalLayout = QHBoxLayout(self.names_groupbox)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.verticalLayout_6 = QVBoxLayout()
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.label = QLabel(self.names_groupbox)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setBold(True)
        self.label.setFont(font)

        self.verticalLayout_6.addWidget(self.label)

        self.botname = QLineEdit(self.names_groupbox)
        self.botname.setObjectName(u"botname")
        self.botname.setCursorPosition(9)

        self.verticalLayout_6.addWidget(self.botname)


        self.horizontalLayout.addLayout(self.verticalLayout_6)


        self.gridLayout.addWidget(self.names_groupbox, 9, 0, 1, 1)

        self.groupBox_2 = QGroupBox(self.scrollAreaWidgetContents_2)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.gridLayout_8 = QGridLayout(self.groupBox_2)
        self.gridLayout_8.setObjectName(u"gridLayout_8")
        self.comboBox = QComboBox(self.groupBox_2)
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.setObjectName(u"comboBox")

        self.gridLayout_8.addWidget(self.comboBox, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_2, 0, 0, 1, 1)

        self.groupBox = QGroupBox(self.scrollAreaWidgetContents_2)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout_3 = QGridLayout(self.groupBox)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.create_new_button = QPushButton(self.groupBox)
        self.create_new_button.setObjectName(u"create_new_button")
        self.create_new_button.setMaximumSize(QSize(40, 16777215))
        icon = QIcon(QIcon.fromTheme(u"list-add"))
        self.create_new_button.setIcon(icon)

        self.gridLayout_3.addWidget(self.create_new_button, 0, 1, 1, 1)

        self.saved_chatbots = QComboBox(self.groupBox)
        self.saved_chatbots.setObjectName(u"saved_chatbots")

        self.gridLayout_3.addWidget(self.saved_chatbots, 0, 0, 1, 1)

        self.delete_button = QPushButton(self.groupBox)
        self.delete_button.setObjectName(u"delete_button")
        self.delete_button.setMaximumSize(QSize(40, 16777215))
        icon1 = QIcon(QIcon.fromTheme(u"process-stop"))
        self.delete_button.setIcon(icon1)

        self.gridLayout_3.addWidget(self.delete_button, 0, 2, 1, 1)


        self.gridLayout.addWidget(self.groupBox, 1, 0, 1, 1)

        self.personality_groupbox = QGroupBox(self.scrollAreaWidgetContents_2)
        self.personality_groupbox.setObjectName(u"personality_groupbox")
        self.personality_groupbox.setCheckable(True)
        self.gridLayout_5 = QGridLayout(self.personality_groupbox)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.bot_personality = QPlainTextEdit(self.personality_groupbox)
        self.bot_personality.setObjectName(u"bot_personality")
        sizePolicy.setHeightForWidth(self.bot_personality.sizePolicy().hasHeightForWidth())
        self.bot_personality.setSizePolicy(sizePolicy)
        self.bot_personality.setMinimumSize(QSize(0, 75))

        self.gridLayout_5.addWidget(self.bot_personality, 1, 0, 1, 1)

        self.label_2 = QLabel(self.personality_groupbox)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout_5.addWidget(self.label_2, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.personality_groupbox, 12, 0, 1, 1)

        self.groupBox_3 = QGroupBox(self.scrollAreaWidgetContents_2)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.gridLayout_9 = QGridLayout(self.groupBox_3)
        self.gridLayout_9.setObjectName(u"gridLayout_9")
        self.browse_documents_button = QPushButton(self.groupBox_3)
        self.browse_documents_button.setObjectName(u"browse_documents_button")

        self.gridLayout_9.addWidget(self.browse_documents_button, 1, 0, 1, 1)

        self.target_files = QScrollArea(self.groupBox_3)
        self.target_files.setObjectName(u"target_files")
        sizePolicy.setHeightForWidth(self.target_files.sizePolicy().hasHeightForWidth())
        self.target_files.setSizePolicy(sizePolicy)
        self.target_files.setMinimumSize(QSize(0, 150))
        self.target_files.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 766, 148))
        self.gridLayout_10 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_10.setObjectName(u"gridLayout_10")
        self.target_files.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_9.addWidget(self.target_files, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_3, 2, 0, 1, 1)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.use_weather_prompt = QCheckBox(self.scrollAreaWidgetContents_2)
        self.use_weather_prompt.setObjectName(u"use_weather_prompt")

        self.horizontalLayout_3.addWidget(self.use_weather_prompt)

        self.use_datetime = QCheckBox(self.scrollAreaWidgetContents_2)
        self.use_datetime.setObjectName(u"use_datetime")

        self.horizontalLayout_3.addWidget(self.use_datetime)


        self.gridLayout.addLayout(self.horizontalLayout_3, 6, 0, 1, 1)

        self.label_3 = QLabel(self.scrollAreaWidgetContents_2)
        self.label_3.setObjectName(u"label_3")

        self.gridLayout.addWidget(self.label_3, 7, 0, 1, 1)

        self.line_2 = QFrame(self.scrollAreaWidgetContents_2)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line_2, 3, 0, 1, 1)

        self.line = QFrame(self.scrollAreaWidgetContents_2)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 8, 0, 1, 1)

        self.guardrails_groupbox = QGroupBox(self.scrollAreaWidgetContents_2)
        self.guardrails_groupbox.setObjectName(u"guardrails_groupbox")
        self.guardrails_groupbox.setCheckable(True)
        self.verticalLayout_2 = QVBoxLayout(self.guardrails_groupbox)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.guardrails_prompt = QPlainTextEdit(self.guardrails_groupbox)
        self.guardrails_prompt.setObjectName(u"guardrails_prompt")
        sizePolicy.setHeightForWidth(self.guardrails_prompt.sizePolicy().hasHeightForWidth())
        self.guardrails_prompt.setSizePolicy(sizePolicy)
        self.guardrails_prompt.setMinimumSize(QSize(0, 150))

        self.verticalLayout_2.addWidget(self.guardrails_prompt)


        self.gridLayout.addWidget(self.guardrails_groupbox, 11, 0, 1, 1)

        self.groupBox_4 = QGroupBox(self.scrollAreaWidgetContents_2)
        self.groupBox_4.setObjectName(u"groupBox_4")
        self.gridLayout_2 = QGridLayout(self.groupBox_4)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gender = QComboBox(self.groupBox_4)
        self.gender.addItem("")
        self.gender.addItem("")
        self.gender.setObjectName(u"gender")

        self.gridLayout_2.addWidget(self.gender, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_4, 13, 0, 1, 1)

        self.voice_groupbox = QGroupBox(self.scrollAreaWidgetContents_2)
        self.voice_groupbox.setObjectName(u"voice_groupbox")
        self.gridLayout_voice = QGridLayout(self.voice_groupbox)
        self.gridLayout_voice.setObjectName(u"gridLayout_voice")
        self.voice_combobox = QComboBox(self.voice_groupbox)
        self.voice_combobox.setObjectName(u"voice_combobox")

        self.gridLayout_voice.addWidget(self.voice_combobox, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.voice_groupbox, 14, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents_2)

        self.gridLayout_4.addWidget(self.scrollArea, 0, 0, 1, 1)


        self.retranslateUi(bot_preferences)
        self.botname.textChanged.connect(bot_preferences.botname_changed)
        self.bot_personality.textChanged.connect(bot_preferences.bot_personality_changed)
        self.names_groupbox.toggled.connect(bot_preferences.toggle_use_names)
        self.personality_groupbox.toggled.connect(bot_preferences.toggle_use_personality)
        self.guardrails_prompt.textChanged.connect(bot_preferences.guardrails_prompt_changed)
        self.system_instructions.textChanged.connect(bot_preferences.system_instructions_changed)
        self.guardrails_groupbox.toggled.connect(bot_preferences.toggle_use_guardrails)
        self.system_instructions_groupbox.toggled.connect(bot_preferences.toggle_use_system_instructions)
        self.saved_chatbots.currentTextChanged.connect(bot_preferences.saved_chatbots_changed)
        self.create_new_button.clicked.connect(bot_preferences.create_new_chatbot_clicked)
        self.delete_button.clicked.connect(bot_preferences.delete_clicked)
        self.comboBox.currentTextChanged.connect(bot_preferences.agent_type_changed)
        self.browse_documents_button.clicked.connect(bot_preferences.browse_documents)
        self.use_weather_prompt.toggled.connect(bot_preferences.use_weather_prompt_toggled)
        self.use_datetime.toggled.connect(bot_preferences.toggle_use_datetime)
        self.gender.currentTextChanged.connect(bot_preferences.gender_changed)
        self.voice_combobox.currentIndexChanged.connect(bot_preferences.voice_changed)

        QMetaObject.connectSlotsByName(bot_preferences)
    # setupUi

    def retranslateUi(self, bot_preferences):
        bot_preferences.setWindowTitle(QCoreApplication.translate("bot_preferences", u"Form", None))
        self.system_instructions_groupbox.setTitle(QCoreApplication.translate("bot_preferences", u"System Instructions", None))
        self.system_instructions.setPlaceholderText(QCoreApplication.translate("bot_preferences", u"Instructions for the LLM", None))
        self.names_groupbox.setTitle(QCoreApplication.translate("bot_preferences", u"Use names", None))
        self.label.setText(QCoreApplication.translate("bot_preferences", u"Assistant name", None))
        self.botname.setText(QCoreApplication.translate("bot_preferences", u"AI Runner", None))
        self.botname.setPlaceholderText(QCoreApplication.translate("bot_preferences", u"Bot name", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("bot_preferences", u"Agent Type", None))
        self.comboBox.setItemText(0, QCoreApplication.translate("bot_preferences", u"Chatbot", None))
        self.comboBox.setItemText(1, QCoreApplication.translate("bot_preferences", u"Tool", None))

        self.groupBox.setTitle(QCoreApplication.translate("bot_preferences", u"Existing Agents", None))
#if QT_CONFIG(tooltip)
        self.create_new_button.setToolTip(QCoreApplication.translate("bot_preferences", u"Add new agent", None))
#endif // QT_CONFIG(tooltip)
        self.create_new_button.setText("")
#if QT_CONFIG(tooltip)
        self.delete_button.setToolTip(QCoreApplication.translate("bot_preferences", u"Delete agent", None))
#endif // QT_CONFIG(tooltip)
        self.delete_button.setText("")
        self.personality_groupbox.setTitle(QCoreApplication.translate("bot_preferences", u"Bot Personality", None))
        self.bot_personality.setPlaceholderText(QCoreApplication.translate("bot_preferences", u"EXAMPLE: {{ botname }} is very helpful and {{ gender }} loves {{ username }}.", None))
        self.label_2.setText(QCoreApplication.translate("bot_preferences", u"A brief description of the bot's personality", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("bot_preferences", u"Documents", None))
        self.browse_documents_button.setText(QCoreApplication.translate("bot_preferences", u"Browse", None))
        self.use_weather_prompt.setText(QCoreApplication.translate("bot_preferences", u"Use Weather Prompt", None))
        self.use_datetime.setText(QCoreApplication.translate("bot_preferences", u"Use Datetime", None))
        self.label_3.setText(QCoreApplication.translate("bot_preferences", u"Check this and set zipcode in User Settings to give agents access to local weather.", None))
        self.guardrails_groupbox.setTitle(QCoreApplication.translate("bot_preferences", u"Guardrails", None))
        self.guardrails_prompt.setPlaceholderText(QCoreApplication.translate("bot_preferences", u"The guardrails prompt is used to moderate results.", None))
        self.groupBox_4.setTitle(QCoreApplication.translate("bot_preferences", u"Gender", None))
        self.gender.setItemText(0, QCoreApplication.translate("bot_preferences", u"Male", None))
        self.gender.setItemText(1, QCoreApplication.translate("bot_preferences", u"Female", None))

        self.voice_groupbox.setTitle(QCoreApplication.translate("bot_preferences", u"Voice", None))
    # retranslateUi

