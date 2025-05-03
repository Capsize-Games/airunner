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
        self.horizontalLayout_2.setContentsMargins(5, 0, 0, 1)
        self.new_button = QPushButton(self.widget1)
        self.new_button.setObjectName(u"new_button")
        self.new_button.setMinimumSize(QSize(30, 30))
        self.new_button.setMaximumSize(QSize(30, 30))
        self.new_button.setCursor(QCursor(Qt.PointingHandCursor))
        icon = QIcon()
        icon.addFile(u":/light/icons/feather/light/file-plus.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.new_button.setIcon(icon)
        self.new_button.setFlat(False)

        self.horizontalLayout_2.addWidget(self.new_button)

        self.import_button = QPushButton(self.widget1)
        self.import_button.setObjectName(u"import_button")
        self.import_button.setMinimumSize(QSize(30, 30))
        self.import_button.setMaximumSize(QSize(30, 30))
        self.import_button.setCursor(QCursor(Qt.PointingHandCursor))
        icon1 = QIcon()
        icon1.addFile(u":/light/icons/feather/light/folder.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.import_button.setIcon(icon1)
        self.import_button.setFlat(False)

        self.horizontalLayout_2.addWidget(self.import_button)

        self.export_button = QPushButton(self.widget1)
        self.export_button.setObjectName(u"export_button")
        self.export_button.setMinimumSize(QSize(30, 30))
        self.export_button.setMaximumSize(QSize(30, 30))
        self.export_button.setCursor(QCursor(Qt.PointingHandCursor))
        icon2 = QIcon()
        icon2.addFile(u":/light/icons/feather/light/save.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.export_button.setIcon(icon2)
        self.export_button.setFlat(False)

        self.horizontalLayout_2.addWidget(self.export_button)

        self.line = QFrame(self.widget1)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.VLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.horizontalLayout_2.addWidget(self.line)

        self.recenter_button = QPushButton(self.widget1)
        self.recenter_button.setObjectName(u"recenter_button")
        self.recenter_button.setMinimumSize(QSize(30, 30))
        self.recenter_button.setMaximumSize(QSize(30, 30))
        self.recenter_button.setCursor(QCursor(Qt.PointingHandCursor))
        icon3 = QIcon()
        icon3.addFile(u":/light/icons/feather/light/target.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.recenter_button.setIcon(icon3)
        self.recenter_button.setFlat(False)

        self.horizontalLayout_2.addWidget(self.recenter_button)

        self.active_grid_area_button = QPushButton(self.widget1)
        self.active_grid_area_button.setObjectName(u"active_grid_area_button")
        self.active_grid_area_button.setMinimumSize(QSize(30, 30))
        self.active_grid_area_button.setMaximumSize(QSize(30, 30))
        self.active_grid_area_button.setCursor(QCursor(Qt.PointingHandCursor))
        icon4 = QIcon()
        icon4.addFile(u":/light/icons/feather/light/object-selected-icon.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.active_grid_area_button.setIcon(icon4)
        self.active_grid_area_button.setCheckable(True)
        self.active_grid_area_button.setFlat(False)

        self.horizontalLayout_2.addWidget(self.active_grid_area_button)

        self.brush_button = QPushButton(self.widget1)
        self.brush_button.setObjectName(u"brush_button")
        self.brush_button.setMinimumSize(QSize(30, 30))
        self.brush_button.setMaximumSize(QSize(30, 30))
        self.brush_button.setCursor(QCursor(Qt.PointingHandCursor))
        icon5 = QIcon()
        icon5.addFile(u":/light/icons/feather/light/pencil-icon.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.brush_button.setIcon(icon5)
        self.brush_button.setCheckable(True)
        self.brush_button.setFlat(False)

        self.horizontalLayout_2.addWidget(self.brush_button)

        self.eraser_button = QPushButton(self.widget1)
        self.eraser_button.setObjectName(u"eraser_button")
        self.eraser_button.setMinimumSize(QSize(30, 30))
        self.eraser_button.setMaximumSize(QSize(30, 30))
        self.eraser_button.setCursor(QCursor(Qt.PointingHandCursor))
        icon6 = QIcon()
        icon6.addFile(u":/light/icons/feather/light/eraser-icon.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.eraser_button.setIcon(icon6)
        self.eraser_button.setCheckable(True)
        self.eraser_button.setFlat(False)

        self.horizontalLayout_2.addWidget(self.eraser_button)

        self.grid_button = QPushButton(self.widget1)
        self.grid_button.setObjectName(u"grid_button")
        self.grid_button.setMinimumSize(QSize(30, 30))
        self.grid_button.setMaximumSize(QSize(30, 30))
        self.grid_button.setCursor(QCursor(Qt.PointingHandCursor))
        icon7 = QIcon()
        icon7.addFile(u":/light/icons/feather/light/grid.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.grid_button.setIcon(icon7)
        self.grid_button.setCheckable(True)
        self.grid_button.setFlat(False)

        self.horizontalLayout_2.addWidget(self.grid_button)

        self.line_2 = QFrame(self.widget1)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.VLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.horizontalLayout_2.addWidget(self.line_2)

        self.undo_button = QPushButton(self.widget1)
        self.undo_button.setObjectName(u"undo_button")
        self.undo_button.setMinimumSize(QSize(30, 30))
        self.undo_button.setMaximumSize(QSize(30, 30))
        self.undo_button.setCursor(QCursor(Qt.PointingHandCursor))
        icon8 = QIcon()
        icon8.addFile(u":/light/icons/feather/light/corner-up-left.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.undo_button.setIcon(icon8)
        self.undo_button.setFlat(False)

        self.horizontalLayout_2.addWidget(self.undo_button)

        self.redo_button = QPushButton(self.widget1)
        self.redo_button.setObjectName(u"redo_button")
        self.redo_button.setMinimumSize(QSize(30, 30))
        self.redo_button.setMaximumSize(QSize(30, 30))
        self.redo_button.setCursor(QCursor(Qt.PointingHandCursor))
        icon9 = QIcon()
        icon9.addFile(u":/light/icons/feather/light/corner-up-right.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.redo_button.setIcon(icon9)
        self.redo_button.setFlat(False)

        self.horizontalLayout_2.addWidget(self.redo_button)

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

        QMetaObject.connectSlotsByName(canvas)
    # setupUi

    def retranslateUi(self, canvas):
        canvas.setWindowTitle(QCoreApplication.translate("canvas", u"Form", None))
        self.new_button.setText("")
        self.import_button.setText("")
        self.export_button.setText("")
#if QT_CONFIG(tooltip)
        self.recenter_button.setToolTip(QCoreApplication.translate("canvas", u"Recenter grid", None))
#endif // QT_CONFIG(tooltip)
        self.recenter_button.setText("")
#if QT_CONFIG(tooltip)
        self.active_grid_area_button.setToolTip(QCoreApplication.translate("canvas", u"Move active grid area", None))
#endif // QT_CONFIG(tooltip)
        self.active_grid_area_button.setText("")
#if QT_CONFIG(tooltip)
        self.brush_button.setToolTip(QCoreApplication.translate("canvas", u"Toggle brush tool", None))
#endif // QT_CONFIG(tooltip)
        self.brush_button.setText("")
#if QT_CONFIG(tooltip)
        self.eraser_button.setToolTip(QCoreApplication.translate("canvas", u"Toggle earser tool", None))
#endif // QT_CONFIG(tooltip)
        self.eraser_button.setText("")
#if QT_CONFIG(tooltip)
        self.grid_button.setToolTip(QCoreApplication.translate("canvas", u"Toggle grid", None))
#endif // QT_CONFIG(tooltip)
        self.grid_button.setText("")
        self.undo_button.setText("")
        self.redo_button.setText("")
        self.canvas_container.setProperty("canvas_type", QCoreApplication.translate("canvas", u"brush", None))
    # retranslateUi

