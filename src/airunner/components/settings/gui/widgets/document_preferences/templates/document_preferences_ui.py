# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'document_preferences.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QGridLayout, QSizePolicy,
    QSpacerItem, QWidget)

class Ui_document_preferences(object):
    def setupUi(self, document_preferences):
        if not document_preferences.objectName():
            document_preferences.setObjectName(u"document_preferences")
        document_preferences.resize(400, 300)
        self.gridLayout = QGridLayout(document_preferences)
        self.gridLayout.setObjectName(u"gridLayout")
        self.autosave_checkbox = QCheckBox(document_preferences)
        self.autosave_checkbox.setObjectName(u"autosave_checkbox")

        self.gridLayout.addWidget(self.autosave_checkbox, 0, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 1, 0, 1, 1)


        self.retranslateUi(document_preferences)

        QMetaObject.connectSlotsByName(document_preferences)
    # setupUi

    def retranslateUi(self, document_preferences):
        document_preferences.setWindowTitle(QCoreApplication.translate("document_preferences", u"Form", None))
        self.autosave_checkbox.setText(QCoreApplication.translate("document_preferences", u"Auto save documents", None))
    # retranslateUi

