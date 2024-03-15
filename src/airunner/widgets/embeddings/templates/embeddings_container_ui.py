# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'embeddings_container.ui'
##
## Created by: Qt User Interface Compiler version 6.6.2
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QGridLayout,
    QHBoxLayout, QLineEdit, QPushButton, QScrollArea,
    QSizePolicy, QWidget)

class Ui_embeddings_container(object):
    def setupUi(self, embeddings_container):
        if not embeddings_container.objectName():
            embeddings_container.setObjectName(u"embeddings_container")
        embeddings_container.resize(479, 257)
        self.gridLayout = QGridLayout(embeddings_container)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.lineEdit = QLineEdit(embeddings_container)
        self.lineEdit.setObjectName(u"lineEdit")

        self.horizontalLayout.addWidget(self.lineEdit)

        self.checkBox = QCheckBox(embeddings_container)
        self.checkBox.setObjectName(u"checkBox")
        font = QFont()
        font.setPointSize(9)
        self.checkBox.setFont(font)

        self.horizontalLayout.addWidget(self.checkBox)


        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)

        self.embeddings = QScrollArea(embeddings_container)
        self.embeddings.setObjectName(u"embeddings")
        self.embeddings.setFont(font)
        self.embeddings.setFrameShape(QFrame.NoFrame)
        self.embeddings.setFrameShadow(QFrame.Plain)
        self.embeddings.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 461, 175))
        self.gridLayout_2 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.embeddings.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout.addWidget(self.embeddings, 1, 0, 1, 1)

        self.pushButton = QPushButton(embeddings_container)
        self.pushButton.setObjectName(u"pushButton")

        self.gridLayout.addWidget(self.pushButton, 2, 0, 1, 1)


        self.retranslateUi(embeddings_container)
        self.pushButton.clicked.connect(embeddings_container.action_clicked_button_scan_for_embeddings)
        self.lineEdit.textChanged.connect(embeddings_container.search_text_changed)
        self.checkBox.toggled.connect(embeddings_container.toggle_all_toggled)

        QMetaObject.connectSlotsByName(embeddings_container)
    # setupUi

    def retranslateUi(self, embeddings_container):
        embeddings_container.setWindowTitle(QCoreApplication.translate("embeddings_container", u"Form", None))
        self.lineEdit.setPlaceholderText(QCoreApplication.translate("embeddings_container", u"Search", None))
        self.checkBox.setText(QCoreApplication.translate("embeddings_container", u"Toggle all", None))
        self.pushButton.setText(QCoreApplication.translate("embeddings_container", u"Scan for embeddings", None))
    # retranslateUi

