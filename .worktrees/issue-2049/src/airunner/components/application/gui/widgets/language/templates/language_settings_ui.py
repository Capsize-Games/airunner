# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'language_settings.ui'
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

class Ui_language_settings_widget(object):
    def setupUi(self, language_settings_widget):
        if not language_settings_widget.objectName():
            language_settings_widget.setObjectName(u"language_settings_widget")
        language_settings_widget.resize(507, 398)
        self.gridLayout = QGridLayout(language_settings_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 3, 0, 1, 1)

        self.groupBox = QGroupBox(language_settings_widget)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout_2 = QGridLayout(self.groupBox)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gui_language = QComboBox(self.groupBox)
        self.gui_language.setObjectName(u"gui_language")

        self.gridLayout_2.addWidget(self.gui_language, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)

        self.groupBox_2 = QGroupBox(language_settings_widget)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.gridLayout_4 = QGridLayout(self.groupBox_2)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.user_language = QComboBox(self.groupBox_2)
        self.user_language.setObjectName(u"user_language")

        self.gridLayout_4.addWidget(self.user_language, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_2, 1, 0, 1, 1)

        self.groupBox_3 = QGroupBox(language_settings_widget)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.gridLayout_3 = QGridLayout(self.groupBox_3)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.bot_language = QComboBox(self.groupBox_3)
        self.bot_language.setObjectName(u"bot_language")

        self.gridLayout_3.addWidget(self.bot_language, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_3, 2, 0, 1, 1)


        self.retranslateUi(language_settings_widget)

        QMetaObject.connectSlotsByName(language_settings_widget)
    # setupUi

    def retranslateUi(self, language_settings_widget):
        language_settings_widget.setWindowTitle(QCoreApplication.translate("language_settings_widget", u"Form", None))
        self.groupBox.setTitle(QCoreApplication.translate("language_settings_widget", u"GUI Langauge", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("language_settings_widget", u"User Language", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("language_settings_widget", u"Bot Language", None))
    # retranslateUi

