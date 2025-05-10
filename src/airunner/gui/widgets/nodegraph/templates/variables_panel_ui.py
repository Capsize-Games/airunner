# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'variables_panel.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QListWidget, QListWidgetItem,
    QPushButton, QSizePolicy, QWidget)

class Ui_variables_panel(object):
    def setupUi(self, variables_panel):
        if not variables_panel.objectName():
            variables_panel.setObjectName(u"variables_panel")
        variables_panel.resize(400, 300)
        self.gridLayout = QGridLayout(variables_panel)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 10, 0)
        self.variables_list_widget = QListWidget(variables_panel)
        self.variables_list_widget.setObjectName(u"variables_list_widget")
        self.variables_list_widget.setDragEnabled(True)

        self.gridLayout.addWidget(self.variables_list_widget, 0, 0, 1, 1)

        self.add_variable_button = QPushButton(variables_panel)
        self.add_variable_button.setObjectName(u"add_variable_button")

        self.gridLayout.addWidget(self.add_variable_button, 1, 0, 1, 1)


        self.retranslateUi(variables_panel)
        self.add_variable_button.clicked.connect(variables_panel.on_add_variable_button_clicked)

        QMetaObject.connectSlotsByName(variables_panel)
    # setupUi

    def retranslateUi(self, variables_panel):
        variables_panel.setWindowTitle(QCoreApplication.translate("variables_panel", u"Form", None))
        self.add_variable_button.setText(QCoreApplication.translate("variables_panel", u"Add Variable", None))
    # retranslateUi

