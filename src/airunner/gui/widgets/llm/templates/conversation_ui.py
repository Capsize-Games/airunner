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
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (QApplication, QGridLayout, QSizePolicy, QWidget)

class Ui_conversation(object):
    def setupUi(self, conversation):
        if not conversation.objectName():
            conversation.setObjectName(u"conversation")
        conversation.resize(400, 300)
        self.gridLayout = QGridLayout(conversation)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.stage = QWebEngineView(conversation)
        self.stage.setObjectName(u"stage")
        self.stage.setMinimumSize(QSize(200, 200))
        self.stage.setUrl(QUrl(u"about:blank"))

        self.gridLayout.addWidget(self.stage, 0, 0, 1, 1)


        self.retranslateUi(conversation)

        QMetaObject.connectSlotsByName(conversation)
    # setupUi

    def retranslateUi(self, conversation):
        conversation.setWindowTitle(QCoreApplication.translate("conversation", u"Form", None))
    # retranslateUi

