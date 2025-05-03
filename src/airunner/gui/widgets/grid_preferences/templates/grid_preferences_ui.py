# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'grid_preferences.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QSizePolicy, QSpacerItem, QSpinBox,
    QWidget)

class Ui_grid_preferences(object):
    def setupUi(self, grid_preferences):
        if not grid_preferences.objectName():
            grid_preferences.setObjectName(u"grid_preferences")
        grid_preferences.resize(811, 377)
        self.gridLayout_2 = QGridLayout(grid_preferences)
        self.gridLayout_2.setSpacing(0)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.scrollArea = QScrollArea(grid_preferences)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 809, 375))
        self.gridLayout = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(0)
        self.gridLayout.setVerticalSpacing(10)
        self.gridLayout.setContentsMargins(0, 0, 10, 0)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.gridLineColorButton = QPushButton(self.scrollAreaWidgetContents)
        self.gridLineColorButton.setObjectName(u"gridLineColorButton")

        self.horizontalLayout.addWidget(self.gridLineColorButton)

        self.canvas_color = QPushButton(self.scrollAreaWidgetContents)
        self.canvas_color.setObjectName(u"canvas_color")

        self.horizontalLayout.addWidget(self.canvas_color)


        self.gridLayout.addLayout(self.horizontalLayout, 3, 0, 1, 1)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.groupBox = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout_3 = QGridLayout(self.groupBox)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.grid_size_spinbox = QSpinBox(self.groupBox)
        self.grid_size_spinbox.setObjectName(u"grid_size_spinbox")
        self.grid_size_spinbox.setMaximum(512)

        self.gridLayout_3.addWidget(self.grid_size_spinbox, 1, 0, 1, 1)


        self.horizontalLayout_2.addWidget(self.groupBox)

        self.groupBox_2 = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.gridLayout_4 = QGridLayout(self.groupBox_2)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.grid_line_width_spinbox = QSpinBox(self.groupBox_2)
        self.grid_line_width_spinbox.setObjectName(u"grid_line_width_spinbox")

        self.gridLayout_4.addWidget(self.grid_line_width_spinbox, 0, 0, 1, 1)


        self.horizontalLayout_2.addWidget(self.groupBox_2)


        self.gridLayout.addLayout(self.horizontalLayout_2, 2, 0, 1, 1)

        self.line = QFrame(self.scrollAreaWidgetContents)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 1, 0, 1, 1)

        self.label_3 = QLabel(self.scrollAreaWidgetContents)
        self.label_3.setObjectName(u"label_3")
        font = QFont()
        font.setBold(True)
        self.label_3.setFont(font)

        self.gridLayout.addWidget(self.label_3, 0, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 8, 0, 1, 1)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.show_grid_checkbox = QCheckBox(self.scrollAreaWidgetContents)
        self.show_grid_checkbox.setObjectName(u"show_grid_checkbox")
        font1 = QFont()
        font1.setBold(False)
        self.show_grid_checkbox.setFont(font1)

        self.horizontalLayout_3.addWidget(self.show_grid_checkbox)

        self.snap_to_grid_checkbox = QCheckBox(self.scrollAreaWidgetContents)
        self.snap_to_grid_checkbox.setObjectName(u"snap_to_grid_checkbox")
        self.snap_to_grid_checkbox.setFont(font1)

        self.horizontalLayout_3.addWidget(self.snap_to_grid_checkbox)


        self.gridLayout.addLayout(self.horizontalLayout_3, 4, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_2.addWidget(self.scrollArea, 0, 0, 1, 1)


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
        self.gridLineColorButton.setText(QCoreApplication.translate("grid_preferences", u"Line Color", None))
        self.canvas_color.setText(QCoreApplication.translate("grid_preferences", u"Canvas Color", None))
        self.groupBox.setTitle(QCoreApplication.translate("grid_preferences", u"Cell Size", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("grid_preferences", u"Line Width", None))
        self.label_3.setText(QCoreApplication.translate("grid_preferences", u"Grid Settings", None))
        self.show_grid_checkbox.setText(QCoreApplication.translate("grid_preferences", u"Show", None))
        self.snap_to_grid_checkbox.setText(QCoreApplication.translate("grid_preferences", u"Snap to", None))
    # retranslateUi

