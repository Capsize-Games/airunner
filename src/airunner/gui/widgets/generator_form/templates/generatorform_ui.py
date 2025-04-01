# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'generatorform.ui'
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
class Ui_generator_form(object):
    def setupUi(self, generator_form):
        if not generator_form.objectName():
            generator_form.setObjectName(u"generator_form")
        generator_form.resize(620, 942)
        font = QFont()
        font.setPointSize(8)
        generator_form.setFont(font)
        generator_form.setCursor(QCursor(Qt.PointingHandCursor))
        self.gridLayout_4 = QGridLayout(generator_form)
        self.gridLayout_4.setSpacing(0)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.gridLayout_4.setContentsMargins(0, 0, 0, 0)
        self.generator_form_tabs = QTabWidget(generator_form)
        self.generator_form_tabs.setObjectName(u"generator_form_tabs")
        self.generator_form_tabs.setTabsClosable(False)
        self.generator_form_tabs.setMovable(False)
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        self.gridLayout_5 = QGridLayout(self.tab_2)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.gridLayout_7 = QGridLayout()
        self.gridLayout_7.setObjectName(u"gridLayout_7")
        self.gridLayout_7.setHorizontalSpacing(0)
        self.gridLayout_7.setVerticalSpacing(10)
        self.chat_prompt_widget = ChatPromptWidget(self.tab_2)
        self.chat_prompt_widget.setObjectName(u"chat_prompt_widget")

        self.gridLayout_7.addWidget(self.chat_prompt_widget, 0, 0, 1, 1)


        self.gridLayout_5.addLayout(self.gridLayout_7, 0, 0, 1, 1)

        self.generator_form_tabs.addTab(self.tab_2, "")

        self.gridLayout_4.addWidget(self.generator_form_tabs, 0, 0, 1, 1)


        self.retranslateUi(generator_form)

        self.generator_form_tabs.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(generator_form)
    # setupUi

    def retranslateUi(self, generator_form):
        generator_form.setWindowTitle(QCoreApplication.translate("generator_form", u"Form", None))
        self.generator_form_tabs.setTabText(self.generator_form_tabs.indexOf(self.tab_2), QCoreApplication.translate("generator_form", u"Chat", None))
    # retranslateUi

