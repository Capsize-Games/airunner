# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'download_page.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QLabel, QProgressBar,
    QSizePolicy, QSpacerItem, QWidget)

class Ui_download_page(object):
    def setupUi(self, download_page):
        if not download_page.objectName():
            download_page.setObjectName(u"download_page")
        download_page.resize(400, 133)
        self.gridLayout_2 = QGridLayout(download_page)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.progressBar = QProgressBar(download_page)
        self.progressBar.setObjectName(u"progressBar")
        self.progressBar.setValue(24)

        self.gridLayout_2.addWidget(self.progressBar, 2, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer, 3, 0, 1, 1)

        self.label = QLabel(download_page)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)

        self.status_label = QLabel(download_page)
        self.status_label.setObjectName(u"status_label")

        self.gridLayout_2.addWidget(self.status_label, 1, 0, 1, 1)


        self.retranslateUi(download_page)

        QMetaObject.connectSlotsByName(download_page)
    # setupUi

    def retranslateUi(self, download_page):
        download_page.setWindowTitle(QCoreApplication.translate("download_page", u"Form", None))
        self.label.setText(QCoreApplication.translate("download_page", u"Installing AI Runner", None))
        self.status_label.setText(QCoreApplication.translate("download_page", u"Status Label", None))
    # retranslateUi

