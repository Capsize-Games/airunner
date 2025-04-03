# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'airunner_settings.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QHeaderView, QScrollArea,
    QSizePolicy, QTreeView, QWidget)

class Ui_airunner_settings(object):
    def setupUi(self, airunner_settings):
        if not airunner_settings.objectName():
            airunner_settings.setObjectName(u"airunner_settings")
        airunner_settings.resize(1014, 726)
        self.gridLayout = QGridLayout(airunner_settings)
        self.gridLayout.setObjectName(u"gridLayout")
        self.directory = QTreeView(airunner_settings)
        self.directory.setObjectName(u"directory")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.directory.sizePolicy().hasHeightForWidth())
        self.directory.setSizePolicy(sizePolicy)
        self.directory.setMinimumSize(QSize(300, 0))

        self.gridLayout.addWidget(self.directory, 0, 0, 1, 1)

        self.preferences = QScrollArea(airunner_settings)
        self.preferences.setObjectName(u"preferences")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.preferences.sizePolicy().hasHeightForWidth())
        self.preferences.setSizePolicy(sizePolicy1)
        self.preferences.setMinimumSize(QSize(350, 0))
        self.preferences.setWidgetResizable(True)
        self.voice_settings = QWidget()
        self.voice_settings.setObjectName(u"voice_settings")
        self.preferences.setWidget(self.voice_settings)

        self.gridLayout.addWidget(self.preferences, 0, 1, 1, 1)


        self.retranslateUi(airunner_settings)

        QMetaObject.connectSlotsByName(airunner_settings)
    # setupUi

    def retranslateUi(self, airunner_settings):
        airunner_settings.setWindowTitle(QCoreApplication.translate("airunner_settings", u"AI Runner Settings", None))
    # retranslateUi

