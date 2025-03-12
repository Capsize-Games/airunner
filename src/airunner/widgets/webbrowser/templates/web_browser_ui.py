# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'web_browser.ui'
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
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (QApplication, QGridLayout, QSizePolicy, QWidget)

class Ui_web_browser_widget(object):
    def setupUi(self, web_browser_widget):
        if not web_browser_widget.objectName():
            web_browser_widget.setObjectName(u"web_browser_widget")
        web_browser_widget.resize(400, 300)
        self.gridLayout = QGridLayout(web_browser_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.webEngineView = QWebEngineView(web_browser_widget)
        self.webEngineView.setObjectName(u"webEngineView")
        self.webEngineView.setUrl(QUrl(u"about:blank"))

        self.gridLayout.addWidget(self.webEngineView, 0, 0, 1, 1)


        self.retranslateUi(web_browser_widget)

        QMetaObject.connectSlotsByName(web_browser_widget)
    # setupUi

    def retranslateUi(self, web_browser_widget):
        web_browser_widget.setWindowTitle(QCoreApplication.translate("web_browser_widget", u"Form", None))
    # retranslateUi

