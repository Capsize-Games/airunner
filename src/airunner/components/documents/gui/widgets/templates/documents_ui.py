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
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QProgressBar, QPushButton,
    QSizePolicy, QSplitter, QTabWidget, QTreeView,
    QVBoxLayout, QWidget)

class Ui_documents(object):
    def setupUi(self, documents):
        if not documents.objectName():
            documents.setObjectName(u"documents")
        documents.resize(467, 524)
        self.gridLayout = QGridLayout(documents)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(0)
        self.gridLayout.setVerticalSpacing(10)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.progressBar = QProgressBar(documents)
        self.progressBar.setObjectName(u"progressBar")
        self.progressBar.setValue(0)

        self.gridLayout.addWidget(self.progressBar, 5, 0, 1, 1)

        self.tabWidget = QTabWidget(documents)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabDocuments = QWidget()
        self.tabDocuments.setObjectName(u"tabDocuments")
        self.verticalLayoutDocuments = QVBoxLayout(self.tabDocuments)
        self.verticalLayoutDocuments.setSpacing(10)
        self.verticalLayoutDocuments.setObjectName(u"verticalLayoutDocuments")
        self.verticalLayoutDocuments.setContentsMargins(10, 10, 10, 10)
        self.documentsTreeView = QTreeView(self.tabDocuments)
        self.documentsTreeView.setObjectName(u"documentsTreeView")

        self.verticalLayoutDocuments.addWidget(self.documentsTreeView)

        self.tabWidget.addTab(self.tabDocuments, "")
        self.tabZim = QWidget()
        self.tabZim.setObjectName(u"tabZim")
        self.verticalLayoutZim = QVBoxLayout(self.tabZim)
        self.verticalLayoutZim.setObjectName(u"verticalLayoutZim")
        self.splitter = QSplitter(self.tabZim)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Vertical)
        self.localZimWidget = QWidget(self.splitter)
        self.localZimWidget.setObjectName(u"localZimWidget")
        self.verticalLayoutLocal = QVBoxLayout(self.localZimWidget)
        self.verticalLayoutLocal.setObjectName(u"verticalLayoutLocal")
        self.verticalLayoutLocal.setContentsMargins(0, 0, 0, 0)
        self.labelLocal = QLabel(self.localZimWidget)
        self.labelLocal.setObjectName(u"labelLocal")
        self.labelLocal.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)

        self.verticalLayoutLocal.addWidget(self.labelLocal)

        self.listLocalZims = QListWidget(self.localZimWidget)
        self.listLocalZims.setObjectName(u"listLocalZims")

        self.verticalLayoutLocal.addWidget(self.listLocalZims)

        self.splitter.addWidget(self.localZimWidget)
        self.remoteZimWidget = QWidget(self.splitter)
        self.remoteZimWidget.setObjectName(u"remoteZimWidget")
        self.verticalLayoutRemote = QVBoxLayout(self.remoteZimWidget)
        self.verticalLayoutRemote.setObjectName(u"verticalLayoutRemote")
        self.verticalLayoutRemote.setContentsMargins(0, 10, 0, 0)
        self.labelRemote = QLabel(self.remoteZimWidget)
        self.labelRemote.setObjectName(u"labelRemote")
        self.labelRemote.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)

        self.verticalLayoutRemote.addWidget(self.labelRemote)

        self.kiwixSearchLayout = QHBoxLayout()
        self.kiwixSearchLayout.setObjectName(u"kiwixSearchLayout")
        self.kiwixSearchBar = QLineEdit(self.remoteZimWidget)
        self.kiwixSearchBar.setObjectName(u"kiwixSearchBar")

        self.kiwixSearchLayout.addWidget(self.kiwixSearchBar)

        self.kiwixLangLabel = QLabel(self.remoteZimWidget)
        self.kiwixLangLabel.setObjectName(u"kiwixLangLabel")

        self.kiwixSearchLayout.addWidget(self.kiwixLangLabel)

        self.kiwixLangCombo = QComboBox(self.remoteZimWidget)
        self.kiwixLangCombo.addItem("")
        self.kiwixLangCombo.addItem("")
        self.kiwixLangCombo.setObjectName(u"kiwixLangCombo")

        self.kiwixSearchLayout.addWidget(self.kiwixLangCombo)

        self.kiwixSearchButton = QPushButton(self.remoteZimWidget)
        self.kiwixSearchButton.setObjectName(u"kiwixSearchButton")

        self.kiwixSearchLayout.addWidget(self.kiwixSearchButton)


        self.verticalLayoutRemote.addLayout(self.kiwixSearchLayout)

        self.listRemoteZims = QListWidget(self.remoteZimWidget)
        self.listRemoteZims.setObjectName(u"listRemoteZims")

        self.verticalLayoutRemote.addWidget(self.listRemoteZims)

        self.splitter.addWidget(self.remoteZimWidget)

        self.verticalLayoutZim.addWidget(self.splitter)

        self.tabWidget.addTab(self.tabZim, "")

        self.gridLayout.addWidget(self.tabWidget, 4, 0, 1, 1)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setSpacing(10)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(10, 15, 10, 10)
        self.label = QLabel(documents)
        self.label.setObjectName(u"label")

        self.verticalLayout.addWidget(self.label)


        self.gridLayout.addLayout(self.verticalLayout, 2, 0, 1, 1)

        self.line = QFrame(documents)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 3, 0, 1, 1)


        self.retranslateUi(documents)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(documents)
    # setupUi

    def retranslateUi(self, documents):
        documents.setWindowTitle(QCoreApplication.translate("documents", u"Documents", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabDocuments), QCoreApplication.translate("documents", u"Documents", None))
        self.labelLocal.setText(QCoreApplication.translate("documents", u"Local ZIM Files", None))
        self.labelRemote.setText(QCoreApplication.translate("documents", u"Kiwix Library Search Results", None))
        self.kiwixSearchBar.setPlaceholderText(QCoreApplication.translate("documents", u"Search Kiwix Library (title, keyword, language code)...", None))
        self.kiwixLangLabel.setText(QCoreApplication.translate("documents", u"Lang:", None))
        self.kiwixLangCombo.setItemText(0, QCoreApplication.translate("documents", u"eng", None))
        self.kiwixLangCombo.setItemText(1, QCoreApplication.translate("documents", u"all", None))

        self.kiwixSearchButton.setText(QCoreApplication.translate("documents", u"Search", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabZim), QCoreApplication.translate("documents", u"Kiwix ZIM", None))
        self.label.setText(QCoreApplication.translate("documents", u"LLM knowledge base", None))
    # retranslateUi

