# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'document_editor_container.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QPlainTextEdit, QSizePolicy,
    QSplitter, QTabWidget, QWidget)

from airunner.components.file_explorer.gui.widgets.file_explorer_widget import FileExplorerWidget
import airunner.feather_rc

class Ui_document_editor_container(object):
    def setupUi(self, document_editor_container):
        if not document_editor_container.objectName():
            document_editor_container.setObjectName(u"document_editor_container")
        document_editor_container.resize(492, 300)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(document_editor_container.sizePolicy().hasHeightForWidth())
        document_editor_container.setSizePolicy(sizePolicy)
        self.gridLayout = QGridLayout(document_editor_container)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.vertical_splitter = QSplitter(document_editor_container)
        self.vertical_splitter.setObjectName(u"vertical_splitter")
        self.vertical_splitter.setOrientation(Qt.Orientation.Vertical)
        self.splitter = QSplitter(self.vertical_splitter)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.documents = QTabWidget(self.splitter)
        self.documents.setObjectName(u"documents")
        self.documents.setTabsClosable(True)
        self.documents.setMovable(True)
        self.splitter.addWidget(self.documents)
        self.file_explorer = FileExplorerWidget(self.splitter)
        self.file_explorer.setObjectName(u"file_explorer")
        self.splitter.addWidget(self.file_explorer)
        self.vertical_splitter.addWidget(self.splitter)
        self.terminal = QPlainTextEdit(self.vertical_splitter)
        self.terminal.setObjectName(u"terminal")
        self.terminal.setReadOnly(True)
        self.vertical_splitter.addWidget(self.terminal)

        self.gridLayout.addWidget(self.vertical_splitter, 2, 0, 1, 2)


        self.retranslateUi(document_editor_container)

        self.documents.setCurrentIndex(-1)


        QMetaObject.connectSlotsByName(document_editor_container)
    # setupUi

    def retranslateUi(self, document_editor_container):
        document_editor_container.setWindowTitle(QCoreApplication.translate("document_editor_container", u"Form", None))
    # retranslateUi

