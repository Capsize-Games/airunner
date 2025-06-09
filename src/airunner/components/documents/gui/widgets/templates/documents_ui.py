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
from PySide6.QtWidgets import (QApplication, QGridLayout, QHBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QSizePolicy,
    QWidget)

class Ui_documents(object):
    def setupUi(self, documents):
        if not documents.objectName():
            documents.setObjectName(u"documents")
        documents.resize(467, 524)
        self.gridLayout = QGridLayout(documents)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.documents_header = QWidget(documents)
        self.documents_header.setObjectName(u"documents_header")
        self.horizontalLayout = QHBoxLayout(self.documents_header)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.documents_header_container = QWidget(self.documents_header)
        self.documents_header_container.setObjectName(u"documents_header_container")
        self.horizontalLayout_2 = QHBoxLayout(self.documents_header_container)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(10, 10, 10, 10)
        self.path = QLineEdit(self.documents_header_container)
        self.path.setObjectName(u"path")

        self.horizontalLayout_2.addWidget(self.path)

        self.browse_button = QPushButton(self.documents_header_container)
        self.browse_button.setObjectName(u"browse_button")

        self.horizontalLayout_2.addWidget(self.browse_button)


        self.horizontalLayout.addWidget(self.documents_header_container)


        self.gridLayout.addWidget(self.documents_header, 0, 0, 1, 1)

        self.document_list = QListWidget(documents)
        self.document_list.setObjectName(u"document_list")

        self.gridLayout.addWidget(self.document_list, 1, 0, 1, 1)


        self.retranslateUi(documents)

        QMetaObject.connectSlotsByName(documents)
    # setupUi

    def retranslateUi(self, documents):
        documents.setWindowTitle(QCoreApplication.translate("documents", u"Form", None))
#if QT_CONFIG(tooltip)
        self.browse_button.setToolTip(QCoreApplication.translate("documents", u"Browse", None))
#endif // QT_CONFIG(tooltip)
        self.browse_button.setText(QCoreApplication.translate("documents", u"Browse", None))
    # retranslateUi

