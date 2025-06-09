# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'home_stage.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QLabel, QSizePolicy,
    QSpacerItem, QWidget)

class Ui_home_stage_widget(object):
    def setupUi(self, home_stage_widget):
        if not home_stage_widget.objectName():
            home_stage_widget.setObjectName(u"home_stage_widget")
        home_stage_widget.resize(690, 623)
        self.gridLayout = QGridLayout(home_stage_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_2 = QLabel(home_stage_widget)
        self.label_2.setObjectName(u"label_2")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 2)

        self.label = QLabel(home_stage_widget)
        self.label.setObjectName(u"label")
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        font = QFont()
        font.setFamilies([u"Ubuntu Sans"])
        font.setPointSize(24)
        font.setBold(False)
        self.label.setFont(font)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 2)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 2, 0, 1, 1)


        self.retranslateUi(home_stage_widget)

        QMetaObject.connectSlotsByName(home_stage_widget)
    # setupUi

    def retranslateUi(self, home_stage_widget):
        home_stage_widget.setWindowTitle(QCoreApplication.translate("home_stage_widget", u"Form", None))
        self.label_2.setText(QCoreApplication.translate("home_stage_widget", u"Offline inference engine", None))
        self.label.setText(QCoreApplication.translate("home_stage_widget", u"AI Runner", None))
    # retranslateUi

