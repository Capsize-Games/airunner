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
    QScrollArea, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)

from airunner.gui.widgets.llm.loading_widget import LoadingWidget

class Ui_embeddings_container(object):
    def setupUi(self, embeddings_container):
        if not embeddings_container.objectName():
            embeddings_container.setObjectName(u"embeddings_container")
        embeddings_container.resize(479, 582)
        self.gridLayout = QGridLayout(embeddings_container)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(0)
        self.gridLayout.setVerticalSpacing(10)
        self.gridLayout.setContentsMargins(10, 10, 10, 10)
        self.embeddings_scroll_area = QScrollArea(embeddings_container)
        self.embeddings_scroll_area.setObjectName(u"embeddings_scroll_area")
        font = QFont()
        font.setPointSize(9)
        self.embeddings_scroll_area.setFont(font)
        self.embeddings_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.embeddings_scroll_area.setFrameShadow(QFrame.Shadow.Plain)
        self.embeddings_scroll_area.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 459, 413))
        self.gridLayout_2 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setHorizontalSpacing(0)
        self.gridLayout_2.setVerticalSpacing(10)
        self.gridLayout_2.setContentsMargins(0, 0, 10, 0)
        self.embeddings_scroll_area.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout.addWidget(self.embeddings_scroll_area, 4, 0, 1, 1)

        self.pushButton = QPushButton(embeddings_container)
        self.pushButton.setObjectName(u"pushButton")

        self.gridLayout.addWidget(self.pushButton, 5, 0, 1, 1)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setSpacing(10)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(-1, -1, 10, 10)
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label = QLabel(embeddings_container)
        self.label.setObjectName(u"label")

        self.horizontalLayout_2.addWidget(self.label)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)

        self.loading_icon = LoadingWidget(embeddings_container)
        self.loading_icon.setObjectName(u"loading_icon")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.loading_icon.sizePolicy().hasHeightForWidth())
        self.loading_icon.setSizePolicy(sizePolicy)
        self.loading_icon.setMinimumSize(QSize(0, 0))

        self.horizontalLayout_2.addWidget(self.loading_icon)

        self.apply_embeddings_button = QPushButton(embeddings_container)
        self.apply_embeddings_button.setObjectName(u"apply_embeddings_button")

        self.horizontalLayout_2.addWidget(self.apply_embeddings_button)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.line = QFrame(embeddings_container)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout.addWidget(self.line)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(10)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(-1, -1, 10, -1)
        self.lineEdit = QLineEdit(embeddings_container)
        self.lineEdit.setObjectName(u"lineEdit")

        self.horizontalLayout.addWidget(self.lineEdit)

        self.toggle_all_embeddings = QCheckBox(embeddings_container)
        self.toggle_all_embeddings.setObjectName(u"toggle_all_embeddings")
        self.toggle_all_embeddings.setFont(font)

        self.horizontalLayout.addWidget(self.toggle_all_embeddings)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.line_2 = QFrame(embeddings_container)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout.addWidget(self.line_2)


        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)


        self.retranslateUi(embeddings_container)
        self.pushButton.clicked.connect(embeddings_container.action_clicked_button_scan_for_embeddings)
        self.lineEdit.textChanged.connect(embeddings_container.search_text_changed)
        self.toggle_all_embeddings.toggled.connect(embeddings_container.toggle_all_toggled)
        self.apply_embeddings_button.clicked.connect(embeddings_container.apply_embeddings)

        QMetaObject.connectSlotsByName(embeddings_container)
    # setupUi

    def retranslateUi(self, embeddings_container):
        embeddings_container.setWindowTitle(QCoreApplication.translate("embeddings_container", u"Form", None))
        self.pushButton.setText(QCoreApplication.translate("embeddings_container", u"Scan for embeddings", None))
        self.label.setText(QCoreApplication.translate("embeddings_container", u"Embeddings", None))
        self.apply_embeddings_button.setText(QCoreApplication.translate("embeddings_container", u"Apply Changes", None))
        self.lineEdit.setPlaceholderText(QCoreApplication.translate("embeddings_container", u"Search", None))
        self.toggle_all_embeddings.setText(QCoreApplication.translate("embeddings_container", u"Toggle all", None))
    # retranslateUi

