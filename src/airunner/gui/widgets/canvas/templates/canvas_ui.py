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

from airunner.gui.widgets.canvas.custom_view import CustomGraphicsView
from airunner.gui.widgets.stablediffusion.stablediffusion_generator_form import StableDiffusionGeneratorForm
from airunner.gui.widgets.stablediffusion.stablediffusion_tool_tab_widget import StablediffusionToolTabWidget
import airunner.feather_rc

class Ui_canvas(object):
    def setupUi(self, canvas):
        if not canvas.objectName():
            canvas.setObjectName(u"canvas")
        canvas.resize(789, 579)
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
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy1)
        self.widget.setMaximumSize(QSize(16777215, 50))
        self.verticalLayout = QVBoxLayout(self.widget)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.widget1 = QWidget(self.widget)
        self.widget1.setObjectName(u"widget1")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.widget1.sizePolicy().hasHeightForWidth())
        self.widget1.setSizePolicy(sizePolicy2)
        self.widget1.setMinimumSize(QSize(370, 50))
        self.widget1.setMaximumSize(QSize(16777215, 50))
        self.widget1.setBaseSize(QSize(0, 50))
        self.horizontalLayout_2 = QHBoxLayout(self.widget1)
        self.horizontalLayout_2.setSpacing(5)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(5, 0, 0, 0)
        self.actionNew = QPushButton(self.widget1)
        self.actionNew.setObjectName(u"actionNew")
        self.actionNew.setMinimumSize(QSize(30, 30))
        self.actionNew.setMaximumSize(QSize(30, 30))
        self.actionNew.setCursor(QCursor(Qt.PointingHandCursor))
        icon = QIcon()
        icon.addFile(u":/light/icons/feather/light/file-plus.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.actionNew.setIcon(icon)
        self.actionNew.setFlat(True)

        self.horizontalLayout_2.addWidget(self.actionNew)

        self.actionImport = QPushButton(self.widget1)
        self.actionImport.setObjectName(u"actionImport")
        self.actionImport.setMinimumSize(QSize(30, 30))
        self.actionImport.setMaximumSize(QSize(30, 30))
        self.actionImport.setCursor(QCursor(Qt.PointingHandCursor))
        icon1 = QIcon()
        icon1.addFile(u":/light/icons/feather/light/folder.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.actionImport.setIcon(icon1)
        self.actionImport.setFlat(True)

        self.horizontalLayout_2.addWidget(self.actionImport)

        self.actionExport = QPushButton(self.widget1)
        self.actionExport.setObjectName(u"actionExport")
        self.actionExport.setMinimumSize(QSize(30, 30))
        self.actionExport.setMaximumSize(QSize(30, 30))
        self.actionExport.setCursor(QCursor(Qt.PointingHandCursor))
        icon2 = QIcon()
        icon2.addFile(u":/light/icons/feather/light/save.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.actionExport.setIcon(icon2)
        self.actionExport.setFlat(True)

        self.horizontalLayout_2.addWidget(self.actionExport)

        self.line = QFrame(self.widget1)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.VLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.horizontalLayout_2.addWidget(self.line)

        self.recenter_Grid_Button = QPushButton(self.widget1)
        self.recenter_Grid_Button.setObjectName(u"recenter_Grid_Button")
        self.recenter_Grid_Button.setMinimumSize(QSize(30, 30))
        self.recenter_Grid_Button.setMaximumSize(QSize(30, 30))
        self.recenter_Grid_Button.setCursor(QCursor(Qt.PointingHandCursor))
        icon3 = QIcon()
        icon3.addFile(u":/light/icons/feather/light/target.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.recenter_Grid_Button.setIcon(icon3)
        self.recenter_Grid_Button.setFlat(True)

        self.horizontalLayout_2.addWidget(self.recenter_Grid_Button)

        self.actionToggle_Active_Grid_Area = QPushButton(self.widget1)
        self.actionToggle_Active_Grid_Area.setObjectName(u"actionToggle_Active_Grid_Area")
        self.actionToggle_Active_Grid_Area.setMinimumSize(QSize(30, 30))
        self.actionToggle_Active_Grid_Area.setMaximumSize(QSize(30, 30))
        self.actionToggle_Active_Grid_Area.setCursor(QCursor(Qt.PointingHandCursor))
        icon4 = QIcon()
        icon4.addFile(u":/light/icons/feather/light/object-selected-icon.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.actionToggle_Active_Grid_Area.setIcon(icon4)
        self.actionToggle_Active_Grid_Area.setCheckable(True)
        self.actionToggle_Active_Grid_Area.setFlat(True)

        self.horizontalLayout_2.addWidget(self.actionToggle_Active_Grid_Area)

        self.actionToggle_Brush = QPushButton(self.widget1)
        self.actionToggle_Brush.setObjectName(u"actionToggle_Brush")
        self.actionToggle_Brush.setMinimumSize(QSize(30, 30))
        self.actionToggle_Brush.setMaximumSize(QSize(30, 30))
        self.actionToggle_Brush.setCursor(QCursor(Qt.PointingHandCursor))
        icon5 = QIcon()
        icon5.addFile(u":/light/icons/feather/light/pencil-icon.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.actionToggle_Brush.setIcon(icon5)
        self.actionToggle_Brush.setCheckable(True)
        self.actionToggle_Brush.setFlat(True)

        self.horizontalLayout_2.addWidget(self.actionToggle_Brush)

        self.actionToggle_Eraser = QPushButton(self.widget1)
        self.actionToggle_Eraser.setObjectName(u"actionToggle_Eraser")
        self.actionToggle_Eraser.setMinimumSize(QSize(30, 30))
        self.actionToggle_Eraser.setMaximumSize(QSize(30, 30))
        self.actionToggle_Eraser.setCursor(QCursor(Qt.PointingHandCursor))
        icon6 = QIcon()
        icon6.addFile(u":/light/icons/feather/light/eraser-icon.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.actionToggle_Eraser.setIcon(icon6)
        self.actionToggle_Eraser.setCheckable(True)
        self.actionToggle_Eraser.setFlat(True)

        self.horizontalLayout_2.addWidget(self.actionToggle_Eraser)

        self.actionToggle_Grid = QPushButton(self.widget1)
        self.actionToggle_Grid.setObjectName(u"actionToggle_Grid")
        self.actionToggle_Grid.setMinimumSize(QSize(30, 30))
        self.actionToggle_Grid.setMaximumSize(QSize(30, 30))
        self.actionToggle_Grid.setCursor(QCursor(Qt.PointingHandCursor))
        icon7 = QIcon()
        icon7.addFile(u":/light/icons/feather/light/grid.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.actionToggle_Grid.setIcon(icon7)
        self.actionToggle_Grid.setCheckable(True)
        self.actionToggle_Grid.setFlat(True)

        self.horizontalLayout_2.addWidget(self.actionToggle_Grid)

        self.line_2 = QFrame(self.widget1)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.VLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.horizontalLayout_2.addWidget(self.line_2)

        self.actionUndo = QPushButton(self.widget1)
        self.actionUndo.setObjectName(u"actionUndo")
        self.actionUndo.setMinimumSize(QSize(30, 30))
        self.actionUndo.setMaximumSize(QSize(30, 30))
        self.actionUndo.setCursor(QCursor(Qt.PointingHandCursor))
        icon8 = QIcon()
        icon8.addFile(u":/light/icons/feather/light/corner-up-left.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.actionUndo.setIcon(icon8)
        self.actionUndo.setFlat(True)

        self.horizontalLayout_2.addWidget(self.actionUndo)

        self.actionRedo = QPushButton(self.widget1)
        self.actionRedo.setObjectName(u"actionRedo")
        self.actionRedo.setMinimumSize(QSize(30, 30))
        self.actionRedo.setMaximumSize(QSize(30, 30))
        self.actionRedo.setCursor(QCursor(Qt.PointingHandCursor))
        icon9 = QIcon()
        icon9.addFile(u":/light/icons/feather/light/corner-up-right.svg", QSize(), QIcon.Normal, QIcon.Off)
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
        self.actionNew.clicked.connect(canvas.action_new)
        self.actionToggle_Eraser.toggled.connect(canvas.action_toggle_eraser)
        self.actionExport.clicked.connect(canvas.action_export)
        self.actionRedo.clicked.connect(canvas.action_redo)
        self.actionToggle_Grid.toggled.connect(canvas.action_toggle_grid)
        self.actionToggle_Brush.toggled.connect(canvas.action_toggle_brush)
        self.actionUndo.clicked.connect(canvas.action_undo)
        self.recenter_Grid_Button.clicked.connect(canvas.action_recenter)
        self.actionImport.clicked.connect(canvas.action_import)
        self.actionToggle_Active_Grid_Area.toggled.connect(canvas.action_toggle_active_grid_area)

        QMetaObject.connectSlotsByName(canvas)
    # setupUi

    def retranslateUi(self, canvas):
        canvas.setWindowTitle(QCoreApplication.translate("canvas", u"Form", None))
        self.actionNew.setText("")
        self.actionImport.setText("")
        self.actionExport.setText("")
#if QT_CONFIG(tooltip)
        self.recenter_Grid_Button.setToolTip(QCoreApplication.translate("canvas", u"Recenter grid", None))
#endif // QT_CONFIG(tooltip)
        self.recenter_Grid_Button.setText("")
#if QT_CONFIG(tooltip)
        self.actionToggle_Active_Grid_Area.setToolTip(QCoreApplication.translate("canvas", u"Move active grid area", None))
#endif // QT_CONFIG(tooltip)
        self.actionToggle_Active_Grid_Area.setText("")
#if QT_CONFIG(tooltip)
        self.actionToggle_Brush.setToolTip(QCoreApplication.translate("canvas", u"Toggle brush tool", None))
#endif // QT_CONFIG(tooltip)
        self.actionToggle_Brush.setText("")
#if QT_CONFIG(tooltip)
        self.actionToggle_Eraser.setToolTip(QCoreApplication.translate("canvas", u"Toggle earser tool", None))
#endif // QT_CONFIG(tooltip)
        self.actionToggle_Eraser.setText("")
#if QT_CONFIG(tooltip)
        self.actionToggle_Grid.setToolTip(QCoreApplication.translate("canvas", u"Toggle grid", None))
#endif // QT_CONFIG(tooltip)
        self.actionToggle_Grid.setText("")
        self.actionUndo.setText("")
        self.actionRedo.setText("")
        self.canvas_container.setProperty("canvas_type", QCoreApplication.translate("canvas", u"brush", None))
    # retranslateUi

