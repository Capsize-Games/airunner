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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QHBoxLayout,
    QLineEdit, QPushButton, QSizePolicy, QSpacerItem,
    QSplitter, QWidget)
import airunner.feather_rc

class Ui_browser(object):
    def setupUi(self, browser):
        if not browser.objectName():
            browser.setObjectName(u"browser")
        browser.resize(847, 780)
        self.gridLayout = QGridLayout(browser)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.widget = QWidget(browser)
        self.widget.setObjectName(u"widget")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy)
        self.footer = QHBoxLayout(self.widget)
        self.footer.setObjectName(u"footer")
        self.plaintext_button = QPushButton(self.widget)
        self.plaintext_button.setObjectName(u"plaintext_button")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.plaintext_button.sizePolicy().hasHeightForWidth())
        self.plaintext_button.setSizePolicy(sizePolicy1)
        icon = QIcon()
        icon.addFile(u":/dark/icons/feather/dark/align-justify.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.plaintext_button.setIcon(icon)
        self.plaintext_button.setCheckable(True)

        self.footer.addWidget(self.plaintext_button)

        self.summarize_button = QPushButton(self.widget)
        self.summarize_button.setObjectName(u"summarize_button")
        sizePolicy1.setHeightForWidth(self.summarize_button.sizePolicy().hasHeightForWidth())
        self.summarize_button.setSizePolicy(sizePolicy1)
        icon1 = QIcon()
        icon1.addFile(u":/dark/icons/feather/dark/list.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.summarize_button.setIcon(icon1)
        self.summarize_button.setCheckable(True)

        self.footer.addWidget(self.summarize_button)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.footer.addItem(self.horizontalSpacer)

        self.clear_data_button = QPushButton(self.widget)
        self.clear_data_button.setObjectName(u"clear_data_button")
        sizePolicy1.setHeightForWidth(self.clear_data_button.sizePolicy().hasHeightForWidth())
        self.clear_data_button.setSizePolicy(sizePolicy1)
        icon2 = QIcon()
        icon2.addFile(u":/dark/icons/feather/dark/trash-2.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.clear_data_button.setIcon(icon2)

        self.footer.addWidget(self.clear_data_button)


        self.gridLayout.addWidget(self.widget, 1, 0, 1, 1)

        self.browser_tab_widget = QWidget(browser)
        self.browser_tab_widget.setObjectName(u"browser_tab_widget")
        self.gridLayout_2 = QGridLayout(self.browser_tab_widget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.widget1 = QWidget(self.browser_tab_widget)
        self.widget1.setObjectName(u"widget1")
        sizePolicy.setHeightForWidth(self.widget1.sizePolicy().hasHeightForWidth())
        self.widget1.setSizePolicy(sizePolicy)
        self.horizontalLayout_4 = QHBoxLayout(self.widget1)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.private_browse_button = QPushButton(self.widget1)
        self.private_browse_button.setObjectName(u"private_browse_button")
        icon3 = QIcon()
        icon3.addFile(u":/dark/icons/feather/dark/eye-off.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.private_browse_button.setIcon(icon3)
        self.private_browse_button.setCheckable(True)

        self.horizontalLayout_4.addWidget(self.private_browse_button)

        self.bookmark_page_button = QPushButton(self.widget1)
        self.bookmark_page_button.setObjectName(u"bookmark_page_button")
        icon4 = QIcon()
        icon4.addFile(u":/dark/icons/feather/dark/star.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.bookmark_page_button.setIcon(icon4)
        self.bookmark_page_button.setCheckable(True)

        self.horizontalLayout_4.addWidget(self.bookmark_page_button)

        self.url = QLineEdit(self.widget1)
        self.url.setObjectName(u"url")

        self.horizontalLayout_4.addWidget(self.url)

        self.submit_button = QPushButton(self.widget1)
        self.submit_button.setObjectName(u"submit_button")
        sizePolicy1.setHeightForWidth(self.submit_button.sizePolicy().hasHeightForWidth())
        self.submit_button.setSizePolicy(sizePolicy1)
        icon5 = QIcon()
        icon5.addFile(u":/dark/icons/feather/dark/chevron-up.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.submit_button.setIcon(icon5)

        self.horizontalLayout_4.addWidget(self.submit_button)

        self.refresh_button = QPushButton(self.widget1)
        self.refresh_button.setObjectName(u"refresh_button")
        sizePolicy1.setHeightForWidth(self.refresh_button.sizePolicy().hasHeightForWidth())
        self.refresh_button.setSizePolicy(sizePolicy1)
        icon6 = QIcon()
        icon6.addFile(u":/dark/icons/feather/dark/refresh-cw.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.refresh_button.setIcon(icon6)

        self.horizontalLayout_4.addWidget(self.refresh_button)

        self.back_button = QPushButton(self.widget1)
        self.back_button.setObjectName(u"back_button")
        sizePolicy1.setHeightForWidth(self.back_button.sizePolicy().hasHeightForWidth())
        self.back_button.setSizePolicy(sizePolicy1)
        icon7 = QIcon()
        icon7.addFile(u":/dark/icons/feather/dark/arrow-left-circle.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.back_button.setIcon(icon7)

        self.horizontalLayout_4.addWidget(self.back_button)

        self.next_button = QPushButton(self.widget1)
        self.next_button.setObjectName(u"next_button")
        sizePolicy1.setHeightForWidth(self.next_button.sizePolicy().hasHeightForWidth())
        self.next_button.setSizePolicy(sizePolicy1)
        icon8 = QIcon()
        icon8.addFile(u":/dark/icons/feather/dark/arrow-right-circle.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.next_button.setIcon(icon8)

        self.horizontalLayout_4.addWidget(self.next_button)

        self.bookmark_button = QPushButton(self.widget1)
        self.bookmark_button.setObjectName(u"bookmark_button")
        icon9 = QIcon()
        icon9.addFile(u":/dark/icons/feather/dark/bookmark.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.bookmark_button.setIcon(icon9)
        self.bookmark_button.setCheckable(True)

        self.horizontalLayout_4.addWidget(self.bookmark_button)

        self.history_button = QPushButton(self.widget1)
        self.history_button.setObjectName(u"history_button")
        icon10 = QIcon()
        icon10.addFile(u":/dark/icons/feather/dark/clock.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.history_button.setIcon(icon10)
        self.history_button.setCheckable(True)

        self.horizontalLayout_4.addWidget(self.history_button)


        self.gridLayout_2.addWidget(self.widget1, 0, 0, 1, 1)

        self.widget2 = QWidget(self.browser_tab_widget)
        self.widget2.setObjectName(u"widget2")
        sizePolicy.setHeightForWidth(self.widget2.sizePolicy().hasHeightForWidth())
        self.widget2.setSizePolicy(sizePolicy)
        self.horizontalLayout_3 = QHBoxLayout(self.widget2)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.user_agent_os = QComboBox(self.widget2)
        self.user_agent_os.setObjectName(u"user_agent_os")

        self.horizontalLayout_3.addWidget(self.user_agent_os)

        self.user_agent_browser = QComboBox(self.widget2)
        self.user_agent_browser.setObjectName(u"user_agent_browser")

        self.horizontalLayout_3.addWidget(self.user_agent_browser)

        self.pushButton = QPushButton(self.widget2)
        self.pushButton.setObjectName(u"pushButton")
        sizePolicy1.setHeightForWidth(self.pushButton.sizePolicy().hasHeightForWidth())
        self.pushButton.setSizePolicy(sizePolicy1)
        self.pushButton.setMinimumSize(QSize(0, 0))
        icon11 = QIcon()
        icon11.addFile(u":/dark/icons/feather/dark/dice-game-icon.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.pushButton.setIcon(icon11)

        self.horizontalLayout_3.addWidget(self.pushButton)


        self.gridLayout_2.addWidget(self.widget2, 1, 0, 1, 1)

        self.splitter = QSplitter(self.browser_tab_widget)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.left_panel = QWidget(self.splitter)
        self.left_panel.setObjectName(u"left_panel")
        self.splitter.addWidget(self.left_panel)
        self.stage = QWebEngineView(self.splitter)
        self.stage.setObjectName(u"stage")
        self.stage.setMinimumSize(QSize(200, 200))
        self.stage.setStyleSheet(u"background-color: rgb(0, 0, 0);")
        self.stage.setUrl(QUrl(u"about:blank"))
        self.splitter.addWidget(self.stage)
        self.right_panel = QWidget(self.splitter)
        self.right_panel.setObjectName(u"right_panel")
        self.splitter.addWidget(self.right_panel)

        self.gridLayout_2.addWidget(self.splitter, 2, 0, 1, 1)


        self.gridLayout.addWidget(self.browser_tab_widget, 0, 0, 1, 1)


        self.retranslateUi(browser)

        QMetaObject.connectSlotsByName(browser)
    # setupUi

    def retranslateUi(self, browser):
        browser.setWindowTitle(QCoreApplication.translate("browser", u"Form", None))
#if QT_CONFIG(tooltip)
        self.plaintext_button.setToolTip(QCoreApplication.translate("browser", u"Plaintext", None))
#endif // QT_CONFIG(tooltip)
        self.plaintext_button.setText("")
#if QT_CONFIG(tooltip)
        self.summarize_button.setToolTip(QCoreApplication.translate("browser", u"Summarize", None))
#endif // QT_CONFIG(tooltip)
        self.summarize_button.setText("")
#if QT_CONFIG(tooltip)
        self.clear_data_button.setToolTip(QCoreApplication.translate("browser", u"Clear tab and delete this site's data", None))
#endif // QT_CONFIG(tooltip)
        self.clear_data_button.setText("")
        self.private_browse_button.setText("")
#if QT_CONFIG(tooltip)
        self.bookmark_page_button.setToolTip(QCoreApplication.translate("browser", u"Bookmark the page", None))
#endif // QT_CONFIG(tooltip)
        self.bookmark_page_button.setText("")
#if QT_CONFIG(tooltip)
        self.url.setToolTip(QCoreApplication.translate("browser", u"Enter a URL", None))
#endif // QT_CONFIG(tooltip)
        self.url.setPlaceholderText(QCoreApplication.translate("browser", u"https://", None))
#if QT_CONFIG(tooltip)
        self.submit_button.setToolTip(QCoreApplication.translate("browser", u"Submit", None))
#endif // QT_CONFIG(tooltip)
        self.submit_button.setText("")
#if QT_CONFIG(tooltip)
        self.refresh_button.setToolTip(QCoreApplication.translate("browser", u"Refresh", None))
#endif // QT_CONFIG(tooltip)
        self.refresh_button.setText("")
#if QT_CONFIG(tooltip)
        self.back_button.setToolTip(QCoreApplication.translate("browser", u"Back", None))
#endif // QT_CONFIG(tooltip)
        self.back_button.setText("")
#if QT_CONFIG(tooltip)
        self.next_button.setToolTip(QCoreApplication.translate("browser", u"Next", None))
#endif // QT_CONFIG(tooltip)
        self.next_button.setText("")
        self.bookmark_button.setText("")
        self.history_button.setText("")
#if QT_CONFIG(tooltip)
        self.user_agent_os.setToolTip(QCoreApplication.translate("browser", u"Choose OS", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.user_agent_browser.setToolTip(QCoreApplication.translate("browser", u"Choose Browser", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.pushButton.setToolTip(QCoreApplication.translate("browser", u"Random", None))
#endif // QT_CONFIG(tooltip)
        self.pushButton.setText("")
    # retranslateUi

