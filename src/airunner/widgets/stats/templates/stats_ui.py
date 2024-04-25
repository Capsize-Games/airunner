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
from PySide6.QtWidgets import (QApplication, QGridLayout, QHeaderView, QPushButton,
    QSizePolicy, QSplitter, QTableWidget, QTableWidgetItem,
    QTextEdit, QWidget)

class Ui_stats_widget(object):
    def setupUi(self, stats_widget):
        if not stats_widget.objectName():
            stats_widget.setObjectName(u"stats_widget")
        stats_widget.resize(527, 664)
        self.gridLayout_2 = QGridLayout(stats_widget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.splitter = QSplitter(stats_widget)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Vertical)
        self.widget = QWidget(self.splitter)
        self.widget.setObjectName(u"widget")
        self.gridLayout = QGridLayout(self.widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.model_stats = QTableWidget(self.widget)
        self.model_stats.setObjectName(u"model_stats")

        self.gridLayout.addWidget(self.model_stats, 0, 0, 1, 2)

        self.pushButton = QPushButton(self.widget)
        self.pushButton.setObjectName(u"pushButton")

        self.gridLayout.addWidget(self.pushButton, 1, 0, 1, 1)

        self.pushButton_2 = QPushButton(self.widget)
        self.pushButton_2.setObjectName(u"pushButton_2")

        self.gridLayout.addWidget(self.pushButton_2, 1, 1, 1, 1)

        self.splitter.addWidget(self.widget)
        self.console = QTextEdit(self.splitter)
        self.console.setObjectName(u"console")
        self.splitter.addWidget(self.console)

        self.gridLayout_2.addWidget(self.splitter, 0, 0, 1, 1)


        self.retranslateUi(stats_widget)
        self.pushButton.clicked.connect(stats_widget.load_all)
        self.pushButton_2.clicked.connect(stats_widget.unload_all)

        QMetaObject.connectSlotsByName(stats_widget)
    # setupUi

    def retranslateUi(self, stats_widget):
        stats_widget.setWindowTitle(QCoreApplication.translate("stats_widget", u"Form", None))
        self.pushButton.setText(QCoreApplication.translate("stats_widget", u"Load all", None))
        self.pushButton_2.setText(QCoreApplication.translate("stats_widget", u"Unload all", None))
    # retranslateUi

