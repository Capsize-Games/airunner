# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'node_graph.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QPushButton, QSizePolicy,
    QSpacerItem, QSplitter, QWidget)

from airunner.gui.widgets.nodegraph.variables_panel import VariablesPanelWidget
import airunner.feather_rc

class Ui_node_graph_widget(object):
    def setupUi(self, node_graph_widget):
        if not node_graph_widget.objectName():
            node_graph_widget.setObjectName(u"node_graph_widget")
        node_graph_widget.resize(1331, 853)
        self.gridLayout_5 = QGridLayout(node_graph_widget)
        self.gridLayout_5.setSpacing(0)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.gridLayout_5.setContentsMargins(10, 10, 10, 10)
        self.widget = QWidget(node_graph_widget)
        self.widget.setObjectName(u"widget")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy)
        self.gridLayout_3 = QGridLayout(self.widget)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setHorizontalSpacing(5)
        self.gridLayout_3.setVerticalSpacing(0)
        self.gridLayout_3.setContentsMargins(0, 0, 0, 10)
        self.pause_button = QPushButton(self.widget)
        self.pause_button.setObjectName(u"pause_button")
        self.pause_button.setCursor(QCursor(Qt.PointingHandCursor))
        icon = QIcon()
        icon.addFile(u":/dark/icons/feather/dark/pause-circle.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.pause_button.setIcon(icon)

        self.gridLayout_3.addWidget(self.pause_button, 0, 1, 1, 1)

        self.save_button = QPushButton(self.widget)
        self.save_button.setObjectName(u"save_button")
        self.save_button.setCursor(QCursor(Qt.PointingHandCursor))
        icon1 = QIcon()
        icon1.addFile(u":/dark/icons/feather/dark/save.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.save_button.setIcon(icon1)

        self.gridLayout_3.addWidget(self.save_button, 0, 4, 1, 1)

        self.play_button = QPushButton(self.widget)
        self.play_button.setObjectName(u"play_button")
        self.play_button.setCursor(QCursor(Qt.PointingHandCursor))
        icon2 = QIcon()
        icon2.addFile(u":/dark/icons/feather/dark/play.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.play_button.setIcon(icon2)

        self.gridLayout_3.addWidget(self.play_button, 0, 0, 1, 1)

        self.stop_button = QPushButton(self.widget)
        self.stop_button.setObjectName(u"stop_button")
        self.stop_button.setCursor(QCursor(Qt.PointingHandCursor))
        icon3 = QIcon()
        icon3.addFile(u":/dark/icons/feather/dark/stop-circle.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.stop_button.setIcon(icon3)

        self.gridLayout_3.addWidget(self.stop_button, 0, 2, 1, 1)

        self.edit_button = QPushButton(self.widget)
        self.edit_button.setObjectName(u"edit_button")
        self.edit_button.setCursor(QCursor(Qt.PointingHandCursor))
        icon4 = QIcon()
        icon4.addFile(u":/dark/icons/feather/dark/edit.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.edit_button.setIcon(icon4)

        self.gridLayout_3.addWidget(self.edit_button, 0, 6, 1, 1)

        self.load_button = QPushButton(self.widget)
        self.load_button.setObjectName(u"load_button")
        self.load_button.setCursor(QCursor(Qt.PointingHandCursor))
        icon5 = QIcon()
        icon5.addFile(u":/dark/icons/feather/dark/folder.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.load_button.setIcon(icon5)

        self.gridLayout_3.addWidget(self.load_button, 0, 7, 1, 1)

        self.horizontalSpacer = QSpacerItem(729, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_3.addItem(self.horizontalSpacer, 0, 3, 1, 1)

        self.delete_button = QPushButton(self.widget)
        self.delete_button.setObjectName(u"delete_button")
        self.delete_button.setCursor(QCursor(Qt.PointingHandCursor))
        icon6 = QIcon()
        icon6.addFile(u":/dark/icons/feather/dark/trash-2.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.delete_button.setIcon(icon6)

        self.gridLayout_3.addWidget(self.delete_button, 0, 8, 1, 1)

        self.pushButton = QPushButton(self.widget)
        self.pushButton.setObjectName(u"pushButton")
        icon7 = QIcon()
        icon7.addFile(u":/dark/icons/feather/dark/x-circle.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.pushButton.setIcon(icon7)

        self.gridLayout_3.addWidget(self.pushButton, 0, 5, 1, 1)


        self.gridLayout_5.addWidget(self.widget, 0, 0, 1, 1)

        self.splitter = QSplitter(node_graph_widget)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.variables = VariablesPanelWidget(self.splitter)
        self.variables.setObjectName(u"variables")
        self.gridLayout_4 = QGridLayout(self.variables)
        self.gridLayout_4.setSpacing(0)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.gridLayout_4.setContentsMargins(0, 0, 10, 0)
        self.splitter.addWidget(self.variables)
        self.graph = QWidget(self.splitter)
        self.graph.setObjectName(u"graph")
        self.gridLayout_2 = QGridLayout(self.graph)
        self.gridLayout_2.setSpacing(0)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(10, 0, 10, 0)
        self.splitter.addWidget(self.graph)
        self.palette = QWidget(self.splitter)
        self.palette.setObjectName(u"palette")
        self.gridLayout = QGridLayout(self.palette)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.splitter.addWidget(self.palette)

        self.gridLayout_5.addWidget(self.splitter, 1, 0, 1, 1)


        self.retranslateUi(node_graph_widget)
        self.play_button.clicked.connect(node_graph_widget.on_run_workflow)
        self.pause_button.clicked.connect(node_graph_widget.on_pause_workflow)
        self.stop_button.clicked.connect(node_graph_widget.on_stop_workflow)
        self.load_button.clicked.connect(node_graph_widget.on_load_workflow)
        self.save_button.clicked.connect(node_graph_widget.on_save_workflow)
        self.edit_button.clicked.connect(node_graph_widget.on_edit_workflow)
        self.delete_button.clicked.connect(node_graph_widget.on_delete_workflow)
        self.pushButton.clicked.connect(node_graph_widget.on_clear_workflow)

        QMetaObject.connectSlotsByName(node_graph_widget)
    # setupUi

    def retranslateUi(self, node_graph_widget):
        node_graph_widget.setWindowTitle(QCoreApplication.translate("node_graph_widget", u"Form", None))
#if QT_CONFIG(tooltip)
        self.pause_button.setToolTip(QCoreApplication.translate("node_graph_widget", u"Pause workflow", None))
#endif // QT_CONFIG(tooltip)
        self.pause_button.setText("")
#if QT_CONFIG(tooltip)
        self.save_button.setToolTip(QCoreApplication.translate("node_graph_widget", u"Save workflow", None))
#endif // QT_CONFIG(tooltip)
        self.save_button.setText("")
#if QT_CONFIG(tooltip)
        self.play_button.setToolTip(QCoreApplication.translate("node_graph_widget", u"Run workflow", None))
#endif // QT_CONFIG(tooltip)
        self.play_button.setText("")
#if QT_CONFIG(tooltip)
        self.stop_button.setToolTip(QCoreApplication.translate("node_graph_widget", u"Stop workflow", None))
#endif // QT_CONFIG(tooltip)
        self.stop_button.setText("")
#if QT_CONFIG(tooltip)
        self.edit_button.setToolTip(QCoreApplication.translate("node_graph_widget", u"Edit workflow", None))
#endif // QT_CONFIG(tooltip)
        self.edit_button.setText("")
#if QT_CONFIG(tooltip)
        self.load_button.setToolTip(QCoreApplication.translate("node_graph_widget", u"Load workflow", None))
#endif // QT_CONFIG(tooltip)
        self.load_button.setText("")
#if QT_CONFIG(tooltip)
        self.delete_button.setToolTip(QCoreApplication.translate("node_graph_widget", u"Delete workflow", None))
#endif // QT_CONFIG(tooltip)
        self.delete_button.setText("")
#if QT_CONFIG(tooltip)
        self.pushButton.setToolTip(QCoreApplication.translate("node_graph_widget", u"Clear workflow", None))
#endif // QT_CONFIG(tooltip)
        self.pushButton.setText("")
    # retranslateUi

