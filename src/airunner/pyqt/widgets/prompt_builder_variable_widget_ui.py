# Form implementation generated from reading ui file '/home/joe/Projects/imagetopixel/airunner/src/airunner/pyqt/widgets/prompt_builder_variable_widget.ui'
#
# Created by: PyQt6 UI code generator 6.4.2
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(200, 57)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Form.sizePolicy().hasHeightForWidth())
        Form.setSizePolicy(sizePolicy)
        Form.setMinimumSize(QtCore.QSize(200, 57))
        Form.setMaximumSize(QtCore.QSize(16777215, 57))
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.groupbox = QtWidgets.QGroupBox(parent=Form)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupbox.sizePolicy().hasHeightForWidth())
        self.groupbox.setSizePolicy(sizePolicy)
        self.groupbox.setMinimumSize(QtCore.QSize(200, 57))
        self.groupbox.setMaximumSize(QtCore.QSize(16777215, 57))
        font = QtGui.QFont()
        font.setPointSize(8)
        font.setBold(True)
        self.groupbox.setFont(font)
        self.groupbox.setFlat(False)
        self.groupbox.setCheckable(False)
        self.groupbox.setObjectName("groupbox")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.groupbox)
        self.horizontalLayout.setContentsMargins(6, 3, 6, 9)
        self.horizontalLayout.setSpacing(3)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.combobox = QtWidgets.QComboBox(parent=self.groupbox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.combobox.sizePolicy().hasHeightForWidth())
        self.combobox.setSizePolicy(sizePolicy)
        self.combobox.setMinimumSize(QtCore.QSize(0, 18))
        self.combobox.setMaximumSize(QtCore.QSize(250, 18))
        font = QtGui.QFont()
        font.setPointSize(9)
        font.setBold(False)
        self.combobox.setFont(font)
        self.combobox.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combobox.setMinimumContentsLength(10)
        self.combobox.setObjectName("combobox")
        self.horizontalLayout.addWidget(self.combobox)
        self.slider = QtWidgets.QSlider(parent=self.groupbox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.slider.sizePolicy().hasHeightForWidth())
        self.slider.setSizePolicy(sizePolicy)
        self.slider.setMinimumSize(QtCore.QSize(50, 0))
        self.slider.setMaximumSize(QtCore.QSize(16777215, 16777215))
        font = QtGui.QFont()
        font.setPointSize(9)
        font.setBold(True)
        self.slider.setFont(font)
        self.slider.setMaximum(200)
        self.slider.setProperty("value", 100)
        self.slider.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.slider.setObjectName("slider")
        self.horizontalLayout.addWidget(self.slider)
        self.spinbox = QtWidgets.QDoubleSpinBox(parent=self.groupbox)
        font = QtGui.QFont()
        font.setPointSize(9)
        font.setBold(False)
        self.spinbox.setFont(font)
        self.spinbox.setMaximum(2.0)
        self.spinbox.setSingleStep(0.01)
        self.spinbox.setProperty("value", 1.0)
        self.spinbox.setObjectName("spinbox")
        self.horizontalLayout.addWidget(self.spinbox)
        self.gridLayout.addWidget(self.groupbox, 0, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.groupbox.setTitle(_translate("Form", "Name"))
        self.slider.setToolTip(_translate("Form", "Weight"))
        self.spinbox.setToolTip(_translate("Form", "Weight"))
