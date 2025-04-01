# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'path_settings.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QSpacerItem, QWidget)

class Ui_PathSettings(object):
    def setupUi(self, PathSettings):
        if not PathSettings.objectName():
            PathSettings.setObjectName(u"PathSettings")
        PathSettings.resize(400, 275)
        self.gridLayout = QGridLayout(PathSettings)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_2 = QLabel(PathSettings)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)
        self.label_2.setWordWrap(True)

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 139, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 4, 0, 1, 1)

        self.label = QLabel(PathSettings)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.base_path = QLineEdit(PathSettings)
        self.base_path.setObjectName(u"base_path")

        self.gridLayout.addWidget(self.base_path, 2, 0, 1, 1)

        self.pushButton = QPushButton(PathSettings)
        self.pushButton.setObjectName(u"pushButton")

        self.gridLayout.addWidget(self.pushButton, 3, 0, 1, 1)


        self.retranslateUi(PathSettings)
        self.pushButton.clicked.connect(PathSettings.browse_files)
        self.base_path.textChanged.connect(PathSettings.path_text_changed)

        QMetaObject.connectSlotsByName(PathSettings)
    # setupUi

    def retranslateUi(self, PathSettings):
        PathSettings.setWindowTitle(QCoreApplication.translate("PathSettings", u"Form", None))
        self.label_2.setText(QCoreApplication.translate("PathSettings", u"Let's begin by setting up the path to your AI Runner directory. This directory will contain subdirectories which will contain your models, generated images and more.", None))
        self.label.setText(QCoreApplication.translate("PathSettings", u"AI Runner path", None))
        self.base_path.setText(QCoreApplication.translate("PathSettings", u"~/.local/share/airunner", None))
        self.pushButton.setText(QCoreApplication.translate("PathSettings", u"Browse", None))
    # retranslateUi

