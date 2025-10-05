# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'document_editor.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QHBoxLayout, QPlainTextEdit,
    QPushButton, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)
import airunner.feather_rc

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(334, 300)
        self.gridLayout = QGridLayout(Form)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.lines = QWidget(Form)
        self.lines.setObjectName(u"lines")
        self.line_numbers = QVBoxLayout(self.lines)
        self.line_numbers.setObjectName(u"line_numbers")

        self.gridLayout.addWidget(self.lines, 0, 0, 1, 1)

        self.editor = QPlainTextEdit(Form)
        self.editor.setObjectName(u"editor")

        self.gridLayout.addWidget(self.editor, 0, 1, 1, 1)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(5, 5, 5, 5)
        self.run_button = QPushButton(Form)
        self.run_button.setObjectName(u"run_button")
        self.run_button.setMinimumSize(QSize(30, 30))
        self.run_button.setMaximumSize(QSize(30, 30))
        self.run_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon = QIcon()
        icon.addFile(u":/dark/icons/feather/dark/play.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.run_button.setIcon(icon)

        self.horizontalLayout_2.addWidget(self.run_button)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_2)


        self.gridLayout.addLayout(self.horizontalLayout_2, 1, 0, 1, 2)


        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
#if QT_CONFIG(tooltip)
        self.run_button.setToolTip(QCoreApplication.translate("Form", u"Run script", None))
#endif // QT_CONFIG(tooltip)
        self.run_button.setText("")
    # retranslateUi

