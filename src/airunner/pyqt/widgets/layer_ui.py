# Form implementation generated from reading ui file '/home/joe/Projects/imagetopixel/airunner/src/airunner/pyqt/widgets/layer.ui'
#
# Created by: PyQt6 UI code generator 6.4.2
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_LayerWidget(object):
    def setupUi(self, LayerWidget):
        LayerWidget.setObjectName("LayerWidget")
        LayerWidget.resize(220, 40)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(LayerWidget.sizePolicy().hasHeightForWidth())
        LayerWidget.setSizePolicy(sizePolicy)
        LayerWidget.setMinimumSize(QtCore.QSize(0, 38))
        LayerWidget.setMaximumSize(QtCore.QSize(220, 40))
        self.gridLayout_2 = QtWidgets.QGridLayout(LayerWidget)
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_2.setSpacing(0)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName("gridLayout")
        self.frame = QtWidgets.QFrame(parent=LayerWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.frame.sizePolicy().hasHeightForWidth())
        self.frame.setSizePolicy(sizePolicy)
        self.frame.setMinimumSize(QtCore.QSize(0, 38))
        self.frame.setStyleSheet("border-color: rgb(51, 209, 122);")
        self.frame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame.setObjectName("frame")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.frame)
        self.horizontalLayout_3.setContentsMargins(3, 3, 3, 3)
        self.horizontalLayout_3.setSpacing(3)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.thumbnail_label = QtWidgets.QLabel(parent=self.frame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.thumbnail_label.sizePolicy().hasHeightForWidth())
        self.thumbnail_label.setSizePolicy(sizePolicy)
        self.thumbnail_label.setMaximumSize(QtCore.QSize(32, 32))
        self.thumbnail_label.setText("")
        self.thumbnail_label.setObjectName("thumbnail_label")
        self.horizontalLayout_3.addWidget(self.thumbnail_label)
        self.layer_name = QtWidgets.QLabel(parent=self.frame)
        self.layer_name.setStyleSheet("border-color: rgba(0, 0, 0, 0);")
        self.layer_name.setObjectName("layer_name")
        self.horizontalLayout_3.addWidget(self.layer_name)
        self.gridLayout.addWidget(self.frame, 0, 1, 1, 1)
        self.visible_button = QtWidgets.QPushButton(parent=LayerWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.visible_button.sizePolicy().hasHeightForWidth())
        self.visible_button.setSizePolicy(sizePolicy)
        self.visible_button.setMinimumSize(QtCore.QSize(38, 38))
        self.visible_button.setMaximumSize(QtCore.QSize(38, 38))
        self.visible_button.setText("")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/icons/src/icons/eye-off.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        icon.addPixmap(QtGui.QPixmap("/home/joe/Projects/imagetopixel/airunner/src/airunner/pyqt/widgets/../src/icons/eye.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.On)
        icon.addPixmap(QtGui.QPixmap(":/icons/src/icons/eye.png"), QtGui.QIcon.Mode.Active, QtGui.QIcon.State.On)
        self.visible_button.setIcon(icon)
        self.visible_button.setCheckable(True)
        self.visible_button.setFlat(True)
        self.visible_button.setObjectName("visible_button")
        self.gridLayout.addWidget(self.visible_button, 0, 0, 1, 1)
        self.gridLayout_2.addLayout(self.gridLayout, 0, 0, 1, 1)

        self.retranslateUi(LayerWidget)
        QtCore.QMetaObject.connectSlotsByName(LayerWidget)

    def retranslateUi(self, LayerWidget):
        _translate = QtCore.QCoreApplication.translate
        LayerWidget.setWindowTitle(_translate("LayerWidget", "Form"))
        self.layer_name.setText(_translate("LayerWidget", "Layer 1"))
