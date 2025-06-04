# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'chat_prompt.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QHBoxLayout,
    QPlainTextEdit, QProgressBar, QPushButton, QScrollArea,
    QSizePolicy, QSpacerItem, QSplitter, QWidget)

from airunner.components.chat.gui.widgets.conversation_widget import ConversationWidget
from airunner.gui.widgets.llm.llm_history_widget import LLMHistoryWidget
import airunner.feather_rc

class Ui_chat_prompt(object):
    def setupUi(self, chat_prompt):
        if not chat_prompt.objectName():
            chat_prompt.setObjectName(u"chat_prompt")
        chat_prompt.resize(597, 691)
        self.gridLayout_2 = QGridLayout(chat_prompt)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.scrollArea = QScrollArea(chat_prompt)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents_2 = QWidget()
        self.scrollAreaWidgetContents_2.setObjectName(u"scrollAreaWidgetContents_2")
        self.scrollAreaWidgetContents_2.setGeometry(QRect(0, 0, 595, 602))
        self.gridLayout = QGridLayout(self.scrollAreaWidgetContents_2)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(0)
        self.gridLayout.setVerticalSpacing(10)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.chat_prompt_splitter = QSplitter(self.scrollAreaWidgetContents_2)
        self.chat_prompt_splitter.setObjectName(u"chat_prompt_splitter")
        self.chat_prompt_splitter.setOrientation(Qt.Orientation.Vertical)
        self.chat_prompt_splitter.setChildrenCollapsible(False)
        self.conversation = ConversationWidget(self.chat_prompt_splitter)
        self.conversation.setObjectName(u"conversation")
        self.chat_prompt_splitter.addWidget(self.conversation)
        self.prompt = QPlainTextEdit(self.chat_prompt_splitter)
        self.prompt.setObjectName(u"prompt")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.prompt.sizePolicy().hasHeightForWidth())
        self.prompt.setSizePolicy(sizePolicy)
        self.prompt.setMinimumSize(QSize(0, 150))
        self.prompt.setMaximumSize(QSize(16777215, 16777215))
        self.chat_prompt_splitter.addWidget(self.prompt)

        self.gridLayout.addWidget(self.chat_prompt_splitter, 0, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents_2)

        self.gridLayout_2.addWidget(self.scrollArea, 2, 0, 1, 1)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)

        self.clear_conversation_button = QPushButton(chat_prompt)
        self.clear_conversation_button.setObjectName(u"clear_conversation_button")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.clear_conversation_button.sizePolicy().hasHeightForWidth())
        self.clear_conversation_button.setSizePolicy(sizePolicy1)
        self.clear_conversation_button.setMinimumSize(QSize(25, 25))
        self.clear_conversation_button.setMaximumSize(QSize(25, 25))
        icon = QIcon()
        icon.addFile(u":/light/icons/feather/light/plus.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.clear_conversation_button.setIcon(icon)

        self.horizontalLayout_2.addWidget(self.clear_conversation_button)

        self.history_button = QPushButton(chat_prompt)
        self.history_button.setObjectName(u"history_button")
        sizePolicy1.setHeightForWidth(self.history_button.sizePolicy().hasHeightForWidth())
        self.history_button.setSizePolicy(sizePolicy1)
        self.history_button.setMinimumSize(QSize(25, 25))
        self.history_button.setMaximumSize(QSize(25, 25))
        icon1 = QIcon()
        icon1.addFile(u":/light/icons/feather/light/clock.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.history_button.setIcon(icon1)
        self.history_button.setCheckable(True)

        self.horizontalLayout_2.addWidget(self.history_button)


        self.gridLayout_2.addLayout(self.horizontalLayout_2, 0, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(5)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.action = QComboBox(chat_prompt)
        self.action.setObjectName(u"action")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.action.sizePolicy().hasHeightForWidth())
        self.action.setSizePolicy(sizePolicy2)
        self.action.setMinimumSize(QSize(100, 30))
        self.action.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)

        self.horizontalLayout.addWidget(self.action)

        self.progressBar = QProgressBar(chat_prompt)
        self.progressBar.setObjectName(u"progressBar")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.progressBar.sizePolicy().hasHeightForWidth())
        self.progressBar.setSizePolicy(sizePolicy3)
        self.progressBar.setMinimumSize(QSize(0, 30))
        self.progressBar.setValue(0)

        self.horizontalLayout.addWidget(self.progressBar)

        self.send_button = QPushButton(chat_prompt)
        self.send_button.setObjectName(u"send_button")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.send_button.sizePolicy().hasHeightForWidth())
        self.send_button.setSizePolicy(sizePolicy4)
        self.send_button.setMinimumSize(QSize(30, 30))
        self.send_button.setMaximumSize(QSize(30, 30))
        icon2 = QIcon()
        icon2.addFile(u":/light/icons/feather/light/chevron-up.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.send_button.setIcon(icon2)

        self.horizontalLayout.addWidget(self.send_button)

        self.pushButton = QPushButton(chat_prompt)
        self.pushButton.setObjectName(u"pushButton")
        sizePolicy4.setHeightForWidth(self.pushButton.sizePolicy().hasHeightForWidth())
        self.pushButton.setSizePolicy(sizePolicy4)
        self.pushButton.setMinimumSize(QSize(30, 30))
        self.pushButton.setMaximumSize(QSize(30, 30))
        icon3 = QIcon()
        icon3.addFile(u":/light/icons/feather/light/stop-circle.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.pushButton.setIcon(icon3)

        self.horizontalLayout.addWidget(self.pushButton)


        self.gridLayout_2.addLayout(self.horizontalLayout, 3, 0, 1, 1)

        self.chat_history_widget = LLMHistoryWidget(chat_prompt)
        self.chat_history_widget.setObjectName(u"chat_history_widget")

        self.gridLayout_2.addWidget(self.chat_history_widget, 1, 0, 1, 1)


        self.retranslateUi(chat_prompt)
        self.prompt.textChanged.connect(chat_prompt.prompt_text_changed)
        self.action.currentTextChanged.connect(chat_prompt.llm_action_changed)
        self.send_button.clicked.connect(chat_prompt.action_button_clicked_send)
        self.clear_conversation_button.clicked.connect(chat_prompt.action_button_clicked_clear_conversation)
        self.pushButton.clicked.connect(chat_prompt.interrupt_button_clicked)

        QMetaObject.connectSlotsByName(chat_prompt)
    # setupUi

    def retranslateUi(self, chat_prompt):
        chat_prompt.setWindowTitle(QCoreApplication.translate("chat_prompt", u"Form", None))
#if QT_CONFIG(tooltip)
        self.clear_conversation_button.setToolTip(QCoreApplication.translate("chat_prompt", u"New converation", None))
#endif // QT_CONFIG(tooltip)
        self.clear_conversation_button.setText("")
        self.history_button.setText("")
#if QT_CONFIG(tooltip)
        self.send_button.setToolTip(QCoreApplication.translate("chat_prompt", u"Send message", None))
#endif // QT_CONFIG(tooltip)
        self.send_button.setText("")
#if QT_CONFIG(tooltip)
        self.pushButton.setToolTip(QCoreApplication.translate("chat_prompt", u"Cancel message", None))
#endif // QT_CONFIG(tooltip)
        self.pushButton.setText("")
    # retranslateUi

