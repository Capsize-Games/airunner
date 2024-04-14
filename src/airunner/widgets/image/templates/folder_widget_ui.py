# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'folder_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QLabel, QPushButton,
    QSizePolicy, QSpacerItem, QWidget)

class Ui_folder_widget(object):
    def setupUi(self, folder_widget):
        if not folder_widget.objectName():
            folder_widget.setObjectName(u"folder_widget")
        folder_widget.resize(94, 93)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(folder_widget.sizePolicy().hasHeightForWidth())
        folder_widget.setSizePolicy(sizePolicy)
        folder_widget.setMaximumSize(QSize(94, 93))
        self.gridLayout = QGridLayout(folder_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 2, 0, 1, 1)

        self.pushButton = QPushButton(folder_widget)
        self.pushButton.setObjectName(u"pushButton")
        self.pushButton.setMinimumSize(QSize(64, 64))
        self.pushButton.setMaximumSize(QSize(64, 64))
        self.pushButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.pushButton.setLayoutDirection(Qt.LeftToRight)
        icon = QIcon()
        iconThemeName = u"folder"
        if QIcon.hasThemeIcon(iconThemeName):
            icon = QIcon.fromTheme(iconThemeName)
        else:
            icon.addFile(u".", QSize(), QIcon.Normal, QIcon.Off)

        self.pushButton.setIcon(icon)
        self.pushButton.setIconSize(QSize(64, 64))
        self.pushButton.setFlat(True)

        self.gridLayout.addWidget(self.pushButton, 0, 0, 1, 1)

        self.label = QLabel(folder_widget)
        self.label.setObjectName(u"label")
        self.label.setLayoutDirection(Qt.LeftToRight)
        self.label.setAlignment(Qt.AlignCenter)

        self.gridLayout.addWidget(self.label, 1, 0, 1, 1)


        self.retranslateUi(folder_widget)
        self.pushButton.clicked.connect(folder_widget.folder_clicked)

        QMetaObject.connectSlotsByName(folder_widget)
    # setupUi

    def retranslateUi(self, folder_widget):
        folder_widget.setWindowTitle(QCoreApplication.translate("folder_widget", u"Form", None))
        self.pushButton.setText("")
        self.label.setText(QCoreApplication.translate("folder_widget", u"TextLabel", None))
    # retranslateUi

