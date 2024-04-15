# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'message.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QSizePolicy, QTextEdit, QWidget)

class Ui_message(object):
    def setupUi(self, message):
        if not message.objectName():
            message.setObjectName(u"message")
        message.resize(418, 902)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(message.sizePolicy().hasHeightForWidth())
        message.setSizePolicy(sizePolicy)
        message.setMinimumSize(QSize(0, 40))
        self.gridLayout = QGridLayout(message)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.user_name = QLabel(message)
        self.user_name.setObjectName(u"user_name")
        self.user_name.setAlignment(Qt.AlignBottom|Qt.AlignLeading|Qt.AlignLeft)

        self.horizontalLayout.addWidget(self.user_name)

        self.content = QTextEdit(message)
        self.content.setObjectName(u"content")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.content.sizePolicy().hasHeightForWidth())
        self.content.setSizePolicy(sizePolicy1)
        self.content.setMinimumSize(QSize(0, 40))
        self.content.setStyleSheet(u"border-radius: 5px; border: 5px solid #1f1f1f; background-color: #1f1f1f; color: #ffffff;")
        self.content.setFrameShape(QFrame.NoFrame)
        self.content.setFrameShadow(QFrame.Plain)
        self.content.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.horizontalLayout.addWidget(self.content)

        self.bot_name = QLabel(message)
        self.bot_name.setObjectName(u"bot_name")
        self.bot_name.setAlignment(Qt.AlignBottom|Qt.AlignLeading|Qt.AlignLeft)

        self.horizontalLayout.addWidget(self.bot_name)


        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)


        self.retranslateUi(message)

        QMetaObject.connectSlotsByName(message)
    # setupUi

    def retranslateUi(self, message):
        message.setWindowTitle(QCoreApplication.translate("message", u"Form", None))
        self.user_name.setText(QCoreApplication.translate("message", u"TextLabel", None))
        self.bot_name.setText(QCoreApplication.translate("message", u"TextLabel", None))
    # retranslateUi

