# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'chat_prompt.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QGridLayout,
    QHBoxLayout, QPlainTextEdit, QProgressBar, QPushButton,
    QScrollArea, QSizePolicy, QSplitter, QTextEdit,
    QVBoxLayout, QWidget)

class Ui_chat_prompt(object):
    def setupUi(self, chat_prompt):
        if not chat_prompt.objectName():
            chat_prompt.setObjectName(u"chat_prompt")
        chat_prompt.resize(679, 1044)
        self.gridLayout = QGridLayout(chat_prompt)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.send_button = QPushButton(chat_prompt)
        self.send_button.setObjectName(u"send_button")

        self.horizontalLayout_2.addWidget(self.send_button)

        self.progressBar = QProgressBar(chat_prompt)
        self.progressBar.setObjectName(u"progressBar")
        self.progressBar.setValue(0)

        self.horizontalLayout_2.addWidget(self.progressBar)

        self.pushButton = QPushButton(chat_prompt)
        self.pushButton.setObjectName(u"pushButton")

        self.horizontalLayout_2.addWidget(self.pushButton)

        self.clear_conversatiion_button = QPushButton(chat_prompt)
        self.clear_conversatiion_button.setObjectName(u"clear_conversatiion_button")
        icon = QIcon(QIcon.fromTheme(u"user-trash"))
        self.clear_conversatiion_button.setIcon(icon)

        self.horizontalLayout_2.addWidget(self.clear_conversatiion_button)


        self.gridLayout.addLayout(self.horizontalLayout_2, 3, 0, 1, 1)

        self.chat_prompt_splitter = QSplitter(chat_prompt)
        self.chat_prompt_splitter.setObjectName(u"chat_prompt_splitter")
        self.chat_prompt_splitter.setOrientation(Qt.Vertical)
        self.chat_prompt_splitter.setChildrenCollapsible(False)
        self.verticalLayoutWidget = QWidget(self.chat_prompt_splitter)
        self.verticalLayoutWidget.setObjectName(u"verticalLayoutWidget")
        self.verticalLayout = QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.chat_container = QScrollArea(self.verticalLayoutWidget)
        self.chat_container.setObjectName(u"chat_container")
        self.chat_container.setFrameShape(QFrame.NoFrame)
        self.chat_container.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 659, 479))
        self.gridLayout_2 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.conversation = QTextEdit(self.scrollAreaWidgetContents)
        self.conversation.setObjectName(u"conversation")
        self.conversation.setReadOnly(True)

        self.gridLayout_2.addWidget(self.conversation, 0, 0, 1, 1)

        self.chat_container.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout.addWidget(self.chat_container)

        self.chat_prompt_splitter.addWidget(self.verticalLayoutWidget)
        self.prompt = QPlainTextEdit(self.chat_prompt_splitter)
        self.prompt.setObjectName(u"prompt")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.prompt.sizePolicy().hasHeightForWidth())
        self.prompt.setSizePolicy(sizePolicy)
        self.prompt.setMinimumSize(QSize(0, 150))
        self.prompt.setMaximumSize(QSize(16777215, 16777215))
        self.chat_prompt_splitter.addWidget(self.prompt)

        self.gridLayout.addWidget(self.chat_prompt_splitter, 1, 0, 1, 1)

        self.action = QComboBox(chat_prompt)
        self.action.setObjectName(u"action")

        self.gridLayout.addWidget(self.action, 2, 0, 1, 1)


        self.retranslateUi(chat_prompt)
        self.prompt.textChanged.connect(chat_prompt.prompt_text_changed)
        self.action.currentTextChanged.connect(chat_prompt.llm_action_changed)
        self.send_button.clicked.connect(chat_prompt.action_button_clicked_send)
        self.clear_conversatiion_button.clicked.connect(chat_prompt.action_button_clicked_clear_conversation)
        self.pushButton.clicked.connect(chat_prompt.interrupt_button_clicked)

        QMetaObject.connectSlotsByName(chat_prompt)
    # setupUi

    def retranslateUi(self, chat_prompt):
        chat_prompt.setWindowTitle(QCoreApplication.translate("chat_prompt", u"Form", None))
#if QT_CONFIG(tooltip)
        self.send_button.setToolTip(QCoreApplication.translate("chat_prompt", u"Send message", None))
#endif // QT_CONFIG(tooltip)
        self.send_button.setText(QCoreApplication.translate("chat_prompt", u"Send", None))
        self.pushButton.setText(QCoreApplication.translate("chat_prompt", u"Interrupt", None))
#if QT_CONFIG(tooltip)
        self.clear_conversatiion_button.setToolTip(QCoreApplication.translate("chat_prompt", u"Clear conversation", None))
#endif // QT_CONFIG(tooltip)
        self.clear_conversatiion_button.setText("")
    # retranslateUi

