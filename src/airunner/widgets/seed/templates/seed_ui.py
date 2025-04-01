# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'seed.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QWidget)
import airunner.feather_rc

class Ui_seed_widget(object):
    def setupUi(self, seed_widget):
        if not seed_widget.objectName():
            seed_widget.setObjectName(u"seed_widget")
        seed_widget.resize(558, 92)
        self.gridLayout = QGridLayout(seed_widget)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.lineEdit = QLineEdit(seed_widget)
        self.lineEdit.setObjectName(u"lineEdit")
        font = QFont()
        font.setPointSize(8)
        self.lineEdit.setFont(font)

        self.gridLayout.addWidget(self.lineEdit, 1, 0, 1, 1)

        self.random_button = QPushButton(seed_widget)
        self.random_button.setObjectName(u"random_button")
        self.random_button.setMinimumSize(QSize(24, 24))
        self.random_button.setMaximumSize(QSize(24, 24))
        self.random_button.setCursor(QCursor(Qt.PointingHandCursor))
        icon = QIcon()
        icon.addFile(u":/light/icons/feather/light/dice-game-icon.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.random_button.setIcon(icon)
        self.random_button.setCheckable(True)
        self.random_button.setFlat(True)

        self.gridLayout.addWidget(self.random_button, 1, 1, 1, 1)

        self.label = QLabel(seed_widget)
        self.label.setObjectName(u"label")
        font1 = QFont()
        font1.setPointSize(8)
        font1.setBold(True)
        self.label.setFont(font1)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)


        self.retranslateUi(seed_widget)
        self.lineEdit.textChanged.connect(seed_widget.action_value_changed_seed)
        self.random_button.toggled.connect(seed_widget.action_clicked_button_random_seed)

        QMetaObject.connectSlotsByName(seed_widget)
    # setupUi

    def retranslateUi(self, seed_widget):
        seed_widget.setWindowTitle(QCoreApplication.translate("seed_widget", u"Form", None))
        self.lineEdit.setPlaceholderText(QCoreApplication.translate("seed_widget", u"seed", None))
#if QT_CONFIG(tooltip)
        self.random_button.setToolTip(QCoreApplication.translate("seed_widget", u"Toggle random seed", None))
#endif // QT_CONFIG(tooltip)
        self.random_button.setText("")
        self.label.setText(QCoreApplication.translate("seed_widget", u"Seed", None))
    # retranslateUi

