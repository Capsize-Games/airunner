# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'install_success_page.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QLabel, QSizePolicy,
    QSpacerItem, QWidget)

class Ui_install_success_page(object):
    def setupUi(self, install_success_page):
        if not install_success_page.objectName():
            install_success_page.setObjectName(u"install_success_page")
        install_success_page.resize(566, 375)
        self.gridLayout = QGridLayout(install_success_page)
        self.gridLayout.setObjectName(u"gridLayout")
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 2, 0, 1, 1)

        self.label_2 = QLabel(install_success_page)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setWordWrap(True)

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.label = QLabel(install_success_page)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)


        self.retranslateUi(install_success_page)

        QMetaObject.connectSlotsByName(install_success_page)
    # setupUi

    def retranslateUi(self, install_success_page):
        install_success_page.setWindowTitle(QCoreApplication.translate("install_success_page", u"Form", None))
        self.label_2.setText(QCoreApplication.translate("install_success_page", u"Click finish and run AI Runner to begin using the application.", None))
        self.label.setText(QCoreApplication.translate("install_success_page", u"Installation Success!", None))
    # retranslateUi

