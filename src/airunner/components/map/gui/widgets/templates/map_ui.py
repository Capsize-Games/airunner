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
from PySide6.QtWidgets import (QApplication, QGridLayout, QSizePolicy, QWidget)
class Ui_map(object):
    def setupUi(self, map):
        if not map.objectName():
            map.setObjectName(u"map")
        map.resize(800, 600)
        self.gridLayout = QGridLayout(map)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.webEngineView = QWebEngineView(map)
        self.webEngineView.setObjectName(u"webEngineView")

        self.gridLayout.addWidget(self.webEngineView, 0, 0, 1, 1)


        self.retranslateUi(map)

        QMetaObject.connectSlotsByName(map)
    # setupUi

    def retranslateUi(self, map):
        map.setWindowTitle(QCoreApplication.translate("map", u"Map", None))
    # retranslateUi

