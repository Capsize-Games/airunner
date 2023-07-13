from PyQt6.QtWidgets import QFileDialog
from airunner.windows.deterministic_generation_window import DeterministicGenerationWindow
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
    deterministic_window = None

    def initialize(self):
        self.actionNew.triggered.connect(self.new_document)
        self.actionSave.triggered.connect(self.save_document)
        self.actionLoad.triggered.connect(self.load_document)
        self.actionImport.triggered.connect(self.import_image)
        self.actionExport.triggered.connect(self.export_image)
        self.actionQuit.triggered.connect(self.quit)
        self.actionPaste.triggered.connect(self.paste_image)
        self.actionCopy.triggered.connect(self.copy_image)
        self.actionRotate_90_clockwise.triggered.connect(self.canvas.rotate_90_clockwise)
        self.actionRotate_90_counter_clockwise.triggered.connect(self.canvas.rotate_90_counterclockwise)
        self.initialize_filter_actions()
        self.actionSave_prompt.triggered.connect(self.save_prompt)
        self.actionPrompt_Browser.triggered.connect(self.show_prompt_browser)
        self.image_interpolation.triggered.connect(self.show_image_interpolation)
        self.actionClear_all_prompts.triggered.connect(self.clear_all_prompts)

    def clear_all_prompts(self):
        for tab_section in self._tabs.keys():
            self.override_tab_section = tab_section
            for tab in self.tabs.keys():
                self.override_section = tab
                self.prompt = ""
                self.negative_prompt = ""
                self.generator_tab_widget.clear_prompts(tab_section, tab)
        self.override_tab_section = None
        self.override_section = None

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
        self.actionGaussian_Blur_2.triggered.connect(self.filter_gaussian_blur.show)
        self.actionPixel_Art.triggered.connect(self.filter_pixel_art.show)
        self.actionBox_Blur_2.triggered.connect(self.filter_box_blur.show)
        self.actionUnsharp_Mask.triggered.connect(self.filter_unsharp_mask.show)
        self.actionSaturation_Filter.triggered.connect(self.filter_saturation.show)
        self.actionColor_Balance.triggered.connect(self.filter_color_balance.show)
        self.actionRGB_Noise.triggered.connect(self.filter_rgb_noise.show)

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

    def show_image_interpolation(self):
        self.image_interpolation_window = ImageInterpolation(self.settings_manager, app=self, exec=False)
        self.image_interpolation_window.show()
        self.image_interpolation_window = None

    def show_deterministic_generation(self):
        if not self.deterministic_window:
            self.deterministic_window = DeterministicGenerationWindow(self.settings_manager, app=self, exec=False, images=self.deterministic_images, data=self.data)
            self.deterministic_window.show()
            self.deterministic_window = None
        else:
            self.deterministic_window.update_images(self.deterministic_images)

    def close_deterministic_generation_window(self):
        self.deterministic_window = None
        self.deterministic_data = None
        self.deterministic_images = None