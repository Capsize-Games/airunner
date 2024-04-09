# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'controlnet.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QHeaderView,
    QLabel, QPushButton, QSizePolicy, QSpacerItem,
    QTableWidget, QTableWidgetItem, QWidget)

class Ui_controlnet_download(object):
    def setupUi(self, controlnet_download):
        if not controlnet_download.objectName():
            controlnet_download.setObjectName(u"controlnet_download")
        controlnet_download.resize(566, 442)
        self.gridLayout = QGridLayout(controlnet_download)
        self.gridLayout.setObjectName(u"gridLayout")
        self.line = QFrame(controlnet_download)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.gridLayout.addWidget(self.line, 2, 0, 1, 1)

        self.tableWidget = QTableWidget(controlnet_download)
        self.tableWidget.setObjectName(u"tableWidget")

        self.gridLayout.addWidget(self.tableWidget, 3, 0, 1, 1)

        self.label_2 = QLabel(controlnet_download)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setWordWrap(True)

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.cancel = QPushButton(controlnet_download)
        self.cancel.setObjectName(u"cancel")

        self.gridLayout.addWidget(self.cancel, 5, 0, 1, 1)

        self.label = QLabel(controlnet_download)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.download = QPushButton(controlnet_download)
        self.download.setObjectName(u"download")

        self.gridLayout.addWidget(self.download, 4, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 7, 0, 1, 1)


        self.retranslateUi(controlnet_download)
        self.download.clicked.connect(controlnet_download.download_models)
        self.cancel.clicked.connect(controlnet_download.cancel)

        QMetaObject.connectSlotsByName(controlnet_download)
    # setupUi

    def retranslateUi(self, controlnet_download):
        controlnet_download.setWindowTitle(QCoreApplication.translate("controlnet_download", u"Form", None))
        self.label_2.setText(QCoreApplication.translate("controlnet_download", u"These models allow for greater control over the output of your AI Art and are required for AI Runner to function properly", None))
        self.cancel.setText(QCoreApplication.translate("controlnet_download", u"Cancel", None))
        self.label.setText(QCoreApplication.translate("controlnet_download", u"Stable Diffusion: Controlnet", None))
        self.download.setText(QCoreApplication.translate("controlnet_download", u"Download Controlnet Models", None))
    # retranslateUi

