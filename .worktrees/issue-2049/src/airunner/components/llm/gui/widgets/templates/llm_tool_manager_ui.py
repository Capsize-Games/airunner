# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'llm_tool_manager.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QSpacerItem, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget)

class Ui_llm_tool_manager(object):
    def setupUi(self, llm_tool_manager):
        if not llm_tool_manager.objectName():
            llm_tool_manager.setObjectName(u"llm_tool_manager")
        llm_tool_manager.resize(800, 600)
        self.verticalLayout = QVBoxLayout(llm_tool_manager)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.title_label = QLabel(llm_tool_manager)
        self.title_label.setObjectName(u"title_label")

        self.verticalLayout.addWidget(self.title_label)

        self.button_layout = QHBoxLayout()
        self.button_layout.setObjectName(u"button_layout")
        self.create_tool_button = QPushButton(llm_tool_manager)
        self.create_tool_button.setObjectName(u"create_tool_button")
        icon = QIcon(QIcon.fromTheme(u"list-add"))
        self.create_tool_button.setIcon(icon)

        self.button_layout.addWidget(self.create_tool_button)

        self.reload_tools_button = QPushButton(llm_tool_manager)
        self.reload_tools_button.setObjectName(u"reload_tools_button")
        icon1 = QIcon(QIcon.fromTheme(u"view-refresh"))
        self.reload_tools_button.setIcon(icon1)

        self.button_layout.addWidget(self.reload_tools_button)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.button_layout.addItem(self.horizontalSpacer)

        self.search_box = QLineEdit(llm_tool_manager)
        self.search_box.setObjectName(u"search_box")

        self.button_layout.addWidget(self.search_box)


        self.verticalLayout.addLayout(self.button_layout)

        self.tools_table = QTableWidget(llm_tool_manager)
        if (self.tools_table.columnCount() < 7):
            self.tools_table.setColumnCount(7)
        __qtablewidgetitem = QTableWidgetItem()
        self.tools_table.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.tools_table.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.tools_table.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.tools_table.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.tools_table.setHorizontalHeaderItem(4, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.tools_table.setHorizontalHeaderItem(5, __qtablewidgetitem5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.tools_table.setHorizontalHeaderItem(6, __qtablewidgetitem6)
        self.tools_table.setObjectName(u"tools_table")
        self.tools_table.setAlternatingRowColors(True)
        self.tools_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tools_table.setSortingEnabled(True)

        self.verticalLayout.addWidget(self.tools_table)


        self.retranslateUi(llm_tool_manager)
        self.create_tool_button.clicked.connect(llm_tool_manager.on_create_tool_clicked)
        self.reload_tools_button.clicked.connect(llm_tool_manager.on_reload_tools_clicked)
        self.search_box.textChanged.connect(llm_tool_manager.on_search_changed)

        QMetaObject.connectSlotsByName(llm_tool_manager)
    # setupUi

    def retranslateUi(self, llm_tool_manager):
        llm_tool_manager.setWindowTitle(QCoreApplication.translate("llm_tool_manager", u"LLM Tool Manager", None))
        self.title_label.setText(QCoreApplication.translate("llm_tool_manager", u"LLM Tool Manager", None))
        self.title_label.setStyleSheet(QCoreApplication.translate("llm_tool_manager", u"font-size: 18px; font-weight: bold; padding: 10px;", None))
        self.create_tool_button.setText(QCoreApplication.translate("llm_tool_manager", u"Create New Tool", None))
        self.reload_tools_button.setText(QCoreApplication.translate("llm_tool_manager", u"Reload Tools", None))
        self.search_box.setPlaceholderText(QCoreApplication.translate("llm_tool_manager", u"Search tools...", None))
        ___qtablewidgetitem = self.tools_table.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("llm_tool_manager", u"Name", None));
        ___qtablewidgetitem1 = self.tools_table.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("llm_tool_manager", u"Description", None));
        ___qtablewidgetitem2 = self.tools_table.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("llm_tool_manager", u"Created By", None));
        ___qtablewidgetitem3 = self.tools_table.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("llm_tool_manager", u"Version", None));
        ___qtablewidgetitem4 = self.tools_table.horizontalHeaderItem(4)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("llm_tool_manager", u"Success Rate", None));
        ___qtablewidgetitem5 = self.tools_table.horizontalHeaderItem(5)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("llm_tool_manager", u"Enabled", None));
        ___qtablewidgetitem6 = self.tools_table.horizontalHeaderItem(6)
        ___qtablewidgetitem6.setText(QCoreApplication.translate("llm_tool_manager", u"Actions", None));
    # retranslateUi

