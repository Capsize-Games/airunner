# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'status.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel,
    QSizePolicy, QWidget)

class Ui_status_widget(object):
    def setupUi(self, status_widget):
        if not status_widget.objectName():
            status_widget.setObjectName(u"status_widget")
        status_widget.resize(1123, 84)
        status_widget.setStyleSheet(u"font-size: 12px")
        self.horizontalLayout = QHBoxLayout(status_widget)
        self.horizontalLayout.setSpacing(5)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 10, 0)
        self.system_message = QLabel(status_widget)
        self.system_message.setObjectName(u"system_message")
        self.system_message.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout.addWidget(self.system_message)

        self.line_4 = QFrame(status_widget)
        self.line_4.setObjectName(u"line_4")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.line_4.sizePolicy().hasHeightForWidth())
        self.line_4.setSizePolicy(sizePolicy)
        self.line_4.setFrameShape(QFrame.Shape.VLine)
        self.line_4.setFrameShadow(QFrame.Shadow.Sunken)

        self.horizontalLayout.addWidget(self.line_4)

        self.cuda_status = QLabel(status_widget)
        self.cuda_status.setObjectName(u"cuda_status")
        self.cuda_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout.addWidget(self.cuda_status)

        self.line = QFrame(status_widget)
        self.line.setObjectName(u"line")
        sizePolicy.setHeightForWidth(self.line.sizePolicy().hasHeightForWidth())
        self.line.setSizePolicy(sizePolicy)
        self.line.setFrameShape(QFrame.Shape.VLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.horizontalLayout.addWidget(self.line)

        self.nsfw_status = QLabel(status_widget)
        self.nsfw_status.setObjectName(u"nsfw_status")
        self.nsfw_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout.addWidget(self.nsfw_status)

        self.nsfw_line = QFrame(status_widget)
        self.nsfw_line.setObjectName(u"nsfw_line")
        sizePolicy.setHeightForWidth(self.nsfw_line.sizePolicy().hasHeightForWidth())
        self.nsfw_line.setSizePolicy(sizePolicy)
        self.nsfw_line.setFrameShape(QFrame.Shape.VLine)
        self.nsfw_line.setFrameShadow(QFrame.Shadow.Sunken)

        self.horizontalLayout.addWidget(self.nsfw_line)

        self.pipeline_label = QLabel(status_widget)
        self.pipeline_label.setObjectName(u"pipeline_label")
        self.pipeline_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout.addWidget(self.pipeline_label)

        self.pipeline_divider = QFrame(status_widget)
        self.pipeline_divider.setObjectName(u"pipeline_divider")
        self.pipeline_divider.setFrameShape(QFrame.Shape.VLine)
        self.pipeline_divider.setFrameShadow(QFrame.Shadow.Sunken)

        self.horizontalLayout.addWidget(self.pipeline_divider)

        self.sd_status = QLabel(status_widget)
        self.sd_status.setObjectName(u"sd_status")
        font = QFont()
        font.setBold(True)
        self.sd_status.setFont(font)
        self.sd_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout.addWidget(self.sd_status)

        self.controlnet_status = QLabel(status_widget)
        self.controlnet_status.setObjectName(u"controlnet_status")
        self.controlnet_status.setFont(font)
        self.controlnet_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout.addWidget(self.controlnet_status)

        self.line_2 = QFrame(status_widget)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.VLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.horizontalLayout.addWidget(self.line_2)

        self.llm_status = QLabel(status_widget)
        self.llm_status.setObjectName(u"llm_status")
        self.llm_status.setFont(font)
        self.llm_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout.addWidget(self.llm_status)

        self.tts_status = QLabel(status_widget)
        self.tts_status.setObjectName(u"tts_status")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.tts_status.sizePolicy().hasHeightForWidth())
        self.tts_status.setSizePolicy(sizePolicy1)
        self.tts_status.setFont(font)
        self.tts_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout.addWidget(self.tts_status)

        self.stt_status = QLabel(status_widget)
        self.stt_status.setObjectName(u"stt_status")
        self.stt_status.setFont(font)
        self.stt_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout.addWidget(self.stt_status)


        self.retranslateUi(status_widget)

        QMetaObject.connectSlotsByName(status_widget)
    # setupUi

    def retranslateUi(self, status_widget):
        status_widget.setWindowTitle(QCoreApplication.translate("status_widget", u"Form", None))
        self.system_message.setText(QCoreApplication.translate("status_widget", u"system message", None))
        self.cuda_status.setText(QCoreApplication.translate("status_widget", u"NVIDIA", None))
        self.nsfw_status.setText(QCoreApplication.translate("status_widget", u"Safety Checker", None))
        self.pipeline_label.setText(QCoreApplication.translate("status_widget", u"pipeline", None))
        self.sd_status.setText(QCoreApplication.translate("status_widget", u"SD", None))
        self.controlnet_status.setText(QCoreApplication.translate("status_widget", u"CN", None))
        self.llm_status.setText(QCoreApplication.translate("status_widget", u"LLM", None))
        self.tts_status.setText(QCoreApplication.translate("status_widget", u"TTS", None))
        self.stt_status.setText(QCoreApplication.translate("status_widget", u"STT", None))
    # retranslateUi

