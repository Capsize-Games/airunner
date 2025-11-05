# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'knowledge_manager.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QSpacerItem, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget)

class Ui_knowledge_manager(object):
    def setupUi(self, knowledge_manager):
        if not knowledge_manager.objectName():
            knowledge_manager.setObjectName(u"knowledge_manager")
        knowledge_manager.resize(1000, 600)
        self.verticalLayout = QVBoxLayout(knowledge_manager)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.title_label = QLabel(knowledge_manager)
        self.title_label.setObjectName(u"title_label")

        self.verticalLayout.addWidget(self.title_label)

        self.button_layout = QHBoxLayout()
        self.button_layout.setObjectName(u"button_layout")
        self.create_fact_button = QPushButton(knowledge_manager)
        self.create_fact_button.setObjectName(u"create_fact_button")
        icon = QIcon(QIcon.fromTheme(u"list-add"))
        self.create_fact_button.setIcon(icon)

        self.button_layout.addWidget(self.create_fact_button)

        self.reload_facts_button = QPushButton(knowledge_manager)
        self.reload_facts_button.setObjectName(u"reload_facts_button")
        icon1 = QIcon(QIcon.fromTheme(u"view-refresh"))
        self.reload_facts_button.setIcon(icon1)

        self.button_layout.addWidget(self.reload_facts_button)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.button_layout.addItem(self.horizontalSpacer)

        self.category_filter = QComboBox(knowledge_manager)
        self.category_filter.setObjectName(u"category_filter")

        self.button_layout.addWidget(self.category_filter)

        self.tag_filter = QLineEdit(knowledge_manager)
        self.tag_filter.setObjectName(u"tag_filter")

        self.button_layout.addWidget(self.tag_filter)

        self.search_box = QLineEdit(knowledge_manager)
        self.search_box.setObjectName(u"search_box")

        self.button_layout.addWidget(self.search_box)


        self.verticalLayout.addLayout(self.button_layout)

        self.facts_table = QTableWidget(knowledge_manager)
        if (self.facts_table.columnCount() < 8):
            self.facts_table.setColumnCount(8)
        __qtablewidgetitem = QTableWidgetItem()
        self.facts_table.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.facts_table.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.facts_table.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.facts_table.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.facts_table.setHorizontalHeaderItem(4, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.facts_table.setHorizontalHeaderItem(5, __qtablewidgetitem5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.facts_table.setHorizontalHeaderItem(6, __qtablewidgetitem6)
        __qtablewidgetitem7 = QTableWidgetItem()
        self.facts_table.setHorizontalHeaderItem(7, __qtablewidgetitem7)
        self.facts_table.setObjectName(u"facts_table")
        self.facts_table.setAlternatingRowColors(True)
        self.facts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.facts_table.setSortingEnabled(True)

        self.verticalLayout.addWidget(self.facts_table)


        self.retranslateUi(knowledge_manager)
        self.create_fact_button.clicked.connect(knowledge_manager.on_create_fact_clicked)
        self.reload_facts_button.clicked.connect(knowledge_manager.on_reload_facts_clicked)
        self.search_box.textChanged.connect(knowledge_manager.on_search_changed)
        self.category_filter.currentTextChanged.connect(knowledge_manager.on_category_filter_changed)
        self.tag_filter.textChanged.connect(knowledge_manager.on_tag_filter_changed)

        QMetaObject.connectSlotsByName(knowledge_manager)
    # setupUi

    def retranslateUi(self, knowledge_manager):
        knowledge_manager.setWindowTitle(QCoreApplication.translate("knowledge_manager", u"Knowledge Manager", None))
        self.title_label.setText(QCoreApplication.translate("knowledge_manager", u"Knowledge Manager", None))
        self.title_label.setStyleSheet(QCoreApplication.translate("knowledge_manager", u"font-size: 18px; font-weight: bold; padding: 10px;", None))
        self.create_fact_button.setText(QCoreApplication.translate("knowledge_manager", u"Create Fact", None))
        self.reload_facts_button.setText(QCoreApplication.translate("knowledge_manager", u"Reload Facts", None))
        self.category_filter.setPlaceholderText(QCoreApplication.translate("knowledge_manager", u"Filter by category...", None))
        self.tag_filter.setPlaceholderText(QCoreApplication.translate("knowledge_manager", u"Filter by tags...", None))
        self.search_box.setPlaceholderText(QCoreApplication.translate("knowledge_manager", u"Search facts...", None))
        ___qtablewidgetitem = self.facts_table.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("knowledge_manager", u"Text", None));
        ___qtablewidgetitem1 = self.facts_table.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("knowledge_manager", u"Category", None));
        ___qtablewidgetitem2 = self.facts_table.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("knowledge_manager", u"Tags", None));
        ___qtablewidgetitem3 = self.facts_table.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("knowledge_manager", u"Confidence", None));
        ___qtablewidgetitem4 = self.facts_table.horizontalHeaderItem(4)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("knowledge_manager", u"Verified", None));
        ___qtablewidgetitem5 = self.facts_table.horizontalHeaderItem(5)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("knowledge_manager", u"Created", None));
        ___qtablewidgetitem6 = self.facts_table.horizontalHeaderItem(6)
        ___qtablewidgetitem6.setText(QCoreApplication.translate("knowledge_manager", u"Access Count", None));
        ___qtablewidgetitem7 = self.facts_table.horizontalHeaderItem(7)
        ___qtablewidgetitem7.setText(QCoreApplication.translate("knowledge_manager", u"Actions", None));
    # retranslateUi

