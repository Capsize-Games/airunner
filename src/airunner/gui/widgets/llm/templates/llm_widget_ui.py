# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'llm_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QSizePolicy, QTabWidget,
    QWidget)

from airunner.gui.widgets.llm.chat_prompt_widget import ChatPromptWidget
from airunner.gui.widgets.llm.llm_preferences_widget import LLMPreferencesWidget
from airunner.gui.widgets.llm.llm_settings_widget import LLMSettingsWidget

class Ui_llm_widget(object):
    def setupUi(self, llm_widget):
        if not llm_widget.objectName():
            llm_widget.setObjectName(u"llm_widget")
        llm_widget.resize(622, 974)
        self.gridLayout = QGridLayout(llm_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.tabWidget = QTabWidget(llm_widget)
        self.tabWidget.setObjectName(u"tabWidget")
        self.chat = QWidget()
        self.chat.setObjectName(u"chat")
        self.gridLayout_8 = QGridLayout(self.chat)
        self.gridLayout_8.setObjectName(u"gridLayout_8")
        self.gridLayout_8.setContentsMargins(0, 0, 0, 0)
        self.chat_prompt_widget = ChatPromptWidget(self.chat)
        self.chat_prompt_widget.setObjectName(u"chat_prompt_widget")

        self.gridLayout_8.addWidget(self.chat_prompt_widget, 0, 0, 1, 1)

        icon = QIcon()
        iconThemeName = u"user-available"
        if QIcon.hasThemeIcon(iconThemeName):
            icon = QIcon.fromTheme(iconThemeName)
        else:
            icon.addFile(u"../../../", QSize(), QIcon.Normal, QIcon.Off)

        self.tabWidget.addTab(self.chat, icon, "")
        self.preferences = QWidget()
        self.preferences.setObjectName(u"preferences")
        self.gridLayout_2 = QGridLayout(self.preferences)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.llm_preferences_widget = LLMPreferencesWidget(self.preferences)
        self.llm_preferences_widget.setObjectName(u"llm_preferences_widget")

        self.gridLayout_2.addWidget(self.llm_preferences_widget, 0, 0, 1, 1)

        icon1 = QIcon()
        iconThemeName = u"preferences-desktop"
        if QIcon.hasThemeIcon(iconThemeName):
            icon1 = QIcon.fromTheme(iconThemeName)
        else:
            icon1.addFile(u"../../../", QSize(), QIcon.Normal, QIcon.Off)

        self.tabWidget.addTab(self.preferences, icon1, "")
        self.settings = QWidget()
        self.settings.setObjectName(u"settings")
        self.gridLayout_5 = QGridLayout(self.settings)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.gridLayout_5.setContentsMargins(0, 0, 0, 0)
        self.llm_settings_widget = LLMSettingsWidget(self.settings)
        self.llm_settings_widget.setObjectName(u"llm_settings_widget")

        self.gridLayout_5.addWidget(self.llm_settings_widget, 0, 0, 1, 1)

        icon2 = QIcon()
        iconThemeName = u"preferences-other"
        if QIcon.hasThemeIcon(iconThemeName):
            icon2 = QIcon.fromTheme(iconThemeName)
        else:
            icon2.addFile(u"../../../", QSize(), QIcon.Normal, QIcon.Off)

        self.tabWidget.addTab(self.settings, icon2, "")

        self.gridLayout.addWidget(self.tabWidget, 0, 0, 1, 1)


        self.retranslateUi(llm_widget)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(llm_widget)
    # setupUi

    def retranslateUi(self, llm_widget):
        llm_widget.setWindowTitle(QCoreApplication.translate("llm_widget", u"Form", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.chat), QCoreApplication.translate("llm_widget", u"Chat", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.preferences), QCoreApplication.translate("llm_widget", u"Preferences", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.settings), QCoreApplication.translate("llm_widget", u"Settings", None))
    # retranslateUi

