# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'section_3_panel.ui'
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
from PySide6.QtWidgets import (QApplication, QLabel, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_section_3_panel(object):
    def setupUi(self, section_3_panel):
        if not section_3_panel.objectName():
            section_3_panel.setObjectName(u"section_3_panel")
        section_3_panel.resize(400, 400)
        self.verticalLayout = QVBoxLayout(section_3_panel)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.placeholder_label = QLabel(section_3_panel)
        self.placeholder_label.setObjectName(u"placeholder_label")
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setStyleSheet(u"font-size: 18px; font-weight: bold;")

        self.verticalLayout.addWidget(self.placeholder_label)


        self.retranslateUi(section_3_panel)

        QMetaObject.connectSlotsByName(section_3_panel)
    # setupUi

    def retranslateUi(self, section_3_panel):
        section_3_panel.setWindowTitle(QCoreApplication.translate("section_3_panel", u"Form", None))
        self.placeholder_label.setText(QCoreApplication.translate("section_3_panel", u"Section 3", None))
    # retranslateUi

