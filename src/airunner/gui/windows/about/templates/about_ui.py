# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'about.ui'
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
    QFormLayout, QLabel, QSizePolicy, QWidget)

class Ui_about_window(object):
    def setupUi(self, about_window):
        if not about_window.objectName():
            about_window.setObjectName(u"about_window")
        about_window.resize(270, 150)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(about_window.sizePolicy().hasHeightForWidth())
        about_window.setSizePolicy(sizePolicy)
        about_window.setMinimumSize(QSize(270, 150))
        about_window.setMaximumSize(QSize(270, 150))
        self.layoutWidget = QWidget(about_window)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.layoutWidget.setGeometry(QRect(10, 10, 249, 134))
        self.formLayout = QFormLayout(self.layoutWidget)
        self.formLayout.setObjectName(u"formLayout")
        self.formLayout.setContentsMargins(0, 0, 0, 0)
        self.title = QLabel(self.layoutWidget)
        self.title.setObjectName(u"title")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.title.sizePolicy().hasHeightForWidth())
        self.title.setSizePolicy(sizePolicy1)
        font = QFont()
        font.setPointSize(14)
        self.title.setFont(font)

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.title)

        self.label_3 = QLabel(self.layoutWidget)
        self.label_3.setObjectName(u"label_3")
        sizePolicy1.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy1)
        self.label_3.setMinimumSize(QSize(0, 0))
        font1 = QFont()
        font1.setPointSize(11)
        self.label_3.setFont(font1)

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.label_3)

        self.label_2 = QLabel(self.layoutWidget)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setFont(font1)

        self.formLayout.setWidget(2, QFormLayout.LabelRole, self.label_2)

        self.buttonBox = QDialogButtonBox(self.layoutWidget)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Ok)

        self.formLayout.setWidget(3, QFormLayout.LabelRole, self.buttonBox)


        self.retranslateUi(about_window)
        self.buttonBox.accepted.connect(about_window.accept)
        self.buttonBox.rejected.connect(about_window.reject)

        QMetaObject.connectSlotsByName(about_window)
    # setupUi

    def retranslateUi(self, about_window):
        about_window.setWindowTitle(QCoreApplication.translate("about_window", u"About", None))
        self.title.setText(QCoreApplication.translate("about_window", u"AI Runner v", None))
        self.label_3.setText(QCoreApplication.translate("about_window", u"Powered by open source software", None))
        self.label_2.setText(QCoreApplication.translate("about_window", u"Copyright \u00a9 2022-2025 Capsize LLC", None))
    # retranslateUi

