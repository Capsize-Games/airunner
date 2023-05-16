from PyQt6.QtWidgets import QFileDialog

from airunner.filters.filter_box_blur import FilterBoxBlur
from airunner.filters.filter_color_balance import FilterColorBalance
from airunner.filters.filter_gaussian_blur import FilterGaussianBlur
from airunner.filters.filter_pixel_art import FilterPixelArt
from airunner.filters.filter_saturation import FilterSaturation
from airunner.filters.filter_unsharp_mask import FilterUnsharpMask


class MenubarMixin:
    def initialize(self):
        self.window.actionNew.triggered.connect(self.new_document)
        self.window.actionSave.triggered.connect(self.save_document)
        self.window.actionLoad.triggered.connect(self.load_document)
        self.window.actionImport.triggered.connect(self.import_image)
        self.window.actionExport.triggered.connect(self.export_image)
        self.window.actionQuit.triggered.connect(self.quit)
        self.window.actionPaste.triggered.connect(self.paste_image)
        self.window.actionCopy.triggered.connect(self.copy_image)
        self.window.actionResize_on_Paste.triggered.connect(self.toggle_resize_on_paste)
        self.window.actionImage_to_new_layer.triggered.connect(self.toggle_image_to_new_layer)
        self.window.actionReset_Settings.triggered.connect(self.reset_settings)
        self.initialize_filter_actions()
        self.window.actionResize_on_Paste.setChecked(self.settings_manager.settings.resize_on_paste.get() == True)
        self.window.actionImage_to_new_layer.setChecked(self.settings_manager.settings.image_to_new_layer.get() == True)

    def initialize_filter_actions(self):
        self.filter_gaussian_blur = FilterGaussianBlur(parent=self)
        self.window.actionGaussian_Blur.triggered.connect(self.filter_gaussian_blur.show)
        self.filter_pixel_art = FilterPixelArt(parent=self)
        self.window.actionPixel_Art.triggered.connect(self.filter_pixel_art.show)
        self.filter_box_blur = FilterBoxBlur(parent=self)
        self.window.actionBox_Blur.triggered.connect(self.filter_box_blur.show)
        self.filter_unsharp_mask = FilterUnsharpMask(parent=self)
        self.window.actionUnsharp_Mask.triggered.connect(self.filter_unsharp_mask.show)
        self.filter_saturation = FilterSaturation(parent=self)
        self.window.actionSaturation.triggered.connect(self.filter_saturation.show)
        self.filter_color_balance = FilterColorBalance(parent=self)
        self.window.actionColor_Balance.triggered.connect(self.filter_color_balance.show)

    def import_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self.window, "Import Image", "", "Image Files (*.png *.jpg *.jpeg)"
        )
        if file_path == "":
            return
        self.canvas.load_image(file_path)
        self.canvas.update()

    def export_image(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self.window,
            "Export Image",
            "",
            "Image Files (*.png *.jpg *.jpeg)"
        )
        if file_path == "":
            return
        self.canvas.save_image(file_path)

    def paste_image(self):
        self.canvas.paste_image_from_clipboard()

    def copy_image(self):
        self.canvas.copy_image()

    def toggle_resize_on_paste(self):
        self.settings_manager.settings.resize_on_paste.set(self.window.actionResize_on_Paste.isChecked())

    def toggle_image_to_new_layer(self):
        self.settings_manager.settings.image_to_new_layer.set(self.window.actionImage_to_new_layer.isChecked())
