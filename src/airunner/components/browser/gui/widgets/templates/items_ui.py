# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'items.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QLabel, QListView,
    QSizePolicy, QWidget)

class Ui_items_widget(object):
    def setupUi(self, items_widget):
        if not items_widget.objectName():
            items_widget.setObjectName(u"items_widget")
        items_widget.resize(400, 300)
        self.gridLayout = QGridLayout(items_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label = QLabel(items_widget)
        self.label.setObjectName(u"label")

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.items = QListView(items_widget)
        self.items.setObjectName(u"items")

        self.gridLayout.addWidget(self.items, 1, 0, 1, 1)


        self.retranslateUi(items_widget)

        QMetaObject.connectSlotsByName(items_widget)
    # setupUi

    def retranslateUi(self, items_widget):
        items_widget.setWindowTitle(QCoreApplication.translate("items_widget", u"Form", None))
        self.label.setText(QCoreApplication.translate("items_widget", u"Section", None))
    # retranslateUi

