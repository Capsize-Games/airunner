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
from PySide6.QtWidgets import (QApplication, QGridLayout, QLineEdit, QPushButton,
    QSizePolicy, QWidget)

class Ui_web_browser_widget(object):
    def setupUi(self, web_browser_widget):
        if not web_browser_widget.objectName():
            web_browser_widget.setObjectName(u"web_browser_widget")
        web_browser_widget.resize(400, 300)
        self.gridLayout = QGridLayout(web_browser_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.webEngineView = QWebEngineView(web_browser_widget)
        self.webEngineView.setObjectName(u"webEngineView")
        self.webEngineView.setUrl(QUrl(u"about:blank"))

        self.gridLayout.addWidget(self.webEngineView, 3, 0, 1, 1)

        self.horizontalWidget = QWidget(web_browser_widget)
        self.horizontalWidget.setObjectName(u"horizontalWidget")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.horizontalWidget.sizePolicy().hasHeightForWidth())
        self.horizontalWidget.setSizePolicy(sizePolicy)
        self.gridLayout_2 = QGridLayout(self.horizontalWidget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.url = QLineEdit(self.horizontalWidget)
        self.url.setObjectName(u"url")

        self.gridLayout_2.addWidget(self.url, 0, 0, 1, 1)

        self.pushButton = QPushButton(self.horizontalWidget)
        self.pushButton.setObjectName(u"pushButton")

        self.gridLayout_2.addWidget(self.pushButton, 0, 1, 1, 1)


        self.gridLayout.addWidget(self.horizontalWidget, 2, 0, 1, 1)


        self.retranslateUi(web_browser_widget)
        self.pushButton.clicked.connect(web_browser_widget.submit)

        QMetaObject.connectSlotsByName(web_browser_widget)
    # setupUi

    def retranslateUi(self, web_browser_widget):
        web_browser_widget.setWindowTitle(QCoreApplication.translate("web_browser_widget", u"Form", None))
        self.url.setPlaceholderText(QCoreApplication.translate("web_browser_widget", u"URL", None))
        self.pushButton.setText(QCoreApplication.translate("web_browser_widget", u"Go", None))
    # retranslateUi

