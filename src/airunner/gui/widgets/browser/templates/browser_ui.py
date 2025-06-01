# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'browser.ui'
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

class Ui_browser(object):
    def setupUi(self, browser):
        if not browser.objectName():
            browser.setObjectName(u"browser")
        browser.resize(400, 300)
        self.gridLayout = QGridLayout(browser)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.stage = QWebEngineView(browser)
        self.stage.setObjectName(u"stage")
        self.stage.setMinimumSize(QSize(200, 200))
        self.stage.setUrl(QUrl(u"about:blank"))

        self.gridLayout.addWidget(self.stage, 0, 0, 1, 1)


        self.retranslateUi(browser)

        QMetaObject.connectSlotsByName(browser)
    # setupUi

    def retranslateUi(self, browser):
        browser.setWindowTitle(QCoreApplication.translate("browser", u"Form", None))
    # retranslateUi

