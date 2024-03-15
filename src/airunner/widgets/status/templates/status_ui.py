# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'status.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel,
    QSizePolicy, QWidget)

class Ui_status_widget(object):
    def setupUi(self, status_widget):
        if not status_widget.objectName():
            status_widget.setObjectName(u"status_widget")
        status_widget.resize(700, 44)
        status_widget.setStyleSheet(u"font-size: 12px")
        self.horizontalLayout = QHBoxLayout(status_widget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 9, 0)
        self.system_message = QLabel(status_widget)
        self.system_message.setObjectName(u"system_message")

        self.horizontalLayout.addWidget(self.system_message)

        self.line_5 = QFrame(status_widget)
        self.line_5.setObjectName(u"line_5")
        self.line_5.setFrameShape(QFrame.VLine)
        self.line_5.setFrameShadow(QFrame.Sunken)

        self.horizontalLayout.addWidget(self.line_5)

        self.queue_stats = QLabel(status_widget)
        self.queue_stats.setObjectName(u"queue_stats")

        self.horizontalLayout.addWidget(self.queue_stats)

        self.nsfw_line = QFrame(status_widget)
        self.nsfw_line.setObjectName(u"nsfw_line")
        self.nsfw_line.setFrameShape(QFrame.VLine)
        self.nsfw_line.setFrameShadow(QFrame.Sunken)

        self.horizontalLayout.addWidget(self.nsfw_line)

        self.nsfw_status = QLabel(status_widget)
        self.nsfw_status.setObjectName(u"nsfw_status")

        self.horizontalLayout.addWidget(self.nsfw_status)

        self.line_4 = QFrame(status_widget)
        self.line_4.setObjectName(u"line_4")
        self.line_4.setFrameShape(QFrame.VLine)
        self.line_4.setFrameShadow(QFrame.Sunken)

        self.horizontalLayout.addWidget(self.line_4)

        self.cuda_status = QLabel(status_widget)
        self.cuda_status.setObjectName(u"cuda_status")

        self.horizontalLayout.addWidget(self.cuda_status)

        self.line = QFrame(status_widget)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.VLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.horizontalLayout.addWidget(self.line)

        self.ram_stats = QLabel(status_widget)
        self.ram_stats.setObjectName(u"ram_stats")

        self.horizontalLayout.addWidget(self.ram_stats)

        self.line_3 = QFrame(status_widget)
        self.line_3.setObjectName(u"line_3")
        self.line_3.setFrameShape(QFrame.VLine)
        self.line_3.setFrameShadow(QFrame.Sunken)

        self.horizontalLayout.addWidget(self.line_3)

        self.vram_stats = QLabel(status_widget)
        self.vram_stats.setObjectName(u"vram_stats")

        self.horizontalLayout.addWidget(self.vram_stats)


        self.retranslateUi(status_widget)

        QMetaObject.connectSlotsByName(status_widget)
    # setupUi

    def retranslateUi(self, status_widget):
        status_widget.setWindowTitle(QCoreApplication.translate("status_widget", u"Form", None))
        self.system_message.setText(QCoreApplication.translate("status_widget", u"system message", None))
        self.queue_stats.setText(QCoreApplication.translate("status_widget", u"queue", None))
        self.nsfw_status.setText(QCoreApplication.translate("status_widget", u"nsfw", None))
        self.cuda_status.setText(QCoreApplication.translate("status_widget", u"gpu", None))
        self.ram_stats.setText(QCoreApplication.translate("status_widget", u"ram", None))
        self.vram_stats.setText(QCoreApplication.translate("status_widget", u"vram", None))
    # retranslateUi

