# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'file_explorer.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QHeaderView, QLabel,
    QSizePolicy, QTreeView, QWidget)

class Ui_file_explorer(object):
    def setupUi(self, file_explorer):
        if not file_explorer.objectName():
            file_explorer.setObjectName(u"file_explorer")
        file_explorer.resize(400, 300)
        self.gridLayout = QGridLayout(file_explorer)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.widget = QWidget(file_explorer)
        self.widget.setObjectName(u"widget")
        self.gridLayout_2 = QGridLayout(self.widget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label = QLabel(self.widget)
        self.label.setObjectName(u"label")

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.widget, 0, 0, 1, 1)

        self.treeView = QTreeView(file_explorer)
        self.treeView.setObjectName(u"treeView")

        self.gridLayout.addWidget(self.treeView, 1, 0, 1, 1)


        self.retranslateUi(file_explorer)

        QMetaObject.connectSlotsByName(file_explorer)
    # setupUi

    def retranslateUi(self, file_explorer):
        file_explorer.setWindowTitle(QCoreApplication.translate("file_explorer", u"Form", None))
        self.label.setText(QCoreApplication.translate("file_explorer", u"Explorer", None))
    # retranslateUi

