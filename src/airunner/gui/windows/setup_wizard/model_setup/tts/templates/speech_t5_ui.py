# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'speech_t5.ui'
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

class Ui_speecht5_setup(object):
    def setupUi(self, speecht5_setup):
        if not speecht5_setup.objectName():
            speecht5_setup.setObjectName(u"speecht5_setup")
        speecht5_setup.resize(566, 442)
        self.gridLayout = QGridLayout(speecht5_setup)
        self.gridLayout.setObjectName(u"gridLayout")
        self.line = QFrame(speecht5_setup)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 2, 0, 1, 1)

        self.label_2 = QLabel(speecht5_setup)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setWordWrap(True)

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.cancel = QPushButton(speecht5_setup)
        self.cancel.setObjectName(u"cancel")

        self.gridLayout.addWidget(self.cancel, 4, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 6, 0, 1, 1)

        self.label = QLabel(speecht5_setup)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.download = QPushButton(speecht5_setup)
        self.download.setObjectName(u"download")

        self.gridLayout.addWidget(self.download, 3, 0, 1, 1)


        self.retranslateUi(speecht5_setup)
        self.download.clicked.connect(speecht5_setup.download_models)
        self.cancel.clicked.connect(speecht5_setup.cancel)

        QMetaObject.connectSlotsByName(speecht5_setup)
    # setupUi

    def retranslateUi(self, speecht5_setup):
        speecht5_setup.setWindowTitle(QCoreApplication.translate("speecht5_setup", u"Form", None))
        self.label_2.setText(QCoreApplication.translate("speecht5_setup", u"Download the models required for text to speech using the SpeechT5 model", None))
        self.cancel.setText(QCoreApplication.translate("speecht5_setup", u"Cancel", None))
        self.label.setText(QCoreApplication.translate("speecht5_setup", u"SpeechT5", None))
        self.download.setText(QCoreApplication.translate("speecht5_setup", u"Download", None))
    # retranslateUi

