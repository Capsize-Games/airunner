# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'installation_settings.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QSpacerItem,
    QWidget)

class Ui_PathSettings(object):
    def setupUi(self, PathSettings):
        if not PathSettings.objectName():
            PathSettings.setObjectName(u"PathSettings")
        PathSettings.resize(400, 275)
        self.gridLayout = QGridLayout(PathSettings)
        self.gridLayout.setObjectName(u"gridLayout")
        self.verticalSpacer = QSpacerItem(20, 139, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 3, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.installation_path = QLineEdit(PathSettings)
        self.installation_path.setObjectName(u"installation_path")

        self.horizontalLayout.addWidget(self.installation_path)

        self.pushButton = QPushButton(PathSettings)
        self.pushButton.setObjectName(u"pushButton")

        self.horizontalLayout.addWidget(self.pushButton)


        self.gridLayout.addLayout(self.horizontalLayout, 2, 0, 1, 1)

        self.label_2 = QLabel(PathSettings)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)
        self.label_2.setWordWrap(True)

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.label = QLabel(PathSettings)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)


        self.retranslateUi(PathSettings)
        self.pushButton.clicked.connect(PathSettings.browse)

        QMetaObject.connectSlotsByName(PathSettings)
    # setupUi

    def retranslateUi(self, PathSettings):
        PathSettings.setWindowTitle(QCoreApplication.translate("PathSettings", u"Form", None))
        self.pushButton.setText(QCoreApplication.translate("PathSettings", u"Browse", None))
        self.label_2.setText(QCoreApplication.translate("PathSettings", u"Choose a directory to install AI Runner to", None))
        self.label.setText(QCoreApplication.translate("PathSettings", u"Installation", None))
    # retranslateUi

