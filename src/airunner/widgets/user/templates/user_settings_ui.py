# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'user_settings.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QGroupBox, QLineEdit,
    QSizePolicy, QSpacerItem, QWidget)

class Ui_user_settings_widget(object):
    def setupUi(self, user_settings_widget):
        if not user_settings_widget.objectName():
            user_settings_widget.setObjectName(u"user_settings_widget")
        user_settings_widget.resize(500, 346)
        self.gridLayout = QGridLayout(user_settings_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.groupBox = QGroupBox(user_settings_widget)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout_3 = QGridLayout(self.groupBox)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.username = QLineEdit(self.groupBox)
        self.username.setObjectName(u"username")

        self.gridLayout_3.addWidget(self.username, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 1, 0, 1, 1)


        self.retranslateUi(user_settings_widget)
        self.username.textChanged.connect(user_settings_widget.username_changed)

        QMetaObject.connectSlotsByName(user_settings_widget)
    # setupUi

    def retranslateUi(self, user_settings_widget):
        user_settings_widget.setWindowTitle(QCoreApplication.translate("user_settings_widget", u"Form", None))
        self.groupBox.setTitle(QCoreApplication.translate("user_settings_widget", u"Username", None))
    # retranslateUi

