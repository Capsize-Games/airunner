# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'llm_history_item.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy, QSpacerItem,
    QTextBrowser, QWidget)

class Ui_llm_history_item_widget(object):
    def setupUi(self, llm_history_item_widget):
        if not llm_history_item_widget.objectName():
            llm_history_item_widget.setObjectName(u"llm_history_item_widget")
        llm_history_item_widget.resize(384, 217)
        self.gridLayout = QGridLayout(llm_history_item_widget)
        self.gridLayout.setSpacing(10)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(10, 0, 0, 0)
        self.conversation_description = QTextBrowser(llm_history_item_widget)
        self.conversation_description.setObjectName(u"conversation_description")

        self.gridLayout.addWidget(self.conversation_description, 0, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(5)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.timestamp = QLabel(llm_history_item_widget)
        self.timestamp.setObjectName(u"timestamp")

        self.horizontalLayout.addWidget(self.timestamp)

        self.line = QFrame(llm_history_item_widget)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.VLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.horizontalLayout.addWidget(self.line)

        self.botname = QLabel(llm_history_item_widget)
        self.botname.setObjectName(u"botname")

        self.horizontalLayout.addWidget(self.botname)

        self.line_2 = QFrame(llm_history_item_widget)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.VLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.horizontalLayout.addWidget(self.line_2)

        self.pushButton = QPushButton(llm_history_item_widget)
        self.pushButton.setObjectName(u"pushButton")
        icon = QIcon(QIcon.fromTheme(u"document-open"))
        self.pushButton.setIcon(icon)

        self.horizontalLayout.addWidget(self.pushButton)

        self.pushButton_2 = QPushButton(llm_history_item_widget)
        self.pushButton_2.setObjectName(u"pushButton_2")
        icon1 = QIcon(QIcon.fromTheme(u"user-trash"))
        self.pushButton_2.setIcon(icon1)

        self.horizontalLayout.addWidget(self.pushButton_2)


        self.gridLayout.addLayout(self.horizontalLayout, 1, 0, 1, 1)


        self.retranslateUi(llm_history_item_widget)
        self.pushButton.clicked.connect(llm_history_item_widget.action_load_conversation_clicked)
        self.pushButton_2.clicked.connect(llm_history_item_widget.action_delete_conversation_clicked)

        QMetaObject.connectSlotsByName(llm_history_item_widget)
    # setupUi

    def retranslateUi(self, llm_history_item_widget):
        llm_history_item_widget.setWindowTitle(QCoreApplication.translate("llm_history_item_widget", u"Form", None))
        self.timestamp.setText(QCoreApplication.translate("llm_history_item_widget", u"Date", None))
        self.botname.setText(QCoreApplication.translate("llm_history_item_widget", u"Bot name", None))
#if QT_CONFIG(tooltip)
        self.pushButton.setToolTip(QCoreApplication.translate("llm_history_item_widget", u"Load conversation", None))
#endif // QT_CONFIG(tooltip)
        self.pushButton.setText("")
#if QT_CONFIG(tooltip)
        self.pushButton_2.setToolTip(QCoreApplication.translate("llm_history_item_widget", u"Deleted conversation", None))
#endif // QT_CONFIG(tooltip)
        self.pushButton_2.setText("")
    # retranslateUi

