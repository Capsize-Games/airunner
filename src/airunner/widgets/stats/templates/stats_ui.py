# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'stats.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QHeaderView, QSizePolicy,
    QSplitter, QTableWidget, QTableWidgetItem, QTextEdit,
    QWidget)

class Ui_stats_widget(object):
    def setupUi(self, stats_widget):
        if not stats_widget.objectName():
            stats_widget.setObjectName(u"stats_widget")
        stats_widget.resize(527, 664)
        self.gridLayout = QGridLayout(stats_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.splitter = QSplitter(stats_widget)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Vertical)
        self.memory_stats = QTableWidget(self.splitter)
        self.memory_stats.setObjectName(u"memory_stats")
        self.splitter.addWidget(self.memory_stats)
        self.console = QTextEdit(self.splitter)
        self.console.setObjectName(u"console")
        self.splitter.addWidget(self.console)

        self.gridLayout.addWidget(self.splitter, 0, 0, 1, 1)


        self.retranslateUi(stats_widget)

        QMetaObject.connectSlotsByName(stats_widget)
    # setupUi

    def retranslateUi(self, stats_widget):
        stats_widget.setWindowTitle(QCoreApplication.translate("stats_widget", u"Form", None))
    # retranslateUi

