# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'stt_setup.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QLabel,
    QPushButton, QSizePolicy, QSpacerItem, QWidget)

class Ui_stt_setup(object):
    def setupUi(self, stt_setup):
        if not stt_setup.objectName():
            stt_setup.setObjectName(u"stt_setup")
        stt_setup.resize(566, 442)
        self.gridLayout = QGridLayout(stt_setup)
        self.gridLayout.setObjectName(u"gridLayout")
        self.line = QFrame(stt_setup)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 2, 0, 1, 1)

        self.label_2 = QLabel(stt_setup)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setWordWrap(True)

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.cancel = QPushButton(stt_setup)
        self.cancel.setObjectName(u"cancel")

        self.gridLayout.addWidget(self.cancel, 4, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 6, 0, 1, 1)

        self.label = QLabel(stt_setup)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.download = QPushButton(stt_setup)
        self.download.setObjectName(u"download")

        self.gridLayout.addWidget(self.download, 3, 0, 1, 1)


        self.retranslateUi(stt_setup)
        self.download.clicked.connect(stt_setup.download_models)
        self.cancel.clicked.connect(stt_setup.cancel)

        QMetaObject.connectSlotsByName(stt_setup)
    # setupUi

    def retranslateUi(self, stt_setup):
        stt_setup.setWindowTitle(QCoreApplication.translate("stt_setup", u"Form", None))
        self.label_2.setText(QCoreApplication.translate("stt_setup", u"Download whisper", None))
        self.cancel.setText(QCoreApplication.translate("stt_setup", u"Cancel", None))
        self.label.setText(QCoreApplication.translate("stt_setup", u"Speech-To-Text Model", None))
        self.download.setText(QCoreApplication.translate("stt_setup", u"Download", None))
    # retranslateUi

