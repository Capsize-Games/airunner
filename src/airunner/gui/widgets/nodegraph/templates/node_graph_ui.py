# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'node_graph.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (
    QCoreApplication,
    QDate,
    QDateTime,
    QLocale,
    QMetaObject,
    QObject,
    QPoint,
    QRect,
    QSize,
    QTime,
    QUrl,
    Qt,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QCursor,
    QFont,
    QFontDatabase,
    QGradient,
    QIcon,
    QImage,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPalette,
    QPixmap,
    QRadialGradient,
    QTransform,
)
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QSplitter,
    QWidget,
)

from airunner.gui.widgets.nodegraph.variables_panel import VariablesPanelWidget
import airunner.feather_rc


class Ui_node_graph_widget(object):
    def setupUi(self, node_graph_widget):
        if not node_graph_widget.objectName():
            node_graph_widget.setObjectName("node_graph_widget")
        node_graph_widget.resize(1331, 853)
        self.gridLayout_5 = QGridLayout(node_graph_widget)
        self.gridLayout_5.setSpacing(0)
        self.gridLayout_5.setObjectName("gridLayout_5")
        self.gridLayout_5.setContentsMargins(10, 10, 10, 10)
        self.widget = QWidget(node_graph_widget)
        self.widget.setObjectName("widget")
        sizePolicy = QSizePolicy(
            QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Maximum
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy)
        self.widget.setMinimumSize(QSize(260, 0))
        self.gridLayout_3 = QGridLayout(self.widget)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.gridLayout_3.setHorizontalSpacing(5)
        self.gridLayout_3.setVerticalSpacing(0)
        self.gridLayout_3.setContentsMargins(0, 0, 0, 10)
        self.new_button = QPushButton(self.widget)
        self.new_button.setObjectName("new_button")
        icon = QIcon()
        icon.addFile(
            ":/dark/icons/feather/dark/file-plus.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.new_button.setIcon(icon)

        self.gridLayout_3.addWidget(self.new_button, 0, 4, 1, 1)

        self.delete_button = QPushButton(self.widget)
        self.delete_button.setObjectName("delete_button")
        self.delete_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon1 = QIcon()
        icon1.addFile(
            ":/dark/icons/feather/dark/trash-2.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.delete_button.setIcon(icon1)

        self.gridLayout_3.addWidget(self.delete_button, 0, 8, 1, 1)

        self.stop_button = QPushButton(self.widget)
        self.stop_button.setObjectName("stop_button")
        self.stop_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon2 = QIcon()
        icon2.addFile(
            ":/dark/icons/feather/dark/stop-circle.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.stop_button.setIcon(icon2)

        self.gridLayout_3.addWidget(self.stop_button, 0, 2, 1, 1)

        self.clear_button = QPushButton(self.widget)
        self.clear_button.setObjectName("clear_button")
        icon3 = QIcon()
        icon3.addFile(
            ":/dark/icons/feather/dark/x-circle.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.clear_button.setIcon(icon3)

        self.gridLayout_3.addWidget(self.clear_button, 0, 6, 1, 1)

        self.play_button = QPushButton(self.widget)
        self.play_button.setObjectName("play_button")
        self.play_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon4 = QIcon()
        icon4.addFile(
            ":/dark/icons/feather/dark/play.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.play_button.setIcon(icon4)

        self.gridLayout_3.addWidget(self.play_button, 0, 0, 1, 1)

        self.load_button = QPushButton(self.widget)
        self.load_button.setObjectName("load_button")
        self.load_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon5 = QIcon()
        icon5.addFile(
            ":/dark/icons/feather/dark/folder.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.load_button.setIcon(icon5)

        self.gridLayout_3.addWidget(self.load_button, 0, 7, 1, 1)

        self.save_button = QPushButton(self.widget)
        self.save_button.setObjectName("save_button")
        self.save_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon6 = QIcon()
        icon6.addFile(
            ":/dark/icons/feather/dark/save.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.save_button.setIcon(icon6)

        self.gridLayout_3.addWidget(self.save_button, 0, 5, 1, 1)

        self.horizontalSpacer = QSpacerItem(
            729, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )

        self.gridLayout_3.addItem(self.horizontalSpacer, 0, 3, 1, 1)

        self.pause_button = QPushButton(self.widget)
        self.pause_button.setObjectName("pause_button")
        self.pause_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon7 = QIcon()
        icon7.addFile(
            ":/dark/icons/feather/dark/pause-circle.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.pause_button.setIcon(icon7)

        self.gridLayout_3.addWidget(self.pause_button, 0, 1, 1, 1)

        self.gridLayout_5.addWidget(self.widget, 0, 0, 1, 1)

        self.splitter = QSplitter(node_graph_widget)
        self.splitter.setObjectName("splitter")
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.variables = VariablesPanelWidget(self.splitter)
        self.variables.setObjectName("variables")
        self.splitter.addWidget(self.variables)
        self.graph = QWidget(self.splitter)
        self.graph.setObjectName("graph")
        self.gridLayout_2 = QGridLayout(self.graph)
        self.gridLayout_2.setSpacing(0)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.gridLayout_2.setContentsMargins(10, 0, 10, 0)
        self.splitter.addWidget(self.graph)
        self.palette = QWidget(self.splitter)
        self.palette.setObjectName("palette")
        self.gridLayout = QGridLayout(self.palette)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName("gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.splitter.addWidget(self.palette)

        self.gridLayout_5.addWidget(self.splitter, 1, 0, 1, 1)

        self.progressBar = QProgressBar(node_graph_widget)
        self.progressBar.setObjectName("progressBar")
        self.progressBar.setValue(24)

        self.gridLayout_5.addWidget(self.progressBar, 2, 0, 1, 1)

        self.retranslateUi(node_graph_widget)

        QMetaObject.connectSlotsByName(node_graph_widget)

    # setupUi

    def retranslateUi(self, node_graph_widget):
        node_graph_widget.setWindowTitle(
            QCoreApplication.translate("node_graph_widget", "Form", None)
        )
        # if QT_CONFIG(tooltip)
        self.new_button.setToolTip(
            QCoreApplication.translate("node_graph_widget", "New workflow", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.new_button.setText("")
        # if QT_CONFIG(tooltip)
        self.delete_button.setToolTip(
            QCoreApplication.translate("node_graph_widget", "Delete workflow", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.delete_button.setText("")
        # if QT_CONFIG(tooltip)
        self.stop_button.setToolTip(
            QCoreApplication.translate("node_graph_widget", "Stop workflow", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.stop_button.setText("")
        # if QT_CONFIG(tooltip)
        self.clear_button.setToolTip(
            QCoreApplication.translate("node_graph_widget", "Clear workflow", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.clear_button.setText("")
        # if QT_CONFIG(tooltip)
        self.play_button.setToolTip(
            QCoreApplication.translate("node_graph_widget", "Run workflow", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.play_button.setText("")
        # if QT_CONFIG(tooltip)
        self.load_button.setToolTip(
            QCoreApplication.translate("node_graph_widget", "Load workflow", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.load_button.setText("")
        # if QT_CONFIG(tooltip)
        self.save_button.setToolTip(
            QCoreApplication.translate("node_graph_widget", "Save workflow", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.save_button.setText("")
        # if QT_CONFIG(tooltip)
        self.pause_button.setToolTip(
            QCoreApplication.translate("node_graph_widget", "Pause workflow", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.pause_button.setText("")

    # retranslateUi
