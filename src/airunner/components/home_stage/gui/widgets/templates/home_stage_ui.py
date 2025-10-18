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
from PySide6.QtWidgets import (QApplication, QGridLayout, QSizePolicy, QWidget)

class Ui_home_stage_widget(object):
    def setupUi(self, home_stage_widget):
        if not home_stage_widget.objectName():
            home_stage_widget.setObjectName(u"home_stage_widget")
        home_stage_widget.resize(800, 600)
        self.gridLayout = QGridLayout(home_stage_widget)
        self.gridLayout.setSpacing(10)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(10, 10, 10, 10)
        self.knowledge_base_panel = QWidget(home_stage_widget)
        self.knowledge_base_panel.setObjectName(u"knowledge_base_panel")
        self.knowledge_base_panel.setMinimumSize(QSize(200, 200))

        self.gridLayout.addWidget(self.knowledge_base_panel, 0, 0, 2, 1)

        self.system_resources_panel = QWidget(home_stage_widget)
        self.system_resources_panel.setObjectName(u"system_resources_panel")
        self.system_resources_panel.setMinimumSize(QSize(200, 200))

        self.gridLayout.addWidget(self.system_resources_panel, 0, 1, 2, 1)


        self.retranslateUi(home_stage_widget)

        QMetaObject.connectSlotsByName(home_stage_widget)
    # setupUi

    def retranslateUi(self, home_stage_widget):
        home_stage_widget.setWindowTitle(QCoreApplication.translate("home_stage_widget", u"Form", None))
    # retranslateUi

