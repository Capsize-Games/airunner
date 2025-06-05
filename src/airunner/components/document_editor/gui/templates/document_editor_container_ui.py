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
from PySide6.QtWidgets import (QApplication, QGridLayout, QSizePolicy, QSplitter,
    QTabWidget, QWidget)

from airunner.components.document_editor.gui.widgets.file_explorer_widget import FileExplorerWidget

class Ui_document_editor_container(object):
    def setupUi(self, document_editor_container):
        if not document_editor_container.objectName():
            document_editor_container.setObjectName(u"document_editor_container")
        document_editor_container.resize(400, 300)
        self.gridLayout_2 = QGridLayout(document_editor_container)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.splitter = QSplitter(document_editor_container)
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

        self.gridLayout_2.addWidget(self.splitter, 0, 0, 1, 1)


        self.retranslateUi(document_editor_container)

        self.documents.setCurrentIndex(-1)


        QMetaObject.connectSlotsByName(document_editor_container)
    # setupUi

    def retranslateUi(self, document_editor_container):
        document_editor_container.setWindowTitle(QCoreApplication.translate("document_editor_container", u"Form", None))
    # retranslateUi

