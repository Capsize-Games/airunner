# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'knowledge_base_panel.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QProgressBar, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget)
import airunner.feather_rc

class Ui_knowledge_base_panel(object):
    def setupUi(self, knowledge_base_panel):
        if not knowledge_base_panel.objectName():
            knowledge_base_panel.setObjectName(u"knowledge_base_panel")
        knowledge_base_panel.resize(400, 328)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(knowledge_base_panel.sizePolicy().hasHeightForWidth())
        knowledge_base_panel.setSizePolicy(sizePolicy)
        knowledge_base_panel.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.verticalLayout = QVBoxLayout(knowledge_base_panel)
        self.verticalLayout.setSpacing(10)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(10, 0, 10, 10)
        self.stats_group = QGroupBox(knowledge_base_panel)
        self.stats_group.setObjectName(u"stats_group")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.stats_group.sizePolicy().hasHeightForWidth())
        self.stats_group.setSizePolicy(sizePolicy1)
        self.gridLayout_2 = QGridLayout(self.stats_group)
        self.gridLayout_2.setSpacing(5)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(10, 10, 10, 10)
        self.total_label = QLabel(self.stats_group)
        self.total_label.setObjectName(u"total_label")

        self.gridLayout_2.addWidget(self.total_label, 0, 0, 1, 1)

        self.total_docs_value = QLabel(self.stats_group)
        self.total_docs_value.setObjectName(u"total_docs_value")
        self.total_docs_value.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.total_docs_value, 0, 1, 1, 1)

        self.indexed_label = QLabel(self.stats_group)
        self.indexed_label.setObjectName(u"indexed_label")

        self.gridLayout_2.addWidget(self.indexed_label, 1, 0, 1, 1)

        self.indexed_docs_value = QLabel(self.stats_group)
        self.indexed_docs_value.setObjectName(u"indexed_docs_value")
        self.indexed_docs_value.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.indexed_docs_value, 1, 1, 1, 1)

        self.unindexed_label = QLabel(self.stats_group)
        self.unindexed_label.setObjectName(u"unindexed_label")

        self.gridLayout_2.addWidget(self.unindexed_label, 2, 0, 1, 1)

        self.unindexed_docs_value = QLabel(self.stats_group)
        self.unindexed_docs_value.setObjectName(u"unindexed_docs_value")
        self.unindexed_docs_value.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.unindexed_docs_value, 2, 1, 1, 1)


        self.verticalLayout.addWidget(self.stats_group)

        self.controlsLayout = QHBoxLayout()
        self.controlsLayout.setSpacing(8)
        self.controlsLayout.setObjectName(u"controlsLayout")
        self.progress_bar = QProgressBar(knowledge_base_panel)
        self.progress_bar.setObjectName(u"progress_bar")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(1)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.progress_bar.sizePolicy().hasHeightForWidth())
        self.progress_bar.setSizePolicy(sizePolicy2)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)

        self.controlsLayout.addWidget(self.progress_bar)

        self.import_button = QPushButton(knowledge_base_panel)
        self.import_button.setObjectName(u"import_button")
        self.import_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon = QIcon()
        icon.addFile(u":/light/icons/lucide/light/import.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.import_button.setIcon(icon)

        self.controlsLayout.addWidget(self.import_button)

        self.index_button = QPushButton(knowledge_base_panel)
        self.index_button.setObjectName(u"index_button")
        self.index_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon1 = QIcon()
        icon1.addFile(u":/light/icons/lucide/light/database.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.index_button.setIcon(icon1)

        self.controlsLayout.addWidget(self.index_button)

        self.cancel_button = QPushButton(knowledge_base_panel)
        self.cancel_button.setObjectName(u"cancel_button")
        self.cancel_button.setEnabled(False)
        self.cancel_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon2 = QIcon()
        icon2.addFile(u":/light/icons/lucide/light/circle-x.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.cancel_button.setIcon(icon2)

        self.controlsLayout.addWidget(self.cancel_button)


        self.verticalLayout.addLayout(self.controlsLayout)


        self.retranslateUi(knowledge_base_panel)

        QMetaObject.connectSlotsByName(knowledge_base_panel)
    # setupUi

    def retranslateUi(self, knowledge_base_panel):
        knowledge_base_panel.setWindowTitle(QCoreApplication.translate("knowledge_base_panel", u"Form", None))
        self.stats_group.setTitle(QCoreApplication.translate("knowledge_base_panel", u"Document Statistics", None))
        self.total_label.setText(QCoreApplication.translate("knowledge_base_panel", u"Total Documents:", None))
        self.total_docs_value.setText(QCoreApplication.translate("knowledge_base_panel", u"0", None))
        self.indexed_label.setText(QCoreApplication.translate("knowledge_base_panel", u"Indexed:", None))
        self.indexed_docs_value.setText(QCoreApplication.translate("knowledge_base_panel", u"0", None))
        self.unindexed_label.setText(QCoreApplication.translate("knowledge_base_panel", u"Unindexed:", None))
        self.unindexed_docs_value.setText(QCoreApplication.translate("knowledge_base_panel", u"0", None))
        self.progress_bar.setFormat(QCoreApplication.translate("knowledge_base_panel", u"%p%", None))
#if QT_CONFIG(tooltip)
        self.import_button.setToolTip(QCoreApplication.translate("knowledge_base_panel", u"Import document", None))
#endif // QT_CONFIG(tooltip)
        self.import_button.setText("")
#if QT_CONFIG(tooltip)
        self.index_button.setToolTip(QCoreApplication.translate("knowledge_base_panel", u"Index all documents", None))
#endif // QT_CONFIG(tooltip)
        self.index_button.setText("")
#if QT_CONFIG(tooltip)
        self.cancel_button.setToolTip(QCoreApplication.translate("knowledge_base_panel", u"Cancel operation", None))
#endif // QT_CONFIG(tooltip)
        self.cancel_button.setText("")
    # retranslateUi

