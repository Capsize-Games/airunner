# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'canvas.ui'
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
    QPushButton, QSizePolicy, QSpacerItem, QSplitter,
    QVBoxLayout, QWidget)

from airunner.widgets.canvas.custom_view import CustomGraphicsView
from airunner.widgets.stablediffusion.stablediffusion_generator_form import StableDiffusionGeneratorForm
from airunner.widgets.stablediffusion.stablediffusion_tool_tab_widget import StablediffusionToolTabWidget
import airunner.resources_dark_rc
import airunner.resources_light_rc

class Ui_canvas(object):
    def setupUi(self, canvas):
        if not canvas.objectName():
            canvas.setObjectName(u"canvas")
        canvas.resize(843, 579)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(canvas.sizePolicy().hasHeightForWidth())
        canvas.setSizePolicy(sizePolicy)
        canvas.setMinimumSize(QSize(0, 0))
        canvas.setStyleSheet(u"b")
        self.gridLayout = QGridLayout(canvas)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.central_widget = QWidget(canvas)
        self.central_widget.setObjectName(u"central_widget")
        sizePolicy.setHeightForWidth(self.central_widget.sizePolicy().hasHeightForWidth())
        self.central_widget.setSizePolicy(sizePolicy)
        self.central_widget.setMinimumSize(QSize(0, 0))
        self.central_widget.setStyleSheet(u"")
        self.gridLayout_2 = QGridLayout(self.central_widget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setVerticalSpacing(0)
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.widget = QWidget(self.central_widget)
        self.widget.setObjectName(u"widget")
        self.widget.setMaximumSize(QSize(16777215, 70))
        self.verticalLayout = QVBoxLayout(self.widget)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.widget1 = QWidget(self.widget)
        self.widget1.setObjectName(u"widget1")
        self.widget1.setMaximumSize(QSize(16777215, 56))
        self.horizontalLayout_2 = QHBoxLayout(self.widget1)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.actionNew = QPushButton(self.widget1)
        self.actionNew.setObjectName(u"actionNew")
        icon = QIcon(QIcon.fromTheme(u"document-new"))
        self.actionNew.setIcon(icon)
        self.actionNew.setFlat(True)

        self.horizontalLayout_2.addWidget(self.actionNew)

        self.actionImport = QPushButton(self.widget1)
        self.actionImport.setObjectName(u"actionImport")
        icon1 = QIcon(QIcon.fromTheme(u"document-open"))
        self.actionImport.setIcon(icon1)
        self.actionImport.setFlat(True)

        self.horizontalLayout_2.addWidget(self.actionImport)

        self.actionExport = QPushButton(self.widget1)
        self.actionExport.setObjectName(u"actionExport")
        icon2 = QIcon(QIcon.fromTheme(u"document-save"))
        self.actionExport.setIcon(icon2)
        self.actionExport.setFlat(True)

        self.horizontalLayout_2.addWidget(self.actionExport)

        self.line = QFrame(self.widget1)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.VLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.horizontalLayout_2.addWidget(self.line)

        self.actionToggle_Active_Grid_Area = QPushButton(self.widget1)
        self.actionToggle_Active_Grid_Area.setObjectName(u"actionToggle_Active_Grid_Area")
        icon3 = QIcon()
        icon3.addFile(u":/icons/light/object-selected-icon.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.actionToggle_Active_Grid_Area.setIcon(icon3)
        self.actionToggle_Active_Grid_Area.setCheckable(True)
        self.actionToggle_Active_Grid_Area.setFlat(True)

        self.horizontalLayout_2.addWidget(self.actionToggle_Active_Grid_Area)

        self.actionToggle_Brush = QPushButton(self.widget1)
        self.actionToggle_Brush.setObjectName(u"actionToggle_Brush")
        icon4 = QIcon()
        icon4.addFile(u":/icons/light/pencil-icon.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.actionToggle_Brush.setIcon(icon4)
        self.actionToggle_Brush.setCheckable(True)
        self.actionToggle_Brush.setFlat(True)

        self.horizontalLayout_2.addWidget(self.actionToggle_Brush)

        self.actionToggle_Eraser = QPushButton(self.widget1)
        self.actionToggle_Eraser.setObjectName(u"actionToggle_Eraser")
        icon5 = QIcon()
        icon5.addFile(u":/icons/light/eraser-icon.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.actionToggle_Eraser.setIcon(icon5)
        self.actionToggle_Eraser.setCheckable(True)
        self.actionToggle_Eraser.setFlat(True)

        self.horizontalLayout_2.addWidget(self.actionToggle_Eraser)

        self.actionToggle_Grid = QPushButton(self.widget1)
        self.actionToggle_Grid.setObjectName(u"actionToggle_Grid")
        icon6 = QIcon()
        icon6.addFile(u":/icons/light/frame-grid-icon.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.actionToggle_Grid.setIcon(icon6)
        self.actionToggle_Grid.setCheckable(True)
        self.actionToggle_Grid.setFlat(True)

        self.horizontalLayout_2.addWidget(self.actionToggle_Grid)

        self.actionMask_toggle = QPushButton(self.widget1)
        self.actionMask_toggle.setObjectName(u"actionMask_toggle")
        icon7 = QIcon()
        icon7.addFile(u":/icons/light/layer-icon.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.actionMask_toggle.setIcon(icon7)
        self.actionMask_toggle.setCheckable(True)
        self.actionMask_toggle.setFlat(True)

        self.horizontalLayout_2.addWidget(self.actionMask_toggle)

        self.line_2 = QFrame(self.widget1)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.VLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.horizontalLayout_2.addWidget(self.line_2)

        self.actionUndo = QPushButton(self.widget1)
        self.actionUndo.setObjectName(u"actionUndo")
        icon8 = QIcon(QIcon.fromTheme(u"undo"))
        self.actionUndo.setIcon(icon8)
        self.actionUndo.setFlat(True)

        self.horizontalLayout_2.addWidget(self.actionUndo)

        self.actionRedo = QPushButton(self.widget1)
        self.actionRedo.setObjectName(u"actionRedo")
        icon9 = QIcon(QIcon.fromTheme(u"redo"))
        self.actionRedo.setIcon(icon9)
        self.actionRedo.setFlat(True)

        self.horizontalLayout_2.addWidget(self.actionRedo)

        self.horizontalSpacer = QSpacerItem(425, 9, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)


        self.verticalLayout.addWidget(self.widget1)

        self.line_3 = QFrame(self.widget)
        self.line_3.setObjectName(u"line_3")
        self.line_3.setFrameShape(QFrame.Shape.HLine)
        self.line_3.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout.addWidget(self.line_3)


        self.gridLayout_2.addWidget(self.widget, 1, 0, 1, 1)

        self.canvas_splitter = QSplitter(self.central_widget)
        self.canvas_splitter.setObjectName(u"canvas_splitter")
        self.canvas_splitter.setOrientation(Qt.Orientation.Horizontal)
        self.prompts = StableDiffusionGeneratorForm(self.canvas_splitter)
        self.prompts.setObjectName(u"prompts")
        self.canvas_splitter.addWidget(self.prompts)
        self.canvas_container = CustomGraphicsView(self.canvas_splitter)
        self.canvas_container.setObjectName(u"canvas_container")
        self.canvas_container.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.canvas_container.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.canvas_splitter.addWidget(self.canvas_container)
        self.widget2 = StablediffusionToolTabWidget(self.canvas_splitter)
        self.widget2.setObjectName(u"widget2")
        self.canvas_splitter.addWidget(self.widget2)

        self.gridLayout_2.addWidget(self.canvas_splitter, 2, 0, 1, 1)


        self.gridLayout.addWidget(self.central_widget, 0, 0, 1, 1)


        self.retranslateUi(canvas)
        self.actionUndo.clicked.connect(canvas.action_undo)
        self.actionRedo.clicked.connect(canvas.action_redo)
        self.actionMask_toggle.toggled.connect(canvas.action_toggle_mask)
        self.actionToggle_Eraser.toggled.connect(canvas.action_toggle_eraser)
        self.actionToggle_Brush.toggled.connect(canvas.action_toggle_brush)
        self.actionToggle_Active_Grid_Area.toggled.connect(canvas.action_toggle_active_grid_area)
        self.actionExport.clicked.connect(canvas.action_export)
        self.actionImport.clicked.connect(canvas.action_import)
        self.actionNew.clicked.connect(canvas.action_new)
        self.actionToggle_Grid.toggled.connect(canvas.action_toggle_grid)

        QMetaObject.connectSlotsByName(canvas)
    # setupUi

    def retranslateUi(self, canvas):
        canvas.setWindowTitle(QCoreApplication.translate("canvas", u"Form", None))
        self.actionNew.setText("")
        self.actionImport.setText("")
        self.actionExport.setText("")
        self.actionToggle_Active_Grid_Area.setText("")
        self.actionToggle_Brush.setText("")
        self.actionToggle_Eraser.setText("")
        self.actionToggle_Grid.setText("")
        self.actionMask_toggle.setText("")
        self.actionUndo.setText("")
        self.actionRedo.setText("")
        self.canvas_container.setProperty("canvas_type", QCoreApplication.translate("canvas", u"brush", None))
    # retranslateUi

