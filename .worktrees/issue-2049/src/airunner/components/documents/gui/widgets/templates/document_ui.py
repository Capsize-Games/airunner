# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'document.ui'
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
    QCheckBox,
    QGridLayout,
    QPushButton,
    QSizePolicy,
    QWidget,
)
import airunner.feather_rc


class Ui_document_widget(object):
    def setupUi(self, document_widget):
        if not document_widget.objectName():
            document_widget.setObjectName("document_widget")
        document_widget.resize(400, 170)
        self.gridLayout = QGridLayout(document_widget)
        self.gridLayout.setObjectName("gridLayout")
        self.delete_button = QPushButton(document_widget)
        self.delete_button.setObjectName("delete_button")
        self.delete_button.setMinimumSize(QSize(30, 30))
        self.delete_button.setMaximumSize(QSize(30, 30))
        self.delete_button.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        icon = QIcon()
        icon.addFile(
            ":/dark/icons/feather/dark/trash-2.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.delete_button.setIcon(icon)

        self.gridLayout.addWidget(self.delete_button, 0, 1, 1, 1)

        self.checkBox = QCheckBox(document_widget)
        self.checkBox.setObjectName("checkBox")

        self.gridLayout.addWidget(self.checkBox, 0, 0, 1, 1)

        self.enabledCheckBox = QCheckBox(document_widget)
        self.enabledCheckBox.setObjectName("enabledCheckBox")

        self.gridLayout.addWidget(self.enabledCheckBox, 0, 2, 1, 1)

        self.retranslateUi(document_widget)

        QMetaObject.connectSlotsByName(document_widget)

    # setupUi

    def retranslateUi(self, document_widget):
        document_widget.setWindowTitle(
            QCoreApplication.translate("document_widget", "Form", None)
        )
        self.delete_button.setText("")
        self.checkBox.setText(
            QCoreApplication.translate("document_widget", "CheckBox", None)
        )
        self.enabledCheckBox.setText(
            QCoreApplication.translate("document_widget", "Enabled", None)
        )

    # retranslateUi
