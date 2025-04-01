# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'completion_page.ui'
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

class Ui_completion_page(object):
    def setupUi(self, completion_page):
        if not completion_page.objectName():
            completion_page.setObjectName(u"completion_page")
        completion_page.resize(400, 81)
        self.gridLayout_2 = QGridLayout(completion_page)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label = QLabel(completion_page)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        self.label.setFont(font)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer, 1, 0, 1, 1)


        self.retranslateUi(completion_page)

        QMetaObject.connectSlotsByName(completion_page)
    # setupUi

    def retranslateUi(self, completion_page):
        completion_page.setWindowTitle(QCoreApplication.translate("completion_page", u"Form", None))
        self.label.setText(QCoreApplication.translate("completion_page", u"Your installation is complete. Please use AI Runner responsibly.", None))
    # retranslateUi

