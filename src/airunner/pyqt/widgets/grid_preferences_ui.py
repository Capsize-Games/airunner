# Form implementation generated from reading ui file '/home/joe/Projects/imagetopixel/airunner/src/airunner/pyqt/widgets/grid_preferences.ui'
#
# Created by: PyQt6 UI code generator 6.4.2
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(332, 323)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        self.gridLineColorButton = QtWidgets.QPushButton(parent=Form)
        self.gridLineColorButton.setObjectName("gridLineColorButton")
        self.gridLayout.addWidget(self.gridLineColorButton, 4, 0, 1, 1)
        self.snap_to_grid_checkbox = QtWidgets.QCheckBox(parent=Form)
        font = QtGui.QFont()
        font.setBold(False)
        self.snap_to_grid_checkbox.setFont(font)
        self.snap_to_grid_checkbox.setObjectName("snap_to_grid_checkbox")
        self.gridLayout.addWidget(self.snap_to_grid_checkbox, 7, 0, 1, 1)
        self.grid_line_width_spinbox = QtWidgets.QSpinBox(parent=Form)
        self.grid_line_width_spinbox.setObjectName("grid_line_width_spinbox")
        self.gridLayout.addWidget(self.grid_line_width_spinbox, 3, 0, 1, 1)
        self.show_grid_checkbox = QtWidgets.QCheckBox(parent=Form)
        font = QtGui.QFont()
        font.setBold(False)
        self.show_grid_checkbox.setFont(font)
        self.show_grid_checkbox.setObjectName("show_grid_checkbox")
        self.gridLayout.addWidget(self.show_grid_checkbox, 6, 0, 1, 1)
        self.grid_size_spinbox = QtWidgets.QSpinBox(parent=Form)
        self.grid_size_spinbox.setMaximum(512)
        self.grid_size_spinbox.setObjectName("grid_size_spinbox")
        self.gridLayout.addWidget(self.grid_size_spinbox, 1, 0, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(20, 72, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.gridLayout.addItem(spacerItem, 8, 0, 1, 1)
        self.label = QtWidgets.QLabel(parent=Form)
        font = QtGui.QFont()
        font.setBold(False)
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.label_2 = QtWidgets.QLabel(parent=Form)
        font = QtGui.QFont()
        font.setBold(False)
        self.label_2.setFont(font)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 2, 0, 1, 1)
        self.canvas_color = QtWidgets.QPushButton(parent=Form)
        self.canvas_color.setObjectName("canvas_color")
        self.gridLayout.addWidget(self.canvas_color, 5, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.gridLineColorButton.setText(_translate("Form", "Grid Line Color"))
        self.snap_to_grid_checkbox.setText(_translate("Form", "Snap to Grid"))
        self.show_grid_checkbox.setText(_translate("Form", "Show Grid"))
        self.label.setText(_translate("Form", "Grid Size"))
        self.label_2.setText(_translate("Form", "Grid Line Width"))
        self.canvas_color.setText(_translate("Form", "Canvas Color"))