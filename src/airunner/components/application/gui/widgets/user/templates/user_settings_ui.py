# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'user_settings.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QGroupBox,
    QLineEdit, QSizePolicy, QSpacerItem, QWidget)

class Ui_user_settings_widget(object):
    def setupUi(self, user_settings_widget):
        if not user_settings_widget.objectName():
            user_settings_widget.setObjectName(u"user_settings_widget")
        user_settings_widget.resize(500, 346)
        self.gridLayout = QGridLayout(user_settings_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.groupBox_3 = QGroupBox(user_settings_widget)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.gridLayout_2 = QGridLayout(self.groupBox_3)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.unit_system = QComboBox(self.groupBox_3)
        self.unit_system.addItem("")
        self.unit_system.addItem("")
        self.unit_system.setObjectName(u"unit_system")

        self.gridLayout_2.addWidget(self.unit_system, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_3, 2, 0, 1, 1)

        self.groupBox_2 = QGroupBox(user_settings_widget)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.gridLayout_4 = QGridLayout(self.groupBox_2)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.zipcode = QLineEdit(self.groupBox_2)
        self.zipcode.setObjectName(u"zipcode")

        self.gridLayout_4.addWidget(self.zipcode, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_2, 1, 0, 1, 1)

        self.groupBox = QGroupBox(user_settings_widget)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout_3 = QGridLayout(self.groupBox)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.username = QLineEdit(self.groupBox)
        self.username.setObjectName(u"username")

        self.gridLayout_3.addWidget(self.username, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 3, 0, 1, 1)


        self.retranslateUi(user_settings_widget)
        self.username.textChanged.connect(user_settings_widget.username_changed)
        self.zipcode.textChanged.connect(user_settings_widget.zipcode_changed)
        self.unit_system.currentTextChanged.connect(user_settings_widget.unit_system_changed)

        QMetaObject.connectSlotsByName(user_settings_widget)
    # setupUi

    def retranslateUi(self, user_settings_widget):
        user_settings_widget.setWindowTitle(QCoreApplication.translate("user_settings_widget", u"Form", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("user_settings_widget", u"Unit System", None))
        self.unit_system.setItemText(0, QCoreApplication.translate("user_settings_widget", u"Imperial", None))
        self.unit_system.setItemText(1, QCoreApplication.translate("user_settings_widget", u"Metric", None))

        self.groupBox_2.setTitle(QCoreApplication.translate("user_settings_widget", u"Zipcode", None))
        self.groupBox.setTitle(QCoreApplication.translate("user_settings_widget", u"Username", None))
    # retranslateUi

