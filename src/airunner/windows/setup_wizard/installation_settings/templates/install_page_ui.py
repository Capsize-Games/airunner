# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'install_page.ui'
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

class Ui_install_page(object):
    def setupUi(self, install_page):
        if not install_page.objectName():
            install_page.setObjectName(u"install_page")
        install_page.resize(566, 375)
        self.gridLayout = QGridLayout(install_page)
        self.gridLayout.setObjectName(u"gridLayout")
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 3, 0, 1, 1)

        self.label = QLabel(install_page)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.progress_bar = QProgressBar(install_page)
        self.progress_bar.setObjectName(u"progress_bar")
        self.progress_bar.setValue(0)

        self.gridLayout.addWidget(self.progress_bar, 2, 0, 1, 1)

        self.status = QLabel(install_page)
        self.status.setObjectName(u"status")

        self.gridLayout.addWidget(self.status, 1, 0, 1, 1)


        self.retranslateUi(install_page)

        QMetaObject.connectSlotsByName(install_page)
    # setupUi

    def retranslateUi(self, install_page):
        install_page.setWindowTitle(QCoreApplication.translate("install_page", u"Form", None))
        self.label.setText(QCoreApplication.translate("install_page", u"Installing AI Runner", None))
        self.progress_bar.setFormat(QCoreApplication.translate("install_page", u"Installation progress %p%", None))
        self.status.setText("")
    # retranslateUi

