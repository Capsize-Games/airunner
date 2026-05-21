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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QFrame,
    QGridLayout, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QPushButton,
    QSizePolicy, QSplitter, QTabWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget)

from airunner.components.documents.gui.widgets.knowledge_base_panel_widget import KnowledgeBasePanelWidget

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
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setSpacing(10)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(10, 15, 10, 10)
        self.label = QLabel(documents)
        self.label.setObjectName(u"label")

        self.verticalLayout.addWidget(self.label)


        self.gridLayout.addLayout(self.verticalLayout, 2, 0, 1, 1)

        self.tabWidget = QTabWidget(documents)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabDocuments = QWidget()
        self.tabDocuments.setObjectName(u"tabDocuments")
        self.verticalLayoutDocuments = QVBoxLayout(self.tabDocuments)
        self.verticalLayoutDocuments.setSpacing(10)
        self.verticalLayoutDocuments.setObjectName(u"verticalLayoutDocuments")
        self.verticalLayoutDocuments.setContentsMargins(10, 10, 10, 10)
        self.documentsStatusWidget = QWidget(self.tabDocuments)
        self.documentsStatusWidget.setObjectName(u"documentsStatusWidget")
        self.verticalLayoutDocumentsStatus = QVBoxLayout(self.documentsStatusWidget)
        self.verticalLayoutDocumentsStatus.setSpacing(5)
        self.verticalLayoutDocumentsStatus.setObjectName(u"verticalLayoutDocumentsStatus")
        self.verticalLayoutDocumentsStatus.setContentsMargins(0, 0, 0, 0)
        self.labelDocuments = QLabel(self.documentsStatusWidget)
        self.labelDocuments.setObjectName(u"labelDocuments")

        self.verticalLayoutDocumentsStatus.addWidget(self.labelDocuments)

        self.documentsTableWidget = QTableWidget(self.documentsStatusWidget)
        if (self.documentsTableWidget.columnCount() < 4):
            self.documentsTableWidget.setColumnCount(4)
        __qtablewidgetitem = QTableWidgetItem()
        self.documentsTableWidget.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.documentsTableWidget.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.documentsTableWidget.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.documentsTableWidget.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        self.documentsTableWidget.setObjectName(u"documentsTableWidget")
        self.documentsTableWidget.setDragEnabled(True)
        self.documentsTableWidget.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.documentsTableWidget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.documentsTableWidget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.documentsTableWidget.setSortingEnabled(True)
        self.documentsTableWidget.setColumnCount(4)

        self.verticalLayoutDocumentsStatus.addWidget(self.documentsTableWidget)


        self.verticalLayoutDocuments.addWidget(self.documentsStatusWidget)

        self.tabWidget.addTab(self.tabDocuments, "")
        self.tabZim = QWidget()
        self.tabZim.setObjectName(u"tabZim")
        self.verticalLayoutZim = QVBoxLayout(self.tabZim)
        self.verticalLayoutZim.setObjectName(u"verticalLayoutZim")
        self.splitter = QSplitter(self.tabZim)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Vertical)
        self.remoteZimWidget = QWidget(self.splitter)
        self.remoteZimWidget.setObjectName(u"remoteZimWidget")
        self.verticalLayoutRemote = QVBoxLayout(self.remoteZimWidget)
        self.verticalLayoutRemote.setObjectName(u"verticalLayoutRemote")
        self.verticalLayoutRemote.setContentsMargins(0, 0, 0, 0)
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
        self.localZimWidget = QWidget(self.splitter)
        self.localZimWidget.setObjectName(u"localZimWidget")
        self.verticalLayoutLocal = QVBoxLayout(self.localZimWidget)
        self.verticalLayoutLocal.setObjectName(u"verticalLayoutLocal")
        self.verticalLayoutLocal.setContentsMargins(0, 10, 0, 0)
        self.labelLocal = QLabel(self.localZimWidget)
        self.labelLocal.setObjectName(u"labelLocal")
        self.labelLocal.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)

        self.verticalLayoutLocal.addWidget(self.labelLocal)

        self.listLocalZims = QListWidget(self.localZimWidget)
        self.listLocalZims.setObjectName(u"listLocalZims")

        self.verticalLayoutLocal.addWidget(self.listLocalZims)

        self.splitter.addWidget(self.localZimWidget)

        self.verticalLayoutZim.addWidget(self.splitter)

        self.tabWidget.addTab(self.tabZim, "")
        self.tabKnowledge = QWidget()
        self.tabKnowledge.setObjectName(u"tabKnowledge")
        self.verticalLayoutKnowledge = QVBoxLayout(self.tabKnowledge)
        self.verticalLayoutKnowledge.setSpacing(0)
        self.verticalLayoutKnowledge.setObjectName(u"verticalLayoutKnowledge")
        self.verticalLayoutKnowledge.setContentsMargins(0, 0, 0, 0)
        self.knowledgeFolderContainer = QWidget(self.tabKnowledge)
        self.knowledgeFolderContainer.setObjectName(u"knowledgeFolderContainer")
        self.knowledgeFolderLayout = QVBoxLayout(self.knowledgeFolderContainer)
        self.knowledgeFolderLayout.setSpacing(0)
        self.knowledgeFolderLayout.setObjectName(u"knowledgeFolderLayout")
        self.knowledgeFolderLayout.setContentsMargins(0, 0, 0, 0)

        self.verticalLayoutKnowledge.addWidget(self.knowledgeFolderContainer)

        self.tabWidget.addTab(self.tabKnowledge, "")

        self.gridLayout.addWidget(self.tabWidget, 3, 0, 1, 1)

        self.line = QFrame(documents)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 4, 0, 1, 1)

        self.knowledge_base_panel_widget = KnowledgeBasePanelWidget(documents)
        self.knowledge_base_panel_widget.setObjectName(u"knowledge_base_panel_widget")

        self.gridLayout.addWidget(self.knowledge_base_panel_widget, 5, 0, 1, 1)


        self.retranslateUi(documents)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(documents)
    # setupUi

    def retranslateUi(self, documents):
        documents.setWindowTitle(QCoreApplication.translate("documents", u"Documents", None))
        self.label.setText(QCoreApplication.translate("documents", u"LLM knowledge base", None))
        self.labelDocuments.setStyleSheet(QCoreApplication.translate("documents", u"font-weight: bold;", None))
        self.labelDocuments.setText(QCoreApplication.translate("documents", u"Documents", None))
        ___qtablewidgetitem = self.documentsTableWidget.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("documents", u"Title", None));
        ___qtablewidgetitem1 = self.documentsTableWidget.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("documents", u"Active", None));
        ___qtablewidgetitem2 = self.documentsTableWidget.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("documents", u"Indexed", None));
        ___qtablewidgetitem3 = self.documentsTableWidget.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("documents", u"Error", None));
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabDocuments), QCoreApplication.translate("documents", u"Documents", None))
        self.labelRemote.setText(QCoreApplication.translate("documents", u"Kiwix Library Search Results", None))
        self.kiwixSearchBar.setPlaceholderText(QCoreApplication.translate("documents", u"Search Kiwix Library (title, keyword, language code)...", None))
        self.kiwixLangLabel.setText(QCoreApplication.translate("documents", u"Lang:", None))
        self.kiwixLangCombo.setItemText(0, QCoreApplication.translate("documents", u"eng", None))
        self.kiwixLangCombo.setItemText(1, QCoreApplication.translate("documents", u"all", None))

        self.kiwixSearchButton.setText(QCoreApplication.translate("documents", u"Search", None))
        self.labelLocal.setText(QCoreApplication.translate("documents", u"Local ZIM Files", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabZim), QCoreApplication.translate("documents", u"Kiwix ZIM", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabKnowledge), QCoreApplication.translate("documents", u"Knowledge", None))
    # retranslateUi

