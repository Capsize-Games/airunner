# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'update.ui'
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

class Ui_update_available(object):
    def setupUi(self, update_available):
        if not update_available.objectName():
            update_available.setObjectName(u"update_available")
        update_available.resize(327, 151)
        self.layoutWidget = QWidget(update_available)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.layoutWidget.setGeometry(QRect(10, 10, 309, 124))
        self.formLayout = QFormLayout(self.layoutWidget)
        self.formLayout.setObjectName(u"formLayout")
        self.formLayout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.layoutWidget)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(14)
        font.setBold(False)
        self.label.setFont(font)

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.label)

        self.current_version_label = QLabel(self.layoutWidget)
        self.current_version_label.setObjectName(u"current_version_label")

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.current_version_label)

        self.latest_version_label = QLabel(self.layoutWidget)
        self.latest_version_label.setObjectName(u"latest_version_label")

        self.formLayout.setWidget(2, QFormLayout.LabelRole, self.latest_version_label)

        self.label_2 = QLabel(self.layoutWidget)
        self.label_2.setObjectName(u"label_2")

        self.formLayout.setWidget(3, QFormLayout.LabelRole, self.label_2)

        self.buttonBox = QDialogButtonBox(self.layoutWidget)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.formLayout.setWidget(4, QFormLayout.LabelRole, self.buttonBox)


        self.retranslateUi(update_available)
        self.buttonBox.accepted.connect(update_available.accept)
        self.buttonBox.rejected.connect(update_available.reject)

        QMetaObject.connectSlotsByName(update_available)
    # setupUi

    def retranslateUi(self, update_available):
        update_available.setWindowTitle(QCoreApplication.translate("update_available", u"Update Available", None))
        self.label.setText(QCoreApplication.translate("update_available", u"New Version of AI Runner available", None))
        self.current_version_label.setText(QCoreApplication.translate("update_available", u"You are currently running version", None))
        self.latest_version_label.setText(QCoreApplication.translate("update_available", u"The latest version is", None))
        self.label_2.setText(QCoreApplication.translate("update_available", u"Click OK to update to the latest version.", None))
    # retranslateUi

