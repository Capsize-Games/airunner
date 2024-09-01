# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'embeddings_container.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QSizePolicy, QWidget)

class Ui_embeddings_container(object):
    def setupUi(self, embeddings_container):
        if not embeddings_container.objectName():
            embeddings_container.setObjectName(u"embeddings_container")
        embeddings_container.resize(479, 257)
        self.gridLayout = QGridLayout(embeddings_container)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(0)
        self.gridLayout.setVerticalSpacing(10)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(embeddings_container)
        self.label.setObjectName(u"label")

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.line = QFrame(embeddings_container)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 1, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(10)
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


        self.gridLayout.addLayout(self.horizontalLayout, 2, 0, 1, 1)

        self.embeddings = QScrollArea(embeddings_container)
        self.embeddings.setObjectName(u"embeddings")
        self.embeddings.setFont(font)
        self.embeddings.setFrameShape(QFrame.Shape.NoFrame)
        self.embeddings.setFrameShadow(QFrame.Shadow.Plain)
        self.embeddings.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 479, 145))
        self.gridLayout_2 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setHorizontalSpacing(0)
        self.gridLayout_2.setVerticalSpacing(10)
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.embeddings.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout.addWidget(self.embeddings, 3, 0, 1, 1)

        self.pushButton = QPushButton(embeddings_container)
        self.pushButton.setObjectName(u"pushButton")

        self.gridLayout.addWidget(self.pushButton, 4, 0, 1, 1)


        self.retranslateUi(embeddings_container)
        self.pushButton.clicked.connect(embeddings_container.action_clicked_button_scan_for_embeddings)
        self.lineEdit.textChanged.connect(embeddings_container.search_text_changed)
        self.checkBox.toggled.connect(embeddings_container.toggle_all_toggled)

        QMetaObject.connectSlotsByName(embeddings_container)
    # setupUi

    def retranslateUi(self, embeddings_container):
        embeddings_container.setWindowTitle(QCoreApplication.translate("embeddings_container", u"Form", None))
        self.label.setText(QCoreApplication.translate("embeddings_container", u"Embeddings", None))
        self.lineEdit.setPlaceholderText(QCoreApplication.translate("embeddings_container", u"Search", None))
        self.checkBox.setText(QCoreApplication.translate("embeddings_container", u"Toggle all", None))
        self.pushButton.setText(QCoreApplication.translate("embeddings_container", u"Scan for embeddings", None))
    # retranslateUi

