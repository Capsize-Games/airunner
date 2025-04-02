# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'voice_settings.ui'
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
from PySide6.QtWidgets import (QApplication, QPushButton, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_voice_settings(object):
    def setupUi(self, voice_settings):
        if not voice_settings.objectName():
            voice_settings.setObjectName(u"voice_settings")
        voice_settings.resize(512, 576)
        self.verticalLayout = QVBoxLayout(voice_settings)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.voice_scroll_area = QScrollArea(voice_settings)
        self.voice_scroll_area.setObjectName(u"voice_scroll_area")
        self.voice_scroll_area.setWidgetResizable(True)
        self.voice_scroll_area_contents = QWidget()
        self.voice_scroll_area_contents.setObjectName(u"voice_scroll_area_contents")
        self.voice_scroll_area_contents.setGeometry(QRect(0, 0, 480, 200))
        self.voice_list_layout = QVBoxLayout(self.voice_scroll_area_contents)
        self.voice_list_layout.setObjectName(u"voice_list_layout")
        self.voice_scroll_area.setWidget(self.voice_scroll_area_contents)

        self.verticalLayout.addWidget(self.voice_scroll_area)

        self.create_voice_button = QPushButton(voice_settings)
        self.create_voice_button.setObjectName(u"create_voice_button")

        self.verticalLayout.addWidget(self.create_voice_button)


        self.retranslateUi(voice_settings)

        QMetaObject.connectSlotsByName(voice_settings)
    # setupUi

    def retranslateUi(self, voice_settings):
        voice_settings.setWindowTitle(QCoreApplication.translate("voice_settings", u"Voice Settings", None))
        self.create_voice_button.setText(QCoreApplication.translate("voice_settings", u"Create Voice", None))
    # retranslateUi

