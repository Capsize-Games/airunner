# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'grid_preferences.ui'
##
## Created by: Qt User Interface Compiler version 6.6.2
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QGridLayout, QLabel,
    QPushButton, QSizePolicy, QSpacerItem, QSpinBox,
    QWidget)

class Ui_grid_preferences(object):
    def setupUi(self, grid_preferences):
        if not grid_preferences.objectName():
            grid_preferences.setObjectName(u"grid_preferences")
        grid_preferences.resize(332, 323)
        self.gridLayout = QGridLayout(grid_preferences)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLineColorButton = QPushButton(grid_preferences)
        self.gridLineColorButton.setObjectName(u"gridLineColorButton")

        self.gridLayout.addWidget(self.gridLineColorButton, 4, 0, 1, 1)

        self.snap_to_grid_checkbox = QCheckBox(grid_preferences)
        self.snap_to_grid_checkbox.setObjectName(u"snap_to_grid_checkbox")
        font = QFont()
        font.setBold(False)
        self.snap_to_grid_checkbox.setFont(font)

        self.gridLayout.addWidget(self.snap_to_grid_checkbox, 7, 0, 1, 1)

        self.grid_line_width_spinbox = QSpinBox(grid_preferences)
        self.grid_line_width_spinbox.setObjectName(u"grid_line_width_spinbox")

        self.gridLayout.addWidget(self.grid_line_width_spinbox, 3, 0, 1, 1)

        self.show_grid_checkbox = QCheckBox(grid_preferences)
        self.show_grid_checkbox.setObjectName(u"show_grid_checkbox")
        self.show_grid_checkbox.setFont(font)

        self.gridLayout.addWidget(self.show_grid_checkbox, 6, 0, 1, 1)

        self.grid_size_spinbox = QSpinBox(grid_preferences)
        self.grid_size_spinbox.setObjectName(u"grid_size_spinbox")
        self.grid_size_spinbox.setMaximum(512)

        self.gridLayout.addWidget(self.grid_size_spinbox, 1, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 72, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 8, 0, 1, 1)

        self.label = QLabel(grid_preferences)
        self.label.setObjectName(u"label")
        self.label.setFont(font)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.label_2 = QLabel(grid_preferences)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setFont(font)

        self.gridLayout.addWidget(self.label_2, 2, 0, 1, 1)

        self.canvas_color = QPushButton(grid_preferences)
        self.canvas_color.setObjectName(u"canvas_color")

        self.gridLayout.addWidget(self.canvas_color, 5, 0, 1, 1)


        self.retranslateUi(grid_preferences)
        self.grid_size_spinbox.valueChanged.connect(grid_preferences.grid_size_changed)
        self.grid_line_width_spinbox.valueChanged.connect(grid_preferences.line_width_changed)
        self.gridLineColorButton.clicked.connect(grid_preferences.action_button_clicked_grid_line_color)
        self.canvas_color.clicked.connect(grid_preferences.action_button_clicked_canvas_color)
        self.show_grid_checkbox.toggled.connect(grid_preferences.action_toggled_show_grid)
        self.snap_to_grid_checkbox.toggled.connect(grid_preferences.action_toggled_snap_to_grid)

        QMetaObject.connectSlotsByName(grid_preferences)
    # setupUi

    def retranslateUi(self, grid_preferences):
        grid_preferences.setWindowTitle(QCoreApplication.translate("grid_preferences", u"Form", None))
        self.gridLineColorButton.setText(QCoreApplication.translate("grid_preferences", u"Grid Line Color", None))
        self.snap_to_grid_checkbox.setText(QCoreApplication.translate("grid_preferences", u"Snap to Grid", None))
        self.show_grid_checkbox.setText(QCoreApplication.translate("grid_preferences", u"Show Grid", None))
        self.label.setText(QCoreApplication.translate("grid_preferences", u"Grid Size", None))
        self.label_2.setText(QCoreApplication.translate("grid_preferences", u"Grid Line Width", None))
        self.canvas_color.setText(QCoreApplication.translate("grid_preferences", u"Canvas Color", None))
    # retranslateUi

