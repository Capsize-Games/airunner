# Form implementation generated from reading ui file '/home/joe/Projects/imagetopixel/airunner/src/airunner/../../src/airunner/widgets/image/templates/image_panel_widget.ui'
#
# Created by: PyQt6 UI code generator 6.4.2
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_image_panel_widget(object):
    def setupUi(self, image_panel_widget):
        image_panel_widget.setObjectName("image_panel_widget")
        image_panel_widget.resize(558, 286)
        self.gridLayout = QtWidgets.QGridLayout(image_panel_widget)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.breadcrumbs = BreadcrumbContainerWidget(parent=image_panel_widget)
        self.breadcrumbs.setObjectName("breadcrumbs")
        self.gridLayout.addWidget(self.breadcrumbs, 0, 0, 1, 1)
        self.scrollArea = QtWidgets.QScrollArea(parent=image_panel_widget)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 556, 268))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.gridLayout.addWidget(self.scrollArea, 1, 0, 1, 1)

        self.retranslateUi(image_panel_widget)
        QtCore.QMetaObject.connectSlotsByName(image_panel_widget)

    def retranslateUi(self, image_panel_widget):
        _translate = QtCore.QCoreApplication.translate
        image_panel_widget.setWindowTitle(_translate("image_panel_widget", "Form"))
from airunner.widgets.breadcrumbs.breadcrumb_container_widget import BreadcrumbContainerWidget