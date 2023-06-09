# Form implementation generated from reading ui file '/home/joe/Projects/imagetopixel/airunner/src/airunner/pyqt/main_window_new.ui'
#
# Created by: PyQt6 UI code generator 6.4.2
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1150, 990)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        MainWindow.setMinimumSize(QtCore.QSize(0, 0))
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        self.centralwidget.setMinimumSize(QtCore.QSize(1000, 512))
        self.centralwidget.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName("gridLayout")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1150, 22))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(parent=self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.menuEdit = QtWidgets.QMenu(parent=self.menubar)
        self.menuEdit.setObjectName("menuEdit")
        self.menuFilters = QtWidgets.QMenu(parent=self.menubar)
        self.menuFilters.setObjectName("menuFilters")
        self.menuBlur = QtWidgets.QMenu(parent=self.menuFilters)
        self.menuBlur.setObjectName("menuBlur")
        self.menuAbout = QtWidgets.QMenu(parent=self.menubar)
        self.menuAbout.setTearOffEnabled(False)
        self.menuAbout.setObjectName("menuAbout")
        self.menuModel_merge = QtWidgets.QMenu(parent=self.menubar)
        self.menuModel_merge.setObjectName("menuModel_merge")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(parent=MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionNew = QtGui.QAction(parent=MainWindow)
        self.actionNew.setObjectName("actionNew")
        self.actionImport = QtGui.QAction(parent=MainWindow)
        self.actionImport.setObjectName("actionImport")
        self.actionExport = QtGui.QAction(parent=MainWindow)
        self.actionExport.setObjectName("actionExport")
        self.actionCopy = QtGui.QAction(parent=MainWindow)
        self.actionCopy.setObjectName("actionCopy")
        self.actionPaste = QtGui.QAction(parent=MainWindow)
        self.actionPaste.setObjectName("actionPaste")
        self.actionUndo = QtGui.QAction(parent=MainWindow)
        self.actionUndo.setObjectName("actionUndo")
        self.actionRedo = QtGui.QAction(parent=MainWindow)
        self.actionRedo.setObjectName("actionRedo")
        self.actionGrid = QtGui.QAction(parent=MainWindow)
        self.actionGrid.setObjectName("actionGrid")
        self.actionPreferences = QtGui.QAction(parent=MainWindow)
        self.actionPreferences.setObjectName("actionPreferences")
        self.actionCanvas_color = QtGui.QAction(parent=MainWindow)
        self.actionCanvas_color.setObjectName("actionCanvas_color")
        self.actionReset_Settings = QtGui.QAction(parent=MainWindow)
        self.actionReset_Settings.setObjectName("actionReset_Settings")
        self.actionResize_on_Paste = QtGui.QAction(parent=MainWindow)
        self.actionResize_on_Paste.setCheckable(True)
        self.actionResize_on_Paste.setObjectName("actionResize_on_Paste")
        self.actionMemory = QtGui.QAction(parent=MainWindow)
        self.actionMemory.setObjectName("actionMemory")
        self.actionAbout = QtGui.QAction(parent=MainWindow)
        self.actionAbout.setObjectName("actionAbout")
        self.actionCheck_for_updates = QtGui.QAction(parent=MainWindow)
        self.actionCheck_for_updates.setObjectName("actionCheck_for_updates")
        self.actionOpen = QtGui.QAction(parent=MainWindow)
        self.actionOpen.setObjectName("actionOpen")
        self.actionView = QtGui.QAction(parent=MainWindow)
        self.actionView.setObjectName("actionView")
        self.actionAdvanced = QtGui.QAction(parent=MainWindow)
        self.actionAdvanced.setObjectName("actionAdvanced")
        self.actionGaussian_Blur = QtGui.QAction(parent=MainWindow)
        self.actionGaussian_Blur.setEnabled(True)
        self.actionGaussian_Blur.setObjectName("actionGaussian_Blur")
        self.actionBox_Blur = QtGui.QAction(parent=MainWindow)
        self.actionBox_Blur.setObjectName("actionBox_Blur")
        self.actionUnsharp_Mask = QtGui.QAction(parent=MainWindow)
        self.actionUnsharp_Mask.setObjectName("actionUnsharp_Mask")
        self.actionPixel_Art = QtGui.QAction(parent=MainWindow)
        self.actionPixel_Art.setVisible(True)
        self.actionPixel_Art.setObjectName("actionPixel_Art")
        self.actionInvert = QtGui.QAction(parent=MainWindow)
        self.actionInvert.setObjectName("actionInvert")
        self.actionSaturation = QtGui.QAction(parent=MainWindow)
        self.actionSaturation.setVisible(True)
        self.actionSaturation.setObjectName("actionSaturation")
        self.actionColor_Balance = QtGui.QAction(parent=MainWindow)
        self.actionColor_Balance.setEnabled(True)
        self.actionColor_Balance.setVisible(True)
        self.actionColor_Balance.setObjectName("actionColor_Balance")
        self.actionSave = QtGui.QAction(parent=MainWindow)
        self.actionSave.setObjectName("actionSave")
        self.actionLoad = QtGui.QAction(parent=MainWindow)
        self.actionLoad.setObjectName("actionLoad")
        self.actionQuit = QtGui.QAction(parent=MainWindow)
        self.actionQuit.setObjectName("actionQuit")
        self.actionPixel_Art_2 = QtGui.QAction(parent=MainWindow)
        self.actionPixel_Art_2.setObjectName("actionPixel_Art_2")
        self.actionBug_report = QtGui.QAction(parent=MainWindow)
        self.actionBug_report.setObjectName("actionBug_report")
        self.actionReport_vulnerability = QtGui.QAction(parent=MainWindow)
        self.actionReport_vulnerability.setObjectName("actionReport_vulnerability")
        self.actionDiscord = QtGui.QAction(parent=MainWindow)
        self.actionDiscord.setObjectName("actionDiscord")
        self.actionExtensions = QtGui.QAction(parent=MainWindow)
        self.actionExtensions.setObjectName("actionExtensions")
        self.actionShow_image_preview = QtGui.QAction(parent=MainWindow)
        self.actionShow_image_preview.setCheckable(True)
        self.actionShow_image_preview.setObjectName("actionShow_image_preview")
        self.actionImage_to_new_layer = QtGui.QAction(parent=MainWindow)
        self.actionImage_to_new_layer.setCheckable(True)
        self.actionImage_to_new_layer.setObjectName("actionImage_to_new_layer")
        self.actionAuto_export_images = QtGui.QAction(parent=MainWindow)
        self.actionAuto_export_images.setCheckable(True)
        self.actionAuto_export_images.setObjectName("actionAuto_export_images")
        self.actionImage_export_settings = QtGui.QAction(parent=MainWindow)
        self.actionImage_export_settings.setObjectName("actionImage_export_settings")
        self.actionCheck_for_latest_version_on_startup = QtGui.QAction(parent=MainWindow)
        self.actionCheck_for_latest_version_on_startup.setCheckable(True)
        self.actionCheck_for_latest_version_on_startup.setObjectName("actionCheck_for_latest_version_on_startup")
        self.actionModel_Merger = QtGui.QAction(parent=MainWindow)
        self.actionModel_Merger.setObjectName("actionModel_Merger")
        self.actionSaturation_Filter = QtGui.QAction(parent=MainWindow)
        self.actionSaturation_Filter.setObjectName("actionSaturation_Filter")
        self.actionColor_Balance_2 = QtGui.QAction(parent=MainWindow)
        self.actionColor_Balance_2.setObjectName("actionColor_Balance_2")
        self.actionRGB_Noise = QtGui.QAction(parent=MainWindow)
        self.actionRGB_Noise.setObjectName("actionRGB_Noise")
        self.actionGaussian_Blur_2 = QtGui.QAction(parent=MainWindow)
        self.actionGaussian_Blur_2.setObjectName("actionGaussian_Blur_2")
        self.actionBox_Blur_2 = QtGui.QAction(parent=MainWindow)
        self.actionBox_Blur_2.setObjectName("actionBox_Blur_2")
        self.actionRotate_90_clockwise = QtGui.QAction(parent=MainWindow)
        self.actionRotate_90_clockwise.setObjectName("actionRotate_90_clockwise")
        self.actionRotate_90_counter_clockwise = QtGui.QAction(parent=MainWindow)
        self.actionRotate_90_counter_clockwise.setObjectName("actionRotate_90_counter_clockwise")
        self.actionSave_prompt = QtGui.QAction(parent=MainWindow)
        self.actionSave_prompt.setObjectName("actionSave_prompt")
        self.actionPrompt_Browser = QtGui.QAction(parent=MainWindow)
        self.actionPrompt_Browser.setObjectName("actionPrompt_Browser")
        self.actionShow_Active_Image_Area = QtGui.QAction(parent=MainWindow)
        self.actionShow_Active_Image_Area.setCheckable(True)
        self.actionShow_Active_Image_Area.setObjectName("actionShow_Active_Image_Area")
        self.actionImage_Interpolation = QtGui.QAction(parent=MainWindow)
        self.actionImage_Interpolation.setObjectName("actionImage_Interpolation")
        self.image_interpolation = QtGui.QAction(parent=MainWindow)
        self.image_interpolation.setObjectName("image_interpolation")
        self.actionFilm = QtGui.QAction(parent=MainWindow)
        self.actionFilm.setObjectName("actionFilm")
        self.actionDeterministic_generation = QtGui.QAction(parent=MainWindow)
        self.actionDeterministic_generation.setObjectName("actionDeterministic_generation")
        self.actionDark_mode = QtGui.QAction(parent=MainWindow)
        self.actionDark_mode.setCheckable(True)
        self.actionDark_mode.setObjectName("actionDark_mode")
        self.actionConsole_window = QtGui.QAction(parent=MainWindow)
        self.actionConsole_window.setObjectName("actionConsole_window")
        self.actionSettings = QtGui.QAction(parent=MainWindow)
        self.actionSettings.setObjectName("actionSettings")
        self.actionEasy_prompt = QtGui.QAction(parent=MainWindow)
        self.actionEasy_prompt.setObjectName("actionEasy_prompt")
        self.menuFile.addAction(self.actionNew)
        self.menuFile.addAction(self.actionLoad)
        self.menuFile.addAction(self.actionSave)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionSettings)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionExport)
        self.menuFile.addAction(self.actionImport)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionSave_prompt)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionQuit)
        self.menuEdit.addAction(self.actionCopy)
        self.menuEdit.addAction(self.actionPaste)
        self.menuEdit.addAction(self.actionUndo)
        self.menuEdit.addAction(self.actionRedo)
        self.menuEdit.addSeparator()
        self.menuEdit.addAction(self.actionRotate_90_clockwise)
        self.menuEdit.addAction(self.actionRotate_90_counter_clockwise)
        self.menuBlur.addSeparator()
        self.menuBlur.addAction(self.actionGaussian_Blur_2)
        self.menuBlur.addAction(self.actionBox_Blur_2)
        self.menuFilters.addAction(self.menuBlur.menuAction())
        self.menuFilters.addSeparator()
        self.menuFilters.addAction(self.actionColor_Balance)
        self.menuFilters.addAction(self.actionSaturation_Filter)
        self.menuFilters.addAction(self.actionUnsharp_Mask)
        self.menuFilters.addAction(self.actionRGB_Noise)
        self.menuFilters.addAction(self.actionPixel_Art)
        self.menuFilters.addSeparator()
        self.menuFilters.addAction(self.actionInvert)
        self.menuFilters.addAction(self.actionFilm)
        self.menuAbout.addAction(self.actionAbout)
        self.menuAbout.addAction(self.actionBug_report)
        self.menuAbout.addAction(self.actionReport_vulnerability)
        self.menuAbout.addAction(self.actionDiscord)
        self.menuModel_merge.addAction(self.image_interpolation)
        self.menuModel_merge.addSeparator()
        self.menuModel_merge.addAction(self.actionDeterministic_generation)
        self.menuModel_merge.addSeparator()
        self.menuModel_merge.addAction(self.actionModel_Merger)
        self.menuModel_merge.addSeparator()
        self.menuModel_merge.addAction(self.actionPrompt_Browser)
        self.menuModel_merge.addSeparator()
        self.menuModel_merge.addAction(self.actionEasy_prompt)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuEdit.menuAction())
        self.menubar.addAction(self.menuModel_merge.menuAction())
        self.menubar.addAction(self.menuFilters.menuAction())
        self.menubar.addAction(self.menuAbout.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "AI Runner"))
        self.menuFile.setTitle(_translate("MainWindow", "File"))
        self.menuEdit.setTitle(_translate("MainWindow", "Edit"))
        self.menuFilters.setTitle(_translate("MainWindow", "Filters"))
        self.menuBlur.setTitle(_translate("MainWindow", "Blur"))
        self.menuAbout.setTitle(_translate("MainWindow", "Help"))
        self.menuModel_merge.setTitle(_translate("MainWindow", "Tools"))
        self.actionNew.setText(_translate("MainWindow", "New"))
        self.actionNew.setShortcut(_translate("MainWindow", "Ctrl+N"))
        self.actionImport.setText(_translate("MainWindow", "Import image"))
        self.actionImport.setShortcut(_translate("MainWindow", "Ctrl+I"))
        self.actionExport.setText(_translate("MainWindow", "Export image"))
        self.actionExport.setShortcut(_translate("MainWindow", "Ctrl+E"))
        self.actionCopy.setText(_translate("MainWindow", "Copy"))
        self.actionCopy.setShortcut(_translate("MainWindow", "Ctrl+C"))
        self.actionPaste.setText(_translate("MainWindow", "Paste"))
        self.actionPaste.setShortcut(_translate("MainWindow", "Ctrl+V"))
        self.actionUndo.setText(_translate("MainWindow", "Undo"))
        self.actionUndo.setShortcut(_translate("MainWindow", "Ctrl+Z"))
        self.actionRedo.setText(_translate("MainWindow", "Redo"))
        self.actionRedo.setShortcut(_translate("MainWindow", "Ctrl+Y"))
        self.actionGrid.setText(_translate("MainWindow", "Grid"))
        self.actionGrid.setToolTip(_translate("MainWindow", "Grid settings"))
        self.actionPreferences.setText(_translate("MainWindow", "Path Preferences"))
        self.actionPreferences.setToolTip(_translate("MainWindow", "Modify model path and more"))
        self.actionCanvas_color.setText(_translate("MainWindow", "Canvas color"))
        self.actionCanvas_color.setToolTip(_translate("MainWindow", "Change the color of the canvas"))
        self.actionReset_Settings.setText(_translate("MainWindow", "Reset Settings to Default"))
        self.actionReset_Settings.setToolTip(_translate("MainWindow", "Reset all settings to default"))
        self.actionResize_on_Paste.setText(_translate("MainWindow", "Resize on Import"))
        self.actionResize_on_Paste.setToolTip(_translate("MainWindow", "Resize the image to active grid area when importing"))
        self.actionMemory.setText(_translate("MainWindow", "Memory"))
        self.actionAbout.setText(_translate("MainWindow", "About"))
        self.actionCheck_for_updates.setText(_translate("MainWindow", "Check for updates"))
        self.actionOpen.setText(_translate("MainWindow", "Open"))
        self.actionView.setText(_translate("MainWindow", "View"))
        self.actionAdvanced.setText(_translate("MainWindow", "Memory Preferences"))
        self.actionAdvanced.setToolTip(_translate("MainWindow", "Change memory settings"))
        self.actionGaussian_Blur.setText(_translate("MainWindow", "Gaussian Blur"))
        self.actionBox_Blur.setText(_translate("MainWindow", "Box Blur"))
        self.actionUnsharp_Mask.setText(_translate("MainWindow", "Unsharp Mask"))
        self.actionPixel_Art.setText(_translate("MainWindow", "Pixel Art"))
        self.actionInvert.setText(_translate("MainWindow", "Invert"))
        self.actionSaturation.setText(_translate("MainWindow", "Saturation"))
        self.actionColor_Balance.setText(_translate("MainWindow", "Color Balance"))
        self.actionSave.setText(_translate("MainWindow", "Save"))
        self.actionSave.setShortcut(_translate("MainWindow", "Ctrl+S"))
        self.actionLoad.setText(_translate("MainWindow", "Open"))
        self.actionLoad.setShortcut(_translate("MainWindow", "Ctrl+O"))
        self.actionQuit.setText(_translate("MainWindow", "Quit"))
        self.actionQuit.setShortcut(_translate("MainWindow", "Ctrl+Q"))
        self.actionPixel_Art_2.setText(_translate("MainWindow", "Pixel Art"))
        self.actionBug_report.setText(_translate("MainWindow", "Bug report"))
        self.actionReport_vulnerability.setText(_translate("MainWindow", "Report vulnerability"))
        self.actionDiscord.setText(_translate("MainWindow", "Discord"))
        self.actionExtensions.setText(_translate("MainWindow", "Extensions"))
        self.actionExtensions.setToolTip(_translate("MainWindow", "Install, update and delete extensions"))
        self.actionShow_image_preview.setText(_translate("MainWindow", "Show image preview"))
        self.actionImage_to_new_layer.setText(_translate("MainWindow", "Image to new layer"))
        self.actionImage_to_new_layer.setToolTip(_translate("MainWindow", "Send generated images to new layer"))
        self.actionAuto_export_images.setText(_translate("MainWindow", "Auto export images"))
        self.actionAuto_export_images.setToolTip(_translate("MainWindow", "Automatically export newly generated images to a folder"))
        self.actionImage_export_settings.setText(_translate("MainWindow", "Import / export preferences"))
        self.actionCheck_for_latest_version_on_startup.setText(_translate("MainWindow", "Check for latest version on startup"))
        self.actionModel_Merger.setText(_translate("MainWindow", "Model Merger"))
        self.actionSaturation_Filter.setText(_translate("MainWindow", "Saturation"))
        self.actionColor_Balance_2.setText(_translate("MainWindow", "Color Balance"))
        self.actionRGB_Noise.setText(_translate("MainWindow", "RGB Noise"))
        self.actionGaussian_Blur_2.setText(_translate("MainWindow", "Gaussian Blur"))
        self.actionBox_Blur_2.setText(_translate("MainWindow", "Box Blur"))
        self.actionRotate_90_clockwise.setText(_translate("MainWindow", "Rotate 90° clockwise"))
        self.actionRotate_90_clockwise.setShortcut(_translate("MainWindow", "Ctrl+R"))
        self.actionRotate_90_counter_clockwise.setText(_translate("MainWindow", "Rotate 90° counter clockwise"))
        self.actionRotate_90_counter_clockwise.setShortcut(_translate("MainWindow", "Ctrl+Shift+R"))
        self.actionSave_prompt.setText(_translate("MainWindow", "Save prompt"))
        self.actionPrompt_Browser.setText(_translate("MainWindow", "Prompt Browser"))
        self.actionShow_Active_Image_Area.setText(_translate("MainWindow", "Show Active Image Area"))
        self.actionImage_Interpolation.setText(_translate("MainWindow", "Image Interpolation"))
        self.image_interpolation.setText(_translate("MainWindow", "Image Interpolation"))
        self.actionFilm.setText(_translate("MainWindow", "Film"))
        self.actionDeterministic_generation.setText(_translate("MainWindow", "Deterministic generator"))
        self.actionDark_mode.setText(_translate("MainWindow", "Dark mode"))
        self.actionConsole_window.setText(_translate("MainWindow", "Console window"))
        self.actionSettings.setText(_translate("MainWindow", "Settings"))
        self.actionEasy_prompt.setText(_translate("MainWindow", "Easy prompt"))
