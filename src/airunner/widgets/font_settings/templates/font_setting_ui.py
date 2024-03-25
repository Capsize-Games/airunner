# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'font_setting.ui'
##
## Created by: Qt User Interface Compiler version 6.6.2
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QGroupBox,
    QSizePolicy, QSpinBox, QWidget)

class Ui_font_setting_widget(object):
    def setupUi(self, font_setting_widget):
        if not font_setting_widget.objectName():
            font_setting_widget.setObjectName(u"font_setting_widget")
        font_setting_widget.resize(400, 300)
        self.gridLayout_4 = QGridLayout(font_setting_widget)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.section = QGroupBox(font_setting_widget)
        self.section.setObjectName(u"section")
        self.gridLayout = QGridLayout(self.section)
        self.gridLayout.setObjectName(u"gridLayout")
        self.font_family = QComboBox(self.section)
        self.font_family.setObjectName(u"font_family")

        self.gridLayout.addWidget(self.font_family, 0, 0, 1, 1)

        self.size = QSpinBox(self.section)
        self.size.setObjectName(u"size")
        self.size.setMaximumSize(QSize(75, 16777215))

        self.gridLayout.addWidget(self.size, 0, 1, 1, 1)


        self.gridLayout_4.addWidget(self.section, 0, 0, 1, 1)


        self.retranslateUi(font_setting_widget)
        self.font_family.currentTextChanged.connect(font_setting_widget.font_family_changed)
        self.size.valueChanged.connect(font_setting_widget.size_changed)

        QMetaObject.connectSlotsByName(font_setting_widget)
    # setupUi

    def retranslateUi(self, font_setting_widget):
        font_setting_widget.setWindowTitle(QCoreApplication.translate("font_setting_widget", u"Form", None))
        self.section.setTitle(QCoreApplication.translate("font_setting_widget", u"Section", None))
    # retranslateUi

