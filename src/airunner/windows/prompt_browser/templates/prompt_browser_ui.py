# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'prompt_browser.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QGridLayout, QScrollArea,
    QSizePolicy, QWidget)

class Ui_prompt_browser(object):
    def setupUi(self, prompt_browser):
        if not prompt_browser.objectName():
            prompt_browser.setObjectName(u"prompt_browser")
        prompt_browser.resize(768, 597)
        self.gridLayout_2 = QGridLayout(prompt_browser)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.scrollArea = QScrollArea(prompt_browser)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 748, 577))
        self.gridLayout = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout.setObjectName(u"gridLayout")
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_2.addWidget(self.scrollArea, 0, 0, 1, 1)


        self.retranslateUi(prompt_browser)

        QMetaObject.connectSlotsByName(prompt_browser)
    # setupUi

    def retranslateUi(self, prompt_browser):
        prompt_browser.setWindowTitle(QCoreApplication.translate("prompt_browser", u"Prompt Browser", None))
    # retranslateUi

