# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'filter_window.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QDialog,
    QDialogButtonBox, QFrame, QGridLayout, QLabel,
    QSizePolicy, QSpacerItem, QWidget)

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
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.gridLayout.addWidget(self.buttonBox, 2, 1, 1, 1)

        self.label = QLabel(filter_window)
        self.label.setObjectName(u"label")
        font1 = QFont()
        font1.setPointSize(9)
        font1.setBold(True)
        self.label.setFont(font1)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 2)

        self.auto_apply = QCheckBox(filter_window)
        self.auto_apply.setObjectName(u"auto_apply")
        font2 = QFont()
        font2.setPointSize(8)
        font2.setBold(True)
        self.auto_apply.setFont(font2)

        self.gridLayout.addWidget(self.auto_apply, 2, 0, 1, 1)

        self.content = QFrame(filter_window)
        self.content.setObjectName(u"content")
        self.content.setFont(font)
        self.content.setFrameShape(QFrame.StyledPanel)
        self.content.setFrameShadow(QFrame.Raised)
        self.gridLayout_2 = QGridLayout(self.content)
        self.gridLayout_2.setObjectName(u"gridLayout_2")

        self.gridLayout.addWidget(self.content, 1, 0, 1, 2)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 3, 1, 1, 1)


        self.retranslateUi(filter_window)
        self.buttonBox.accepted.connect(filter_window.accept)
        self.buttonBox.rejected.connect(filter_window.reject)

        QMetaObject.connectSlotsByName(filter_window)
    # setupUi

    def retranslateUi(self, filter_window):
        filter_window.setWindowTitle(QCoreApplication.translate("filter_window", u"Dialog", None))
        self.label.setText(QCoreApplication.translate("filter_window", u"Filter Name", None))
        self.auto_apply.setText(QCoreApplication.translate("filter_window", u"Auto Apply Filter", None))
    # retranslateUi

