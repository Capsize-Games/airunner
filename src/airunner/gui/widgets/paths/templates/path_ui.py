# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'path.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QWidget)

class Ui_path_widget(object):
    def setupUi(self, path_widget):
        if not path_widget.objectName():
            path_widget.setObjectName(u"path_widget")
        path_widget.resize(452, 94)
        self.gridLayout = QGridLayout(path_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontal_line = QFrame(path_widget)
        self.horizontal_line.setObjectName(u"horizontal_line")
        self.horizontal_line.setFrameShape(QFrame.Shape.HLine)
        self.horizontal_line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.horizontal_line, 4, 0, 1, 1)

        self.title_label = QLabel(path_widget)
        self.title_label.setObjectName(u"title_label")
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self.title_label.setFont(font)

        self.gridLayout.addWidget(self.title_label, 1, 0, 1, 1)

        self.description_label = QLabel(path_widget)
        self.description_label.setObjectName(u"description_label")
        font1 = QFont()
        font1.setPointSize(10)
        self.description_label.setFont(font1)

        self.gridLayout.addWidget(self.description_label, 2, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.path = QLineEdit(path_widget)
        self.path.setObjectName(u"path")
        self.path.setFont(font1)

        self.horizontalLayout.addWidget(self.path)

        self.browse_button = QPushButton(path_widget)
        self.browse_button.setObjectName(u"browse_button")
        self.browse_button.setFont(font1)

        self.horizontalLayout.addWidget(self.browse_button)


        self.gridLayout.addLayout(self.horizontalLayout, 3, 0, 1, 1)


        self.retranslateUi(path_widget)
        self.path.textChanged.connect(path_widget.action_path_changed)
        self.browse_button.clicked.connect(path_widget.action_button_clicked)

        QMetaObject.connectSlotsByName(path_widget)
    # setupUi

    def retranslateUi(self, path_widget):
        path_widget.setWindowTitle(QCoreApplication.translate("path_widget", u"Form", None))
        self.title_label.setText(QCoreApplication.translate("path_widget", u"Title", None))
        self.description_label.setText(QCoreApplication.translate("path_widget", u"Description", None))
        self.browse_button.setText(QCoreApplication.translate("path_widget", u"Browse", None))
    # retranslateUi

