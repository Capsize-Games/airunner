# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'map.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QSpacerItem, QSplitter,
    QVBoxLayout, QWidget)

class Ui_map(object):
    def setupUi(self, map):
        if not map.objectName():
            map.setObjectName(u"map")
        map.resize(800, 600)
        self.gridLayout = QGridLayout(map)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.splitter = QSplitter(map)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.sidebarWidget = QWidget(self.splitter)
        self.sidebarWidget.setObjectName(u"sidebarWidget")
        self.sidebarWidget.setMinimumSize(QSize(250, 0))
        self.sidebarWidget.setMaximumSize(QSize(250, 16777215))
        self.sidebarLayout = QVBoxLayout(self.sidebarWidget)
        self.sidebarLayout.setObjectName(u"sidebarLayout")
        self.sidebarLayout.setContentsMargins(10, 10, 10, 10)
        self.searchLabel = QLabel(self.sidebarWidget)
        self.searchLabel.setObjectName(u"searchLabel")

        self.sidebarLayout.addWidget(self.searchLabel)

        self.searchLineEdit = QLineEdit(self.sidebarWidget)
        self.searchLineEdit.setObjectName(u"searchLineEdit")

        self.sidebarLayout.addWidget(self.searchLineEdit)

        self.searchButton = QPushButton(self.sidebarWidget)
        self.searchButton.setObjectName(u"searchButton")

        self.sidebarLayout.addWidget(self.searchButton)

        self.locateMeButton = QPushButton(self.sidebarWidget)
        self.locateMeButton.setObjectName(u"locateMeButton")

        self.sidebarLayout.addWidget(self.locateMeButton)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.sidebarLayout.addItem(self.verticalSpacer)

        self.splitter.addWidget(self.sidebarWidget)
        self.webEngineView = QWebEngineView(self.splitter)
        self.webEngineView.setObjectName(u"webEngineView")
        self.splitter.addWidget(self.webEngineView)

        self.gridLayout.addWidget(self.splitter, 0, 0, 1, 1)


        self.retranslateUi(map)

        QMetaObject.connectSlotsByName(map)
    # setupUi

    def retranslateUi(self, map):
        map.setWindowTitle(QCoreApplication.translate("map", u"Map", None))
        self.searchLabel.setText(QCoreApplication.translate("map", u"Search Location:", None))
        self.searchLineEdit.setPlaceholderText(QCoreApplication.translate("map", u"Enter location...", None))
        self.searchButton.setText(QCoreApplication.translate("map", u"Search", None))
        self.locateMeButton.setText(QCoreApplication.translate("map", u"Locate Me", None))
    # retranslateUi

