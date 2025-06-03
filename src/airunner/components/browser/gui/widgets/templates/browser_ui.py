# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'browser.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (
    QCoreApplication,
    QDate,
    QDateTime,
    QLocale,
    QMetaObject,
    QObject,
    QPoint,
    QRect,
    QSize,
    QTime,
    QUrl,
    Qt,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QCursor,
    QFont,
    QFontDatabase,
    QGradient,
    QIcon,
    QImage,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPalette,
    QPixmap,
    QRadialGradient,
    QTransform,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QWidget,
)
import airunner.feather_rc


class Ui_browser(object):
    def setupUi(self, browser):
        if not browser.objectName():
            browser.setObjectName("browser")
        browser.resize(530, 551)
        self.gridLayout = QGridLayout(browser)
        self.gridLayout.setObjectName("gridLayout")
        self.browser_tab_widget = QTabWidget(browser)
        self.browser_tab_widget.setObjectName("browser_tab_widget")
        self.tab = QWidget()
        self.tab.setObjectName("tab")
        self.gridLayout_2 = QGridLayout(self.tab)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.user_agent_os = QComboBox(self.tab)
        self.user_agent_os.setObjectName("user_agent_os")

        self.gridLayout_2.addWidget(self.user_agent_os, 1, 0, 1, 1)

        self.pushButton = QPushButton(self.tab)
        self.pushButton.setObjectName("pushButton")
        sizePolicy = QSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.pushButton.sizePolicy().hasHeightForWidth()
        )
        self.pushButton.setSizePolicy(sizePolicy)
        self.pushButton.setMinimumSize(QSize(0, 0))
        icon = QIcon()
        icon.addFile(
            ":/dark/icons/feather/dark/dice-game-icon.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.pushButton.setIcon(icon)

        self.gridLayout_2.addWidget(self.pushButton, 1, 2, 1, 1)

        self.user_agent_browser = QComboBox(self.tab)
        self.user_agent_browser.setObjectName("user_agent_browser")

        self.gridLayout_2.addWidget(self.user_agent_browser, 1, 1, 1, 1)

        self.stage = QWebEngineView(self.tab)
        self.stage.setObjectName("stage")
        self.stage.setMinimumSize(QSize(200, 200))
        self.stage.setStyleSheet("background-color: rgb(0, 0, 0);")
        self.stage.setUrl(QUrl("about:blank"))

        self.gridLayout_2.addWidget(self.stage, 4, 0, 1, 3)

        self.url = QLineEdit(self.tab)
        self.url.setObjectName("url")

        self.gridLayout_2.addWidget(self.url, 0, 0, 1, 1)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.submit_button = QPushButton(self.tab)
        self.submit_button.setObjectName("submit_button")
        sizePolicy.setHeightForWidth(
            self.submit_button.sizePolicy().hasHeightForWidth()
        )
        self.submit_button.setSizePolicy(sizePolicy)
        icon1 = QIcon()
        icon1.addFile(
            ":/dark/icons/feather/dark/chevron-up.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.submit_button.setIcon(icon1)

        self.horizontalLayout_4.addWidget(self.submit_button)

        self.refresh_button = QPushButton(self.tab)
        self.refresh_button.setObjectName("refresh_button")
        sizePolicy.setHeightForWidth(
            self.refresh_button.sizePolicy().hasHeightForWidth()
        )
        self.refresh_button.setSizePolicy(sizePolicy)
        icon2 = QIcon()
        icon2.addFile(
            ":/dark/icons/feather/dark/refresh-cw.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.refresh_button.setIcon(icon2)

        self.horizontalLayout_4.addWidget(self.refresh_button)

        self.back_button = QPushButton(self.tab)
        self.back_button.setObjectName("back_button")
        sizePolicy.setHeightForWidth(
            self.back_button.sizePolicy().hasHeightForWidth()
        )
        self.back_button.setSizePolicy(sizePolicy)
        icon3 = QIcon()
        icon3.addFile(
            ":/dark/icons/feather/dark/arrow-left-circle.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.back_button.setIcon(icon3)

        self.horizontalLayout_4.addWidget(self.back_button)

        self.next_button = QPushButton(self.tab)
        self.next_button.setObjectName("next_button")
        sizePolicy.setHeightForWidth(
            self.next_button.sizePolicy().hasHeightForWidth()
        )
        self.next_button.setSizePolicy(sizePolicy)
        icon4 = QIcon()
        icon4.addFile(
            ":/dark/icons/feather/dark/arrow-right-circle.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.next_button.setIcon(icon4)

        self.horizontalLayout_4.addWidget(self.next_button)

        self.plaintext_button = QPushButton(self.tab)
        self.plaintext_button.setObjectName("plaintext_button")
        sizePolicy.setHeightForWidth(
            self.plaintext_button.sizePolicy().hasHeightForWidth()
        )
        self.plaintext_button.setSizePolicy(sizePolicy)
        icon5 = QIcon()
        icon5.addFile(
            ":/dark/icons/feather/dark/align-justify.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.plaintext_button.setIcon(icon5)
        self.plaintext_button.setCheckable(True)

        self.horizontalLayout_4.addWidget(self.plaintext_button)

        self.summarize_button = QPushButton(self.tab)
        self.summarize_button.setObjectName("summarize_button")
        sizePolicy.setHeightForWidth(
            self.summarize_button.sizePolicy().hasHeightForWidth()
        )
        self.summarize_button.setSizePolicy(sizePolicy)
        icon6 = QIcon()
        icon6.addFile(
            ":/dark/icons/feather/dark/list.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.summarize_button.setIcon(icon6)
        self.summarize_button.setCheckable(True)

        self.horizontalLayout_4.addWidget(self.summarize_button)

        self.clear_data_button = QPushButton(self.tab)
        self.clear_data_button.setObjectName("clear_data_button")
        sizePolicy.setHeightForWidth(
            self.clear_data_button.sizePolicy().hasHeightForWidth()
        )
        self.clear_data_button.setSizePolicy(sizePolicy)
        icon7 = QIcon()
        icon7.addFile(
            ":/dark/icons/feather/dark/trash-2.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.clear_data_button.setIcon(icon7)

        self.horizontalLayout_4.addWidget(self.clear_data_button)

        self.gridLayout_2.addLayout(self.horizontalLayout_4, 0, 1, 1, 2)

        self.browser_tab_widget.addTab(self.tab, "")

        self.gridLayout.addWidget(self.browser_tab_widget, 2, 0, 1, 3)

        self.retranslateUi(browser)

        self.browser_tab_widget.setCurrentIndex(0)

        QMetaObject.connectSlotsByName(browser)

    # setupUi

    def retranslateUi(self, browser):
        browser.setWindowTitle(
            QCoreApplication.translate("browser", "Form", None)
        )
        # if QT_CONFIG(tooltip)
        self.user_agent_os.setToolTip(
            QCoreApplication.translate("browser", "Choose OS", None)
        )
        # endif // QT_CONFIG(tooltip)
        # if QT_CONFIG(tooltip)
        self.pushButton.setToolTip(
            QCoreApplication.translate("browser", "Random", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.pushButton.setText("")
        # if QT_CONFIG(tooltip)
        self.user_agent_browser.setToolTip(
            QCoreApplication.translate("browser", "Choose Browser", None)
        )
        # endif // QT_CONFIG(tooltip)
        # if QT_CONFIG(tooltip)
        self.url.setToolTip(
            QCoreApplication.translate("browser", "Enter a URL", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.url.setPlaceholderText(
            QCoreApplication.translate("browser", "https://", None)
        )
        # if QT_CONFIG(tooltip)
        self.submit_button.setToolTip(
            QCoreApplication.translate("browser", "Submit", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.submit_button.setText("")
        # if QT_CONFIG(tooltip)
        self.refresh_button.setToolTip(
            QCoreApplication.translate("browser", "Refresh", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.refresh_button.setText("")
        # if QT_CONFIG(tooltip)
        self.back_button.setToolTip(
            QCoreApplication.translate("browser", "Back", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.back_button.setText("")
        # if QT_CONFIG(tooltip)
        self.next_button.setToolTip(
            QCoreApplication.translate("browser", "Next", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.next_button.setText("")
        # if QT_CONFIG(tooltip)
        self.plaintext_button.setToolTip(
            QCoreApplication.translate("browser", "Plaintext", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.plaintext_button.setText("")
        # if QT_CONFIG(tooltip)
        self.summarize_button.setToolTip(
            QCoreApplication.translate("browser", "Summarize", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.summarize_button.setText("")
        # if QT_CONFIG(tooltip)
        self.clear_data_button.setToolTip(
            QCoreApplication.translate("browser", "Clear website", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.clear_data_button.setText("")
        self.browser_tab_widget.setTabText(
            self.browser_tab_widget.indexOf(self.tab),
            QCoreApplication.translate("browser", "New Tab", None),
        )

    # retranslateUi
