# Form implementation generated from reading ui file '/home/joe/Projects/imagetopixel/airunner/src/airunner/../../src/airunner/widgets/prompt_builder/templates/prompt_builder.ui'
#
# Created by: PyQt6 UI code generator 6.4.2
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_prompt_builder(object):
    def setupUi(self, prompt_builder):
        prompt_builder.setObjectName("prompt_builder")
        prompt_builder.resize(300, 405)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(prompt_builder.sizePolicy().hasHeightForWidth())
        prompt_builder.setSizePolicy(sizePolicy)
        prompt_builder.setMinimumSize(QtCore.QSize(0, 405))
        font = QtGui.QFont()
        font.setPointSize(9)
        prompt_builder.setFont(font)
        self.gridLayout = QtWidgets.QGridLayout(prompt_builder)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.tabs = QtWidgets.QTabWidget(parent=prompt_builder)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tabs.sizePolicy().hasHeightForWidth())
        self.tabs.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(9)
        self.tabs.setFont(font)
        self.tabs.setStyleSheet("")
        self.tabs.setTabsClosable(False)
        self.tabs.setTabBarAutoHide(False)
        self.tabs.setObjectName("tabs")
        self.gridLayout.addWidget(self.tabs, 0, 0, 1, 1)

        self.retranslateUi(prompt_builder)
        self.tabs.setCurrentIndex(-1)
        QtCore.QMetaObject.connectSlotsByName(prompt_builder)

    def retranslateUi(self, prompt_builder):
        _translate = QtCore.QCoreApplication.translate
        prompt_builder.setWindowTitle(_translate("prompt_builder", "Form"))