# Form implementation generated from reading ui file '/home/joe/Projects/imagetopixel/airunner/src/airunner/../../src/airunner/pyqt/widgets/model_scheduler_widget.ui'
#
# Created by: PyQt6 UI code generator 6.4.2
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(315, 43)
        Form.setMinimumSize(QtCore.QSize(0, 43))
        Form.setMaximumSize(QtCore.QSize(16777215, 43))
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(parent=Form)
        font = QtGui.QFont()
        font.setPointSize(8)
        font.setBold(True)
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.model_dropdown = QtWidgets.QComboBox(parent=Form)
        font = QtGui.QFont()
        font.setPointSize(8)
        self.model_dropdown.setFont(font)
        self.model_dropdown.setObjectName("model_dropdown")
        self.verticalLayout.addWidget(self.model_dropdown)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.label_2 = QtWidgets.QLabel(parent=Form)
        font = QtGui.QFont()
        font.setPointSize(8)
        font.setBold(True)
        self.label_2.setFont(font)
        self.label_2.setObjectName("label_2")
        self.verticalLayout_2.addWidget(self.label_2)
        self.scheduler_dropdown = QtWidgets.QComboBox(parent=Form)
        font = QtGui.QFont()
        font.setPointSize(8)
        self.scheduler_dropdown.setFont(font)
        self.scheduler_dropdown.setObjectName("scheduler_dropdown")
        self.verticalLayout_2.addWidget(self.scheduler_dropdown)
        self.gridLayout.addLayout(self.verticalLayout_2, 0, 1, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.label.setText(_translate("Form", "Model"))
        self.label_2.setText(_translate("Form", "Scheduler"))