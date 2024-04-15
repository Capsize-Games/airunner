# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'download_vision_models.ui'
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
    QLineEdit, QProgressBar, QPushButton, QSizePolicy,
    QSpacerItem, QWidget)

class Ui_vision_setup(object):
    def setupUi(self, vision_setup):
        if not vision_setup.objectName():
            vision_setup.setObjectName(u"vision_setup")
        vision_setup.resize(447, 533)
        self.gridLayout = QGridLayout(vision_setup)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label = QLabel(vision_setup)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.label_2 = QLabel(vision_setup)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setWordWrap(True)

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 2)

        self.line = QFrame(vision_setup)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 2, 0, 1, 2)

        self.lineEdit = QLineEdit(vision_setup)
        self.lineEdit.setObjectName(u"lineEdit")

        self.gridLayout.addWidget(self.lineEdit, 3, 0, 1, 1)

        self.progressBar = QProgressBar(vision_setup)
        self.progressBar.setObjectName(u"progressBar")
        self.progressBar.setValue(0)

        self.gridLayout.addWidget(self.progressBar, 4, 0, 1, 1)

        self.download = QPushButton(vision_setup)
        self.download.setObjectName(u"download")

        self.gridLayout.addWidget(self.download, 5, 0, 1, 1)

        self.cancel = QPushButton(vision_setup)
        self.cancel.setObjectName(u"cancel")

        self.gridLayout.addWidget(self.cancel, 6, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 7, 1, 1, 1)


        self.retranslateUi(vision_setup)
        self.download.clicked.connect(vision_setup.download_models)
        self.cancel.clicked.connect(vision_setup.cancel)

        QMetaObject.connectSlotsByName(vision_setup)
    # setupUi

    def retranslateUi(self, vision_setup):
        vision_setup.setWindowTitle(QCoreApplication.translate("vision_setup", u"Form", None))
        self.label.setText(QCoreApplication.translate("vision_setup", u"Vision Models", None))
        self.label_2.setText(QCoreApplication.translate("vision_setup", u"This model is used for processing images from your camera feed. That content is used to enhance your conversations with chatbots. You can skip this step if you do not intend to use this feature.", None))
        self.lineEdit.setText("")
        self.download.setText(QCoreApplication.translate("vision_setup", u"Download Controlnet Models", None))
        self.cancel.setText(QCoreApplication.translate("vision_setup", u"Cancel", None))
    # retranslateUi

