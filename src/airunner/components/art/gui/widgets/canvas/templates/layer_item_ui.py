# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'layer_item.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QWidget)
import airunner.feather_rc

class Ui_layer_item(object):
    def setupUi(self, layer_item):
        if not layer_item.objectName():
            layer_item.setObjectName(u"layer_item")
        layer_item.resize(400, 132)
        layer_item.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.horizontalLayout = QHBoxLayout(layer_item)
        self.horizontalLayout.setSpacing(5)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(layer_item)
        self.label.setObjectName(u"label")

        self.horizontalLayout.addWidget(self.label)

        self.visibility = QPushButton(layer_item)
        self.visibility.setObjectName(u"visibility")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.visibility.sizePolicy().hasHeightForWidth())
        self.visibility.setSizePolicy(sizePolicy)
        self.visibility.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon = QIcon()
        icon.addFile(u":/dark/icons/feather/dark/eye.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.visibility.setIcon(icon)
        self.visibility.setCheckable(True)

        self.horizontalLayout.addWidget(self.visibility)

        self.delete_layer = QPushButton(layer_item)
        self.delete_layer.setObjectName(u"delete_layer")
        sizePolicy.setHeightForWidth(self.delete_layer.sizePolicy().hasHeightForWidth())
        self.delete_layer.setSizePolicy(sizePolicy)
        self.delete_layer.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon1 = QIcon()
        icon1.addFile(u":/dark/icons/feather/dark/trash-2.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.delete_layer.setIcon(icon1)

        self.horizontalLayout.addWidget(self.delete_layer)


        self.retranslateUi(layer_item)

        QMetaObject.connectSlotsByName(layer_item)
    # setupUi

    def retranslateUi(self, layer_item):
        layer_item.setWindowTitle(QCoreApplication.translate("layer_item", u"Form", None))
        self.label.setText(QCoreApplication.translate("layer_item", u"Layer N", None))
#if QT_CONFIG(tooltip)
        self.visibility.setToolTip(QCoreApplication.translate("layer_item", u"Toggle visibility", None))
#endif // QT_CONFIG(tooltip)
        self.visibility.setText("")
#if QT_CONFIG(tooltip)
        self.delete_layer.setToolTip(QCoreApplication.translate("layer_item", u"Delete layer", None))
#endif // QT_CONFIG(tooltip)
        self.delete_layer.setText("")
    # retranslateUi

