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
from PySide6.QtWidgets import (QApplication, QGridLayout, QLineEdit, QPushButton,
    QSizePolicy, QWidget)
import airunner.feather_rc

class Ui_browser(object):
    def setupUi(self, browser):
        if not browser.objectName():
            browser.setObjectName(u"browser")
        browser.resize(400, 300)
        self.gridLayout = QGridLayout(browser)
        self.gridLayout.setObjectName(u"gridLayout")
        self.next_button = QPushButton(browser)
        self.next_button.setObjectName(u"next_button")
        icon = QIcon()
        icon.addFile(u":/dark/icons/feather/dark/arrow-right-circle.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.next_button.setIcon(icon)

        self.gridLayout.addWidget(self.next_button, 0, 4, 1, 1)

        self.submit_button = QPushButton(browser)
        self.submit_button.setObjectName(u"submit_button")
        icon1 = QIcon()
        icon1.addFile(u":/dark/icons/feather/dark/chevron-up.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.submit_button.setIcon(icon1)

        self.gridLayout.addWidget(self.submit_button, 0, 1, 1, 1)

        self.refresh_button = QPushButton(browser)
        self.refresh_button.setObjectName(u"refresh_button")
        icon2 = QIcon()
        icon2.addFile(u":/dark/icons/feather/dark/refresh-cw.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.refresh_button.setIcon(icon2)

        self.gridLayout.addWidget(self.refresh_button, 0, 2, 1, 1)

        self.url = QLineEdit(browser)
        self.url.setObjectName(u"url")

        self.gridLayout.addWidget(self.url, 0, 0, 1, 1)

        self.plaintext_button = QPushButton(browser)
        self.plaintext_button.setObjectName(u"plaintext_button")
        icon3 = QIcon()
        icon3.addFile(u":/dark/icons/feather/dark/align-justify.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.plaintext_button.setIcon(icon3)
        self.plaintext_button.setCheckable(True)

        self.gridLayout.addWidget(self.plaintext_button, 0, 5, 1, 1)

        self.back_button = QPushButton(browser)
        self.back_button.setObjectName(u"back_button")
        icon4 = QIcon()
        icon4.addFile(u":/dark/icons/feather/dark/arrow-left-circle.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.back_button.setIcon(icon4)

        self.gridLayout.addWidget(self.back_button, 0, 3, 1, 1)

        self.summarize_button = QPushButton(browser)
        self.summarize_button.setObjectName(u"summarize_button")
        icon5 = QIcon()
        icon5.addFile(u":/dark/icons/feather/dark/list.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.summarize_button.setIcon(icon5)
        self.summarize_button.setCheckable(True)

        self.gridLayout.addWidget(self.summarize_button, 0, 6, 1, 1)

        self.clear_data_button = QPushButton(browser)
        self.clear_data_button.setObjectName(u"clear_data_button")
        icon6 = QIcon()
        icon6.addFile(u":/dark/icons/feather/dark/trash-2.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.clear_data_button.setIcon(icon6)

        self.gridLayout.addWidget(self.clear_data_button, 0, 7, 1, 1)

        self.stage = QWebEngineView(browser)
        self.stage.setObjectName(u"stage")
        self.stage.setMinimumSize(QSize(200, 200))
        self.stage.setUrl(QUrl(u"about:blank"))

        self.gridLayout.addWidget(self.stage, 1, 0, 1, 8)


        self.retranslateUi(browser)

        QMetaObject.connectSlotsByName(browser)
    # setupUi

    def retranslateUi(self, browser):
        browser.setWindowTitle(QCoreApplication.translate("browser", u"Form", None))
#if QT_CONFIG(tooltip)
        self.next_button.setToolTip(QCoreApplication.translate("browser", u"Next", None))
#endif // QT_CONFIG(tooltip)
        self.next_button.setText("")
#if QT_CONFIG(tooltip)
        self.submit_button.setToolTip(QCoreApplication.translate("browser", u"Submit", None))
#endif // QT_CONFIG(tooltip)
        self.submit_button.setText("")
#if QT_CONFIG(tooltip)
        self.refresh_button.setToolTip(QCoreApplication.translate("browser", u"Refresh", None))
#endif // QT_CONFIG(tooltip)
        self.refresh_button.setText("")
        self.url.setPlaceholderText(QCoreApplication.translate("browser", u"https://", None))
#if QT_CONFIG(tooltip)
        self.plaintext_button.setToolTip(QCoreApplication.translate("browser", u"Plaintext", None))
#endif // QT_CONFIG(tooltip)
        self.plaintext_button.setText("")
#if QT_CONFIG(tooltip)
        self.back_button.setToolTip(QCoreApplication.translate("browser", u"Back", None))
#endif // QT_CONFIG(tooltip)
        self.back_button.setText("")
#if QT_CONFIG(tooltip)
        self.summarize_button.setToolTip(QCoreApplication.translate("browser", u"Summarize", None))
#endif // QT_CONFIG(tooltip)
        self.summarize_button.setText("")
#if QT_CONFIG(tooltip)
        self.clear_data_button.setToolTip(QCoreApplication.translate("browser", u"Clear Browsing Data", None))
#endif // QT_CONFIG(tooltip)
        self.clear_data_button.setText("")
    # retranslateUi

