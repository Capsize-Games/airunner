# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'canvas_layer_container.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QHBoxLayout, QPushButton,
    QScrollArea, QSizePolicy, QSpacerItem, QWidget)
import airunner.feather_rc

class Ui_canvas_layer_container(object):
    def setupUi(self, canvas_layer_container):
        if not canvas_layer_container.objectName():
            canvas_layer_container.setObjectName(u"canvas_layer_container")
        canvas_layer_container.resize(400, 300)
        self.gridLayout = QGridLayout(canvas_layer_container)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.layer_list = QScrollArea(canvas_layer_container)
        self.layer_list.setObjectName(u"layer_list")
        self.layer_list.setWidgetResizable(True)
        self.layer_list_layout = QWidget()
        self.layer_list_layout.setObjectName(u"layer_list_layout")
        self.layer_list_layout.setGeometry(QRect(0, 0, 398, 248))
        self.gridLayout_2 = QGridLayout(self.layer_list_layout)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(10, 10, 10, 10)
        self.layer_list.setWidget(self.layer_list_layout)

        self.gridLayout.addWidget(self.layer_list, 0, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(10, 10, 10, 10)
        self.add_layer = QPushButton(canvas_layer_container)
        self.add_layer.setObjectName(u"add_layer")
        self.add_layer.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon = QIcon()
        icon.addFile(u":/dark/icons/feather/dark/plus.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.add_layer.setIcon(icon)

        self.horizontalLayout.addWidget(self.add_layer)

        self.move_layer_up = QPushButton(canvas_layer_container)
        self.move_layer_up.setObjectName(u"move_layer_up")
        self.move_layer_up.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon1 = QIcon()
        icon1.addFile(u":/dark/icons/feather/dark/chevron-up.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.move_layer_up.setIcon(icon1)

        self.horizontalLayout.addWidget(self.move_layer_up)

        self.move_layer_down = QPushButton(canvas_layer_container)
        self.move_layer_down.setObjectName(u"move_layer_down")
        self.move_layer_down.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon2 = QIcon()
        icon2.addFile(u":/dark/icons/feather/dark/chevron-down.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.move_layer_down.setIcon(icon2)

        self.horizontalLayout.addWidget(self.move_layer_down)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.merge_visible_layers = QPushButton(canvas_layer_container)
        self.merge_visible_layers.setObjectName(u"merge_visible_layers")
        icon3 = QIcon()
        icon3.addFile(u":/dark/icons/feather/dark/arrow-down.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.merge_visible_layers.setIcon(icon3)

        self.horizontalLayout.addWidget(self.merge_visible_layers)

        self.delete_layer = QPushButton(canvas_layer_container)
        self.delete_layer.setObjectName(u"delete_layer")
        self.delete_layer.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon4 = QIcon()
        icon4.addFile(u":/dark/icons/feather/dark/trash-2.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.delete_layer.setIcon(icon4)

        self.horizontalLayout.addWidget(self.delete_layer)


        self.gridLayout.addLayout(self.horizontalLayout, 1, 0, 1, 1)


        self.retranslateUi(canvas_layer_container)

        QMetaObject.connectSlotsByName(canvas_layer_container)
    # setupUi

    def retranslateUi(self, canvas_layer_container):
        canvas_layer_container.setWindowTitle(QCoreApplication.translate("canvas_layer_container", u"Form", None))
#if QT_CONFIG(tooltip)
        self.add_layer.setToolTip(QCoreApplication.translate("canvas_layer_container", u"Add new layer", None))
#endif // QT_CONFIG(tooltip)
        self.add_layer.setText("")
#if QT_CONFIG(tooltip)
        self.move_layer_up.setToolTip(QCoreApplication.translate("canvas_layer_container", u"Move selected layer up", None))
#endif // QT_CONFIG(tooltip)
        self.move_layer_up.setText("")
#if QT_CONFIG(tooltip)
        self.move_layer_down.setToolTip(QCoreApplication.translate("canvas_layer_container", u"Move selected layer down", None))
#endif // QT_CONFIG(tooltip)
        self.move_layer_down.setText("")
#if QT_CONFIG(tooltip)
        self.merge_visible_layers.setToolTip(QCoreApplication.translate("canvas_layer_container", u"Merge visible", None))
#endif // QT_CONFIG(tooltip)
        self.merge_visible_layers.setText("")
#if QT_CONFIG(tooltip)
        self.delete_layer.setToolTip(QCoreApplication.translate("canvas_layer_container", u"Delete selected layer", None))
#endif // QT_CONFIG(tooltip)
        self.delete_layer.setText("")
    # retranslateUi

