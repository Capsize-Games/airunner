# Form implementation generated from reading ui file '/home/joe/Projects/imagetopixel/airunner/src/airunner/pyqt/windows/prompt_browser/prompt_browser_prompt_widget.ui'
#
# Created by: PyQt6 UI code generator 6.4.2
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(616, 257)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.load_button = QtWidgets.QPushButton(parent=Form)
        font = QtGui.QFont()
        font.setPointSize(9)
        self.load_button.setFont(font)
        self.load_button.setObjectName("load_button")
        self.horizontalLayout.addWidget(self.load_button)
        self.delete_button = QtWidgets.QPushButton(parent=Form)
        font = QtGui.QFont()
        font.setPointSize(9)
        self.delete_button.setFont(font)
        self.delete_button.setObjectName("delete_button")
        self.horizontalLayout.addWidget(self.delete_button)
        self.gridLayout.addLayout(self.horizontalLayout, 1, 0, 1, 2)
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(parent=Form)
        font = QtGui.QFont()
        font.setPointSize(9)
        font.setBold(True)
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.prompt = QtWidgets.QTextBrowser(parent=Form)
        font = QtGui.QFont()
        font.setPointSize(9)
        self.prompt.setFont(font)
        self.prompt.setReadOnly(False)
        self.prompt.setObjectName("prompt")
        self.verticalLayout.addWidget(self.prompt)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.label_3 = QtWidgets.QLabel(parent=Form)
        font = QtGui.QFont()
        font.setPointSize(9)
        font.setBold(True)
        self.label_3.setFont(font)
        self.label_3.setObjectName("label_3")
        self.verticalLayout_2.addWidget(self.label_3)
        self.negative_prompt = QtWidgets.QTextBrowser(parent=Form)
        font = QtGui.QFont()
        font.setPointSize(9)
        self.negative_prompt.setFont(font)
        self.negative_prompt.setReadOnly(False)
        self.negative_prompt.setObjectName("negative_prompt")
        self.verticalLayout_2.addWidget(self.negative_prompt)
        self.verticalLayout.addLayout(self.verticalLayout_2)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 2)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.load_button.setText(_translate("Form", "Load"))
        self.delete_button.setText(_translate("Form", "Delete"))
        self.label.setText(_translate("Form", "Prompt"))
        self.label_3.setText(_translate("Form", "Negative Prompt"))