# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'conversation.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_conversation(object):
    def setupUi(self, conversation):
        if not conversation.objectName():
            conversation.setObjectName(u"conversation")
        conversation.resize(400, 300)
        conversation.setStyleSheet(u"\n"
"    QWidget#conversation {\n"
"     background: #181C20;\n"
"     border: 1.5px solid #23272B;\n"
"     border-radius: 6px;\n"
"    }\n"
"   ")
        self.gridLayout = QGridLayout(conversation)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.messages = QScrollArea(conversation)
        self.messages.setObjectName(u"messages")
        self.messages.setMinimumSize(QSize(200, 200))
        self.messages.setFrameShape(QFrame.Shape.NoFrame)
        self.messages.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.messages.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 400, 300))
        self.messagesLayout = QVBoxLayout(self.scrollAreaWidgetContents)
        self.messagesLayout.setSpacing(2)
        self.messagesLayout.setObjectName(u"messagesLayout")
        self.messagesLayout.setContentsMargins(0, 0, 0, 0)
        self.messages.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout.addWidget(self.messages, 0, 0, 1, 1)


        self.retranslateUi(conversation)

        QMetaObject.connectSlotsByName(conversation)
    # setupUi

    def retranslateUi(self, conversation):
        conversation.setWindowTitle(QCoreApplication.translate("conversation", u"Form", None))
    # retranslateUi

