# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'documents.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QSizePolicy, QWidget)

class Ui_documents(object):
    def setupUi(self, documents):
        if not documents.objectName():
            documents.setObjectName(u"documents")
        documents.resize(467, 524)
        self.gridLayout = QGridLayout(documents)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(0)
        self.gridLayout.setVerticalSpacing(10)
        self.gridLayout.setContentsMargins(10, 10, 10, 10)
        self.add_files = QPushButton(documents)
        self.add_files.setObjectName(u"add_files")
        self.add_files.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.gridLayout.addWidget(self.add_files, 2, 0, 1, 2)

        self.document_list = QListWidget(documents)
        self.document_list.setObjectName(u"document_list")

        self.gridLayout.addWidget(self.document_list, 1, 0, 1, 2)

        self.label = QLabel(documents)
        self.label.setObjectName(u"label")

        self.gridLayout.addWidget(self.label, 0, 0, 1, 2)


        self.retranslateUi(documents)

        QMetaObject.connectSlotsByName(documents)
    # setupUi

    def retranslateUi(self, documents):
        documents.setWindowTitle(QCoreApplication.translate("documents", u"Form", None))
#if QT_CONFIG(tooltip)
        self.add_files.setToolTip(QCoreApplication.translate("documents", u"Add files to knowledgebase", None))
#endif // QT_CONFIG(tooltip)
        self.add_files.setText(QCoreApplication.translate("documents", u"Add Files", None))
        self.label.setText(QCoreApplication.translate("documents", u"Documents in knowledge base", None))
    # retranslateUi

