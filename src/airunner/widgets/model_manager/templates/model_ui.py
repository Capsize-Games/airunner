# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'model.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QGridLayout, QHBoxLayout,
    QHeaderView, QPushButton, QSizePolicy, QSpacerItem,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
import airunner.resources_light_rc
import airunner.resources_dark_rc

class Ui_model_widget(object):
    def setupUi(self, model_widget):
        if not model_widget.objectName():
            model_widget.setObjectName(u"model_widget")
        model_widget.resize(395, 295)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(model_widget.sizePolicy().hasHeightForWidth())
        model_widget.setSizePolicy(sizePolicy)
        model_widget.setMinimumSize(QSize(0, 0))
        self.gridLayout = QGridLayout(model_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.name = QCheckBox(model_widget)
        self.name.setObjectName(u"name")
        font = QFont()
        font.setPointSize(8)
        font.setBold(True)
        self.name.setFont(font)

        self.horizontalLayout_2.addWidget(self.name)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.toolButton = QPushButton(model_widget)
        self.toolButton.setObjectName(u"toolButton")
        self.toolButton.setMinimumSize(QSize(24, 24))
        self.toolButton.setMaximumSize(QSize(24, 24))
        self.toolButton.setCursor(QCursor(Qt.PointingHandCursor))
        icon = QIcon()
        icon.addFile(u":/icons/light/eye-look-icon.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.toolButton.setIcon(icon)
        self.toolButton.setCheckable(True)
        self.toolButton.setChecked(False)

        self.horizontalLayout.addWidget(self.toolButton)

        self.delete_button = QPushButton(model_widget)
        self.delete_button.setObjectName(u"delete_button")
        self.delete_button.setMinimumSize(QSize(24, 24))
        self.delete_button.setMaximumSize(QSize(24, 24))
        self.delete_button.setCursor(QCursor(Qt.PointingHandCursor))
        icon1 = QIcon()
        icon1.addFile(u":/icons/light/recycle-bin-line-icon.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.delete_button.setIcon(icon1)

        self.horizontalLayout.addWidget(self.delete_button)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)


        self.verticalLayout.addLayout(self.horizontalLayout)


        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)

        self.details = QTableWidget(model_widget)
        if (self.details.columnCount() < 2):
            self.details.setColumnCount(2)
        if (self.details.rowCount() < 7):
            self.details.setRowCount(7)
        __qtablewidgetitem = QTableWidgetItem()
        self.details.setItem(0, 0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.details.setItem(0, 1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.details.setItem(1, 0, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.details.setItem(1, 1, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.details.setItem(2, 0, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.details.setItem(2, 1, __qtablewidgetitem5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.details.setItem(3, 0, __qtablewidgetitem6)
        __qtablewidgetitem7 = QTableWidgetItem()
        self.details.setItem(3, 1, __qtablewidgetitem7)
        __qtablewidgetitem8 = QTableWidgetItem()
        self.details.setItem(4, 0, __qtablewidgetitem8)
        __qtablewidgetitem9 = QTableWidgetItem()
        self.details.setItem(4, 1, __qtablewidgetitem9)
        __qtablewidgetitem10 = QTableWidgetItem()
        self.details.setItem(5, 0, __qtablewidgetitem10)
        __qtablewidgetitem11 = QTableWidgetItem()
        self.details.setItem(5, 1, __qtablewidgetitem11)
        __qtablewidgetitem12 = QTableWidgetItem()
        self.details.setItem(6, 0, __qtablewidgetitem12)
        __qtablewidgetitem13 = QTableWidgetItem()
        self.details.setItem(6, 1, __qtablewidgetitem13)
        self.details.setObjectName(u"details")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.details.sizePolicy().hasHeightForWidth())
        self.details.setSizePolicy(sizePolicy1)
        self.details.setMinimumSize(QSize(0, 214))
        self.details.setRowCount(7)
        self.details.setColumnCount(2)
        self.details.horizontalHeader().setVisible(False)
        self.details.horizontalHeader().setStretchLastSection(True)
        self.details.verticalHeader().setVisible(False)
        self.details.verticalHeader().setStretchLastSection(False)

        self.gridLayout.addWidget(self.details, 1, 0, 1, 1)


        self.retranslateUi(model_widget)
        self.toolButton.toggled.connect(model_widget.action_toggled_button_details)
        self.delete_button.clicked.connect(model_widget.action_clicked_button_delete)
        self.details.cellChanged.connect(model_widget.action_cell_changed)

        QMetaObject.connectSlotsByName(model_widget)
    # setupUi

    def retranslateUi(self, model_widget):
        model_widget.setWindowTitle(QCoreApplication.translate("model_widget", u"Form", None))
        model_widget.setProperty("branch", "")
        model_widget.setProperty("path", "")
        model_widget.setProperty("version", "")
        model_widget.setProperty("category", "")
        model_widget.setProperty("pipeline_action", "")
        model_widget.setProperty("pipeline_class", "")
        model_widget.setProperty("prompts", "")
        self.name.setText(QCoreApplication.translate("model_widget", u"UPC", None))
#if QT_CONFIG(tooltip)
        self.toolButton.setToolTip(QCoreApplication.translate("model_widget", u"View details", None))
#endif // QT_CONFIG(tooltip)
        self.toolButton.setText("")
#if QT_CONFIG(tooltip)
        self.delete_button.setToolTip(QCoreApplication.translate("model_widget", u"Delete model", None))
#endif // QT_CONFIG(tooltip)
        self.delete_button.setText("")

        __sortingEnabled = self.details.isSortingEnabled()
        self.details.setSortingEnabled(False)
        ___qtablewidgetitem = self.details.item(0, 0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("model_widget", u"path", None));
        ___qtablewidgetitem1 = self.details.item(0, 1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("model_widget", u"~/.local/share/airunner/models/model_type", None));
        ___qtablewidgetitem2 = self.details.item(1, 0)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("model_widget", u"branch", None));
        ___qtablewidgetitem3 = self.details.item(1, 1)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("model_widget", u"main", None));
        ___qtablewidgetitem4 = self.details.item(2, 0)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("model_widget", u"version", None));
        ___qtablewidgetitem5 = self.details.item(2, 1)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("model_widget", u"v1", None));
        ___qtablewidgetitem6 = self.details.item(3, 0)
        ___qtablewidgetitem6.setText(QCoreApplication.translate("model_widget", u"category", None));
        ___qtablewidgetitem7 = self.details.item(3, 1)
        ___qtablewidgetitem7.setText(QCoreApplication.translate("model_widget", u"stablediffusion", None));
        ___qtablewidgetitem8 = self.details.item(4, 0)
        ___qtablewidgetitem8.setText(QCoreApplication.translate("model_widget", u"pipeline action", None));
        ___qtablewidgetitem9 = self.details.item(4, 1)
        ___qtablewidgetitem9.setText(QCoreApplication.translate("model_widget", u"txt2img", None));
        ___qtablewidgetitem10 = self.details.item(5, 0)
        ___qtablewidgetitem10.setText(QCoreApplication.translate("model_widget", u"pipeline class", None));
        ___qtablewidgetitem11 = self.details.item(5, 1)
        ___qtablewidgetitem11.setText(QCoreApplication.translate("model_widget", u"diffusers.StableDiffusion", None));
        ___qtablewidgetitem12 = self.details.item(6, 0)
        ___qtablewidgetitem12.setText(QCoreApplication.translate("model_widget", u"prompts", None));
        ___qtablewidgetitem13 = self.details.item(6, 1)
        ___qtablewidgetitem13.setText(QCoreApplication.translate("model_widget", u"prompt", None));
        self.details.setSortingEnabled(__sortingEnabled)

    # retranslateUi

