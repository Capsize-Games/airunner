# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'filter_window.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QFrame, QGridLayout, QSizePolicy, QSpacerItem,
    QWidget)

class Ui_filter_window(object):
    def setupUi(self, filter_window):
        if not filter_window.objectName():
            filter_window.setObjectName(u"filter_window")
        filter_window.resize(352, 94)
        self.gridLayout = QGridLayout(filter_window)
        self.gridLayout.setObjectName(u"gridLayout")
        self.buttonBox = QDialogButtonBox(filter_window)
        self.buttonBox.setObjectName(u"buttonBox")
        font = QFont()
        font.setPointSize(8)
        self.buttonBox.setFont(font)
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.gridLayout.addWidget(self.buttonBox, 1, 1, 1, 1)

        self.content = QFrame(filter_window)
        self.content.setObjectName(u"content")
        self.content.setFont(font)
        self.content.setFrameShape(QFrame.Shape.StyledPanel)
        self.content.setFrameShadow(QFrame.Shadow.Raised)
        self.gridLayout_2 = QGridLayout(self.content)
        self.gridLayout_2.setObjectName(u"gridLayout_2")

        self.gridLayout.addWidget(self.content, 0, 0, 1, 2)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 2, 1, 1, 1)


        self.retranslateUi(filter_window)
        self.buttonBox.accepted.connect(filter_window.accept)
        self.buttonBox.rejected.connect(filter_window.reject)

        QMetaObject.connectSlotsByName(filter_window)
    # setupUi

    def retranslateUi(self, filter_window):
        filter_window.setWindowTitle(QCoreApplication.translate("filter_window", u"Dialog", None))
    # retranslateUi

