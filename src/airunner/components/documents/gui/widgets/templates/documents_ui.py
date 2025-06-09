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
from PySide6.QtWidgets import (QApplication, QGridLayout, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QSizePolicy, QWidget)

class Ui_documents(object):
    def setupUi(self, documents):
        if not documents.objectName():
            documents.setObjectName(u"documents")
        documents.resize(467, 524)
        self.gridLayout = QGridLayout(documents)
        self.gridLayout.setObjectName(u"gridLayout")
        self.document_list = QListWidget(documents)
        self.document_list.setObjectName(u"document_list")

        self.gridLayout.addWidget(self.document_list, 1, 0, 1, 2)

        self.browse_button = QPushButton(documents)
        self.browse_button.setObjectName(u"browse_button")

        self.gridLayout.addWidget(self.browse_button, 0, 1, 1, 1)

        self.path = QLineEdit(documents)
        self.path.setObjectName(u"path")

        self.gridLayout.addWidget(self.path, 0, 0, 1, 1)


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

