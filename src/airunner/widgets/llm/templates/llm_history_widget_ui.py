# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'llm_history_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QScrollArea, QSizePolicy,
    QWidget)

class Ui_llm_history_widget(object):
    def setupUi(self, llm_history_widget):
        if not llm_history_widget.objectName():
            llm_history_widget.setObjectName(u"llm_history_widget")
        llm_history_widget.resize(689, 545)
        self.gridLayout = QGridLayout(llm_history_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(0)
        self.gridLayout.setVerticalSpacing(10)
        self.gridLayout.setContentsMargins(0, 10, 0, 0)
        self.conversations_scroll_area = QScrollArea(llm_history_widget)
        self.conversations_scroll_area.setObjectName(u"conversations_scroll_area")
        self.conversations_scroll_area.setMinimumSize(QSize(0, 50))
        self.conversations_scroll_area.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 687, 533))
        self.gridLayout_2 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setHorizontalSpacing(0)
        self.gridLayout_2.setVerticalSpacing(10)
        self.gridLayout_2.setContentsMargins(0, 0, 10, 10)
        self.conversations_scroll_area.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout.addWidget(self.conversations_scroll_area, 0, 0, 1, 1)


        self.retranslateUi(llm_history_widget)

        QMetaObject.connectSlotsByName(llm_history_widget)
    # setupUi

    def retranslateUi(self, llm_history_widget):
        llm_history_widget.setWindowTitle(QCoreApplication.translate("llm_history_widget", u"Form", None))
    # retranslateUi

