# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'canvas.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy, QSpacerItem,
    QSplitter, QVBoxLayout, QWidget)

from airunner.components.application.gui.widgets.slider.slider_widget import SliderWidget
from airunner.components.art.gui.widgets.canvas.custom_view import CustomGraphicsView
import airunner.feather_rc

class Ui_canvas(object):
    def setupUi(self, canvas):
        if not canvas.objectName():
            canvas.setObjectName(u"canvas")
        canvas.resize(760, 531)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(canvas.sizePolicy().hasHeightForWidth())
        canvas.setSizePolicy(sizePolicy)
        canvas.setMinimumSize(QSize(760, 0))
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
        self.gridLayout_4 = QGridLayout(self.central_widget)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.gridLayout_4.setVerticalSpacing(0)
        self.gridLayout_4.setContentsMargins(0, 0, 0, 0)
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
        self.horizontalLayout_2.setContentsMargins(5, 0, 5, 1)
        self.new_button = QPushButton(self.widget1)
        self.new_button.setObjectName(u"new_button")
        self.new_button.setMinimumSize(QSize(30, 30))
        self.new_button.setMaximumSize(QSize(30, 30))
        self.new_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon = QIcon()
        icon.addFile(u":/light/icons/feather/light/file-plus.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.new_button.setIcon(icon)
        self.new_button.setFlat(False)

        self.horizontalLayout_2.addWidget(self.new_button)

        self.open_art_document = QPushButton(self.widget1)
        self.open_art_document.setObjectName(u"open_art_document")
        self.open_art_document.setMinimumSize(QSize(30, 30))
        self.open_art_document.setMaximumSize(QSize(30, 30))
        self.open_art_document.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon1 = QIcon()
        icon1.addFile(u":/light/icons/feather/light/folder.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.open_art_document.setIcon(icon1)

        self.horizontalLayout_2.addWidget(self.open_art_document)

        self.save_art_document = QPushButton(self.widget1)
        self.save_art_document.setObjectName(u"save_art_document")
        self.save_art_document.setMinimumSize(QSize(30, 30))
        self.save_art_document.setMaximumSize(QSize(30, 30))
        self.save_art_document.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon2 = QIcon()
        icon2.addFile(u":/light/icons/feather/light/save.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.save_art_document.setIcon(icon2)

        self.horizontalLayout_2.addWidget(self.save_art_document)

        self.line_7 = QFrame(self.widget1)
        self.line_7.setObjectName(u"line_7")
        self.line_7.setFrameShape(QFrame.Shape.VLine)
        self.line_7.setFrameShadow(QFrame.Shadow.Sunken)

        self.horizontalLayout_2.addWidget(self.line_7)

        self.import_button = QPushButton(self.widget1)
        self.import_button.setObjectName(u"import_button")
        self.import_button.setMinimumSize(QSize(30, 30))
        self.import_button.setMaximumSize(QSize(30, 30))
        self.import_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon3 = QIcon()
        icon3.addFile(u":/light/icons/lucide/light/image-down.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.import_button.setIcon(icon3)
        self.import_button.setFlat(False)

        self.horizontalLayout_2.addWidget(self.import_button)

        self.export_button = QPushButton(self.widget1)
        self.export_button.setObjectName(u"export_button")
        self.export_button.setMinimumSize(QSize(30, 30))
        self.export_button.setMaximumSize(QSize(30, 30))
        self.export_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon4 = QIcon()
        icon4.addFile(u":/light/icons/lucide/light/image-up.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.export_button.setIcon(icon4)
        self.export_button.setFlat(False)

        self.horizontalLayout_2.addWidget(self.export_button)

        self.line = QFrame(self.widget1)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.VLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.horizontalLayout_2.addWidget(self.line)

        self.align_center_horizontal = QPushButton(self.widget1)
        self.align_center_horizontal.setObjectName(u"align_center_horizontal")
        self.align_center_horizontal.setMinimumSize(QSize(30, 30))
        self.align_center_horizontal.setMaximumSize(QSize(30, 30))
        self.align_center_horizontal.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon5 = QIcon()
        icon5.addFile(u":/light/icons/lucide/light/align-center-horizontal.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.align_center_horizontal.setIcon(icon5)
        self.align_center_horizontal.setFlat(False)

        self.horizontalLayout_2.addWidget(self.align_center_horizontal)

        self.align_center_vertical = QPushButton(self.widget1)
        self.align_center_vertical.setObjectName(u"align_center_vertical")
        self.align_center_vertical.setMinimumSize(QSize(30, 30))
        self.align_center_vertical.setMaximumSize(QSize(30, 30))
        self.align_center_vertical.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon6 = QIcon()
        icon6.addFile(u":/light/icons/lucide/light/align-center-vertical.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.align_center_vertical.setIcon(icon6)

        self.horizontalLayout_2.addWidget(self.align_center_vertical)

        self.active_grid_area_button = QPushButton(self.widget1)
        self.active_grid_area_button.setObjectName(u"active_grid_area_button")
        self.active_grid_area_button.setMinimumSize(QSize(30, 30))
        self.active_grid_area_button.setMaximumSize(QSize(30, 30))
        self.active_grid_area_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon7 = QIcon()
        icon7.addFile(u":/light/icons/feather/light/object-selected-icon.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.active_grid_area_button.setIcon(icon7)
        self.active_grid_area_button.setCheckable(True)
        self.active_grid_area_button.setFlat(False)

        self.horizontalLayout_2.addWidget(self.active_grid_area_button)

        self.move_button = QPushButton(self.widget1)
        self.move_button.setObjectName(u"move_button")
        self.move_button.setMinimumSize(QSize(30, 30))
        self.move_button.setMaximumSize(QSize(30, 30))
        self.move_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon8 = QIcon()
        icon8.addFile(u":/light/icons/feather/light/move.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.move_button.setIcon(icon8)
        self.move_button.setCheckable(True)

        self.horizontalLayout_2.addWidget(self.move_button)

        self.line_4 = QFrame(self.widget1)
        self.line_4.setObjectName(u"line_4")
        self.line_4.setFrameShape(QFrame.Shape.VLine)
        self.line_4.setFrameShadow(QFrame.Shadow.Sunken)

        self.horizontalLayout_2.addWidget(self.line_4)

        self.filter_button = QPushButton(self.widget1)
        self.filter_button.setObjectName(u"filter_button")
        self.filter_button.setMinimumSize(QSize(30, 30))
        self.filter_button.setMaximumSize(QSize(30, 30))
        self.filter_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon9 = QIcon()
        icon9.addFile(u":/light/icons/feather/light/filter.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.filter_button.setIcon(icon9)

        self.horizontalLayout_2.addWidget(self.filter_button)

        self.line_5 = QFrame(self.widget1)
        self.line_5.setObjectName(u"line_5")
        self.line_5.setFrameShape(QFrame.Shape.VLine)
        self.line_5.setFrameShadow(QFrame.Shadow.Sunken)

        self.horizontalLayout_2.addWidget(self.line_5)

        self.grid_button = QPushButton(self.widget1)
        self.grid_button.setObjectName(u"grid_button")
        self.grid_button.setMinimumSize(QSize(30, 30))
        self.grid_button.setMaximumSize(QSize(30, 30))
        self.grid_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon10 = QIcon()
        icon10.addFile(u":/light/icons/lucide/light/grid-3x3.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.grid_button.setIcon(icon10)
        self.grid_button.setCheckable(True)
        self.grid_button.setFlat(False)

        self.horizontalLayout_2.addWidget(self.grid_button)

        self.snap_to_grid_button = QPushButton(self.widget1)
        self.snap_to_grid_button.setObjectName(u"snap_to_grid_button")
        self.snap_to_grid_button.setMinimumSize(QSize(30, 30))
        self.snap_to_grid_button.setMaximumSize(QSize(30, 30))
        self.snap_to_grid_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon11 = QIcon()
        icon11.addFile(u":/light/icons/feather/light/link-2.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.snap_to_grid_button.setIcon(icon11)
        self.snap_to_grid_button.setCheckable(True)

        self.horizontalLayout_2.addWidget(self.snap_to_grid_button)

        self.line_2 = QFrame(self.widget1)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.VLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.horizontalLayout_2.addWidget(self.line_2)

        self.remove_background_button = QPushButton(self.widget1)
        self.remove_background_button.setObjectName(u"remove_background_button")
        self.remove_background_button.setMinimumSize(QSize(30, 30))
        self.remove_background_button.setMaximumSize(QSize(30, 30))
        self.remove_background_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon12 = QIcon()
        icon12.addFile(u":/light/icons/lucide/light/image-minus.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.remove_background_button.setIcon(icon12)

        self.horizontalLayout_2.addWidget(self.remove_background_button)

        self.line_8 = QFrame(self.widget1)
        self.line_8.setObjectName(u"line_8")
        self.line_8.setFrameShape(QFrame.Shape.VLine)
        self.line_8.setFrameShadow(QFrame.Shadow.Sunken)

        self.horizontalLayout_2.addWidget(self.line_8)

        self.undo_button = QPushButton(self.widget1)
        self.undo_button.setObjectName(u"undo_button")
        self.undo_button.setMinimumSize(QSize(30, 30))
        self.undo_button.setMaximumSize(QSize(30, 30))
        self.undo_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon13 = QIcon()
        icon13.addFile(u":/light/icons/lucide/light/undo.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.undo_button.setIcon(icon13)
        self.undo_button.setFlat(False)

        self.horizontalLayout_2.addWidget(self.undo_button)

        self.redo_button = QPushButton(self.widget1)
        self.redo_button.setObjectName(u"redo_button")
        self.redo_button.setMinimumSize(QSize(30, 30))
        self.redo_button.setMaximumSize(QSize(30, 30))
        self.redo_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon14 = QIcon()
        icon14.addFile(u":/light/icons/lucide/light/redo.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.redo_button.setIcon(icon14)
        self.redo_button.setFlat(False)

        self.horizontalLayout_2.addWidget(self.redo_button)

        self.horizontalSpacer = QSpacerItem(425, 9, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)

        self.brush_button = QPushButton(self.widget1)
        self.brush_button.setObjectName(u"brush_button")
        self.brush_button.setMinimumSize(QSize(30, 30))
        self.brush_button.setMaximumSize(QSize(30, 30))
        self.brush_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon15 = QIcon()
        icon15.addFile(u":/light/icons/lucide/light/pencil.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.brush_button.setIcon(icon15)
        self.brush_button.setCheckable(True)
        self.brush_button.setFlat(False)

        self.horizontalLayout_2.addWidget(self.brush_button)

        self.eraser_button = QPushButton(self.widget1)
        self.eraser_button.setObjectName(u"eraser_button")
        self.eraser_button.setMinimumSize(QSize(30, 30))
        self.eraser_button.setMaximumSize(QSize(30, 30))
        self.eraser_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon16 = QIcon()
        icon16.addFile(u":/light/icons/lucide/light/eraser.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.eraser_button.setIcon(icon16)
        self.eraser_button.setCheckable(True)
        self.eraser_button.setFlat(False)

        self.horizontalLayout_2.addWidget(self.eraser_button)

        self.brush_size_slider = SliderWidget(self.widget1)
        self.brush_size_slider.setObjectName(u"brush_size_slider")
        self.brush_size_slider.setMinimumSize(QSize(100, 40))
        self.brush_size_slider.setMaximumSize(QSize(16777215, 40))
        self.brush_size_slider.setProperty(u"slider_minimum", 1)
        self.brush_size_slider.setProperty(u"slider_maximum", 100)
        self.brush_size_slider.setProperty(u"spinbox_minimum", 1)
        self.brush_size_slider.setProperty(u"spinbox_maximum", 100)
        self.brush_size_slider.setProperty(u"slider_tick_interval", 1)
        self.brush_size_slider.setProperty(u"slider_single_step", 1)
        self.brush_size_slider.setProperty(u"slider_page_step", 10)
        self.brush_size_slider.setProperty(u"spinbox_single_step", 1)
        self.brush_size_slider.setProperty(u"spinbox_page_step", 10)
        self.brush_size_slider.setProperty(u"settings_property", u"brush_settings.size")
        self.brush_size_slider.setProperty(u"display_as_float", False)

        self.horizontalLayout_2.addWidget(self.brush_size_slider)

        self.brush_color_button = QPushButton(self.widget1)
        self.brush_color_button.setObjectName(u"brush_color_button")
        self.brush_color_button.setMinimumSize(QSize(30, 30))
        self.brush_color_button.setMaximumSize(QSize(30, 30))
        self.brush_color_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.horizontalLayout_2.addWidget(self.brush_color_button)


        self.verticalLayout.addWidget(self.widget1)

        self.line_3 = QFrame(self.widget)
        self.line_3.setObjectName(u"line_3")
        self.line_3.setFrameShape(QFrame.Shape.HLine)
        self.line_3.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout.addWidget(self.line_3)


        self.gridLayout_4.addWidget(self.widget, 0, 0, 1, 1)

        self.splitter = QSplitter(self.central_widget)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.layoutWidget = QWidget(self.splitter)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.gridLayout_3 = QGridLayout(self.layoutWidget)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setVerticalSpacing(0)
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.canvas_container = CustomGraphicsView(self.layoutWidget)
        self.canvas_container.setObjectName(u"canvas_container")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Expanding)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.canvas_container.sizePolicy().hasHeightForWidth())
        self.canvas_container.setSizePolicy(sizePolicy3)
        self.canvas_container.setMinimumSize(QSize(1, 0))
        self.canvas_container.setBaseSize(QSize(1024, 0))
        self.canvas_container.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.canvas_container.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.gridLayout_3.addWidget(self.canvas_container, 0, 0, 1, 1)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(10, 10, 10, 10)
        self.grid_info = QLabel(self.layoutWidget)
        self.grid_info.setObjectName(u"grid_info")
        sizePolicy1.setHeightForWidth(self.grid_info.sizePolicy().hasHeightForWidth())
        self.grid_info.setSizePolicy(sizePolicy1)
        font = QFont()
        font.setPointSize(10)
        self.grid_info.setFont(font)

        self.horizontalLayout_4.addWidget(self.grid_info)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer_2)

        self.active_item_info = QLabel(self.layoutWidget)
        self.active_item_info.setObjectName(u"active_item_info")
        sizePolicy1.setHeightForWidth(self.active_item_info.sizePolicy().hasHeightForWidth())
        self.active_item_info.setSizePolicy(sizePolicy1)
        self.active_item_info.setFont(font)
        self.active_item_info.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.horizontalLayout_4.addWidget(self.active_item_info)


        self.gridLayout_3.addLayout(self.horizontalLayout_4, 2, 0, 1, 1)

        self.line_6 = QFrame(self.layoutWidget)
        self.line_6.setObjectName(u"line_6")
        self.line_6.setFrameShape(QFrame.Shape.HLine)
        self.line_6.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_3.addWidget(self.line_6, 1, 0, 1, 1)

        self.splitter.addWidget(self.layoutWidget)

        self.gridLayout_4.addWidget(self.splitter, 1, 0, 1, 1)


        self.gridLayout.addWidget(self.central_widget, 0, 0, 1, 1)


        self.retranslateUi(canvas)

        QMetaObject.connectSlotsByName(canvas)
    # setupUi

    def retranslateUi(self, canvas):
        canvas.setWindowTitle(QCoreApplication.translate("canvas", u"Form", None))
#if QT_CONFIG(tooltip)
        self.new_button.setToolTip(QCoreApplication.translate("canvas", u"New art document", None))
#endif // QT_CONFIG(tooltip)
        self.new_button.setText("")
#if QT_CONFIG(tooltip)
        self.open_art_document.setToolTip(QCoreApplication.translate("canvas", u"Open art document", None))
#endif // QT_CONFIG(tooltip)
        self.open_art_document.setText("")
#if QT_CONFIG(tooltip)
        self.save_art_document.setToolTip(QCoreApplication.translate("canvas", u"Save art document", None))
#endif // QT_CONFIG(tooltip)
        self.save_art_document.setText("")
#if QT_CONFIG(tooltip)
        self.import_button.setToolTip(QCoreApplication.translate("canvas", u"Import image", None))
#endif // QT_CONFIG(tooltip)
        self.import_button.setText("")
#if QT_CONFIG(tooltip)
        self.export_button.setToolTip(QCoreApplication.translate("canvas", u"Export image", None))
#endif // QT_CONFIG(tooltip)
        self.export_button.setText("")
#if QT_CONFIG(tooltip)
        self.align_center_horizontal.setToolTip(QCoreApplication.translate("canvas", u"Align center horizontal", None))
#endif // QT_CONFIG(tooltip)
        self.align_center_horizontal.setText("")
#if QT_CONFIG(tooltip)
        self.align_center_vertical.setToolTip(QCoreApplication.translate("canvas", u"Align center vertical", None))
#endif // QT_CONFIG(tooltip)
        self.align_center_vertical.setText("")
#if QT_CONFIG(tooltip)
        self.active_grid_area_button.setToolTip(QCoreApplication.translate("canvas", u"Move active grid area", None))
#endif // QT_CONFIG(tooltip)
        self.active_grid_area_button.setText("")
#if QT_CONFIG(tooltip)
        self.move_button.setToolTip(QCoreApplication.translate("canvas", u"Move layer tool", None))
#endif // QT_CONFIG(tooltip)
        self.move_button.setText("")
#if QT_CONFIG(tooltip)
        self.filter_button.setToolTip(QCoreApplication.translate("canvas", u"Toggle filters", None))
#endif // QT_CONFIG(tooltip)
        self.filter_button.setText("")
#if QT_CONFIG(tooltip)
        self.grid_button.setToolTip(QCoreApplication.translate("canvas", u"Toggle grid", None))
#endif // QT_CONFIG(tooltip)
        self.grid_button.setText("")
#if QT_CONFIG(tooltip)
        self.snap_to_grid_button.setToolTip(QCoreApplication.translate("canvas", u"Snap to grid", None))
#endif // QT_CONFIG(tooltip)
        self.snap_to_grid_button.setText("")
#if QT_CONFIG(tooltip)
        self.remove_background_button.setToolTip(QCoreApplication.translate("canvas", u"Remove Background", None))
#endif // QT_CONFIG(tooltip)
        self.remove_background_button.setText("")
#if QT_CONFIG(tooltip)
        self.undo_button.setToolTip(QCoreApplication.translate("canvas", u"Undo", None))
#endif // QT_CONFIG(tooltip)
        self.undo_button.setText("")
#if QT_CONFIG(tooltip)
        self.redo_button.setToolTip(QCoreApplication.translate("canvas", u"Redo", None))
#endif // QT_CONFIG(tooltip)
        self.redo_button.setText("")
#if QT_CONFIG(tooltip)
        self.brush_button.setToolTip(QCoreApplication.translate("canvas", u"Toggle brush tool", None))
#endif // QT_CONFIG(tooltip)
        self.brush_button.setText("")
#if QT_CONFIG(tooltip)
        self.eraser_button.setToolTip(QCoreApplication.translate("canvas", u"Toggle earser tool", None))
#endif // QT_CONFIG(tooltip)
        self.eraser_button.setText("")
#if QT_CONFIG(tooltip)
        self.brush_size_slider.setToolTip(QCoreApplication.translate("canvas", u"Brush Size", None))
#endif // QT_CONFIG(tooltip)
        self.brush_size_slider.setProperty(u"label_text", "")
#if QT_CONFIG(tooltip)
        self.brush_color_button.setToolTip(QCoreApplication.translate("canvas", u"Brush Color", None))
#endif // QT_CONFIG(tooltip)
        self.brush_color_button.setText("")
        self.canvas_container.setProperty(u"canvas_type", QCoreApplication.translate("canvas", u"brush", None))
        self.grid_info.setText(QCoreApplication.translate("canvas", u"TextLabel", None))
        self.active_item_info.setText("")
    # retranslateUi

