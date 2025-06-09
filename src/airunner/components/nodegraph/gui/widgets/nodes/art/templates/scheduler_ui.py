# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'scheduler.ui'
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

class Ui_scheduler_node(object):
    def setupUi(self, scheduler_node):
        if not scheduler_node.objectName():
            scheduler_node.setObjectName(u"scheduler_node")
        scheduler_node.resize(400, 300)
        self.gridLayout = QGridLayout(scheduler_node)
        self.gridLayout.setObjectName(u"gridLayout")
        self.groupBox = QGroupBox(scheduler_node)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout_2 = QGridLayout(self.groupBox)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.scheduler_combobox = QComboBox(self.groupBox)
        self.scheduler_combobox.setObjectName(u"scheduler_combobox")

        self.gridLayout_2.addWidget(self.scheduler_combobox, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 1, 0, 1, 1)


        self.retranslateUi(scheduler_node)

        QMetaObject.connectSlotsByName(scheduler_node)
    # setupUi

    def retranslateUi(self, scheduler_node):
        scheduler_node.setWindowTitle(QCoreApplication.translate("scheduler_node", u"Form", None))
        self.groupBox.setTitle(QCoreApplication.translate("scheduler_node", u"Scheduler", None))
    # retranslateUi

