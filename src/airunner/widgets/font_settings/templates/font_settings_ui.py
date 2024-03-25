# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'font_settings.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QSizePolicy, QWidget)

from airunner.widgets.font_settings.font_setting_widget import FontSettingWidget

class Ui_font_settings_widget(object):
    def setupUi(self, font_settings_widget):
        if not font_settings_widget.objectName():
            font_settings_widget.setObjectName(u"font_settings_widget")
        font_settings_widget.resize(512, 341)
        self.gridLayout_2 = QGridLayout(font_settings_widget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.widget = FontSettingWidget(font_settings_widget)
        self.widget.setObjectName(u"widget")

        self.gridLayout_2.addWidget(self.widget, 0, 0, 1, 1)


        self.retranslateUi(font_settings_widget)

        QMetaObject.connectSlotsByName(font_settings_widget)
    # setupUi

    def retranslateUi(self, font_settings_widget):
        font_settings_widget.setWindowTitle(QCoreApplication.translate("font_settings_widget", u"Form", None))
        self.widget.setProperty("section", QCoreApplication.translate("font_settings_widget", u"chat", None))
    # retranslateUi

