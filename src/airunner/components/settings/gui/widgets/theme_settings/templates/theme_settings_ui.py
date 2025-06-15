# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'theme_settings.ui'
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
    QSizePolicy, QSpacerItem, QWidget)

class Ui_theme_settings(object):
    def setupUi(self, theme_settings):
        if not theme_settings.objectName():
            theme_settings.setObjectName(u"theme_settings")
        theme_settings.resize(400, 300)
        self.gridLayout_2 = QGridLayout(theme_settings)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.groupBox = QGroupBox(theme_settings)
        self.groupBox.setObjectName(u"groupBox")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox.sizePolicy().hasHeightForWidth())
        self.groupBox.setSizePolicy(sizePolicy)
        self.gridLayout = QGridLayout(self.groupBox)
        self.gridLayout.setObjectName(u"gridLayout")
        self.theme_combobox = QComboBox(self.groupBox)
        self.theme_combobox.setObjectName(u"theme_combobox")

        self.gridLayout.addWidget(self.theme_combobox, 0, 0, 1, 1)


        self.gridLayout_2.addWidget(self.groupBox, 0, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer, 1, 0, 1, 1)


        self.retranslateUi(theme_settings)

        QMetaObject.connectSlotsByName(theme_settings)
    # setupUi

    def retranslateUi(self, theme_settings):
        theme_settings.setWindowTitle(QCoreApplication.translate("theme_settings", u"Form", None))
        self.groupBox.setTitle(QCoreApplication.translate("theme_settings", u"Theme", None))
    # retranslateUi

