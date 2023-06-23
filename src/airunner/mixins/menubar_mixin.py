from PyQt6.QtWidgets import QFileDialog
from airunner.windows.advanced_settings import AdvancedSettings
from airunner.windows.export_preferences import ExportPreferences
from airunner.filters.filter_box_blur import FilterBoxBlur
from airunner.filters.filter_color_balance import FilterColorBalance
from airunner.filters.filter_gaussian_blur import FilterGaussianBlur
from airunner.filters.filter_pixel_art import FilterPixelArt
from airunner.filters.filter_saturation import FilterSaturation
from airunner.filters.filter_unsharp_mask import FilterUnsharpMask
from airunner.filters.filter_rgb_noise import FilterRGBNoise
from airunner.windows.image_interpolation import ImageInterpolation
from airunner.windows.prompt_browser import PromptBrowser


class MenubarMixin:
    image_interpolation_window = None

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
        self.window.actionRotate_90_clockwise.triggered.connect(self.canvas.rotate_90_clockwise)
        self.window.actionRotate_90_counter_clockwise.triggered.connect(self.canvas.rotate_90_counterclockwise)
        self.initialize_filter_actions()
        self.window.actionResize_on_Paste.setChecked(self.settings_manager.settings.resize_on_paste.get() == True)
        self.window.actionImage_to_new_layer.setChecked(self.settings_manager.settings.image_to_new_layer.get() == True)
        self.window.actionAdvanced.triggered.connect(self.show_advanced)
        self.window.actionImage_export_settings.triggered.connect(self.show_export_preferences)
        self.window.actionCheck_for_latest_version_on_startup.setChecked(
            self.settings_manager.settings.latest_version_check.get() == True)
        self.window.actionCheck_for_latest_version_on_startup.triggered.connect(
            lambda: self.settings_manager.settings.latest_version_check.set(
                self.window.actionCheck_for_latest_version_on_startup.isChecked()
            )
        )
        self.window.actionSave_prompt.triggered.connect(self.save_prompt)
        self.window.actionPrompt_Browser.triggered.connect(self.show_prompt_browser)
        self.window.image_interpolation.triggered.connect(self.show_image_interpolation)

    def show_prompt_browser(self):
        PromptBrowser(settings_manager=self.prompts_manager, app=self)

    def save_prompt(self):
        saved_prompts = self.prompts_manager.settings.prompts.get()
        saved_prompts.append({
            'prompt': self.prompt,
            'negative_prompt': self.negative_prompt
        })
        self.prompts_manager.settings.prompts.set(saved_prompts)
        self.prompts_manager.save_settings()

    def initialize_filter_actions(self):
        self.filter_gaussian_blur = FilterGaussianBlur(parent=self)
        self.filter_pixel_art = FilterPixelArt(parent=self)
        self.filter_box_blur = FilterBoxBlur(parent=self)
        self.filter_unsharp_mask = FilterUnsharpMask(parent=self)
        self.filter_saturation = FilterSaturation(parent=self)
        self.filter_color_balance = FilterColorBalance(parent=self)
        self.filter_rgb_noise = FilterRGBNoise(parent=self)
        self.window.actionGaussian_Blur_2.triggered.connect(self.filter_gaussian_blur.show)
        self.window.actionPixel_Art.triggered.connect(self.filter_pixel_art.show)
        self.window.actionBox_Blur_2.triggered.connect(self.filter_box_blur.show)
        self.window.actionUnsharp_Mask.triggered.connect(self.filter_unsharp_mask.show)
        self.window.actionSaturation_Filter.triggered.connect(self.filter_saturation.show)
        self.window.actionColor_Balance.triggered.connect(self.filter_color_balance.show)
        self.window.actionRGB_Noise.triggered.connect(self.filter_rgb_noise.show)

    def import_image(self):
        file_path, _ = self.display_import_image_dialog()
        if file_path == "":
            return
        self.canvas.load_image(file_path)
        self.canvas.update()

    def export_image(self):
        file_path, _ = self.display_file_export_dialog()
        if file_path == "":
            return
        self.canvas.save_image(file_path)

    def display_file_export_dialog(self):
        return QFileDialog.getSaveFileName(
            self.window,
            "Export Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.gif)"
        )

    def display_import_image_dialog(self, label="Import Image"):
        return QFileDialog.getOpenFileName(
            self.window, label, "", "Image Files (*.png *.jpg *.jpeg)"
        )

    def paste_image(self):
        self.canvas.paste_image_from_clipboard()

    def copy_image(self):
        self.canvas.copy_image()

    def toggle_resize_on_paste(self):
        self.settings_manager.settings.resize_on_paste.set(self.window.actionResize_on_Paste.isChecked())

    def toggle_image_to_new_layer(self):
        self.settings_manager.settings.image_to_new_layer.set(self.window.actionImage_to_new_layer.isChecked())

    def show_advanced(self):
        AdvancedSettings(self.settings_manager)

    def show_export_preferences(self):
        ExportPreferences(self.settings_manager)

    def show_image_interpolation(self):
        self.image_interpolation_window = ImageInterpolation(self.settings_manager, app=self, exec=False)
        self.image_interpolation_window.show()
        self.image_interpolation_window = None
