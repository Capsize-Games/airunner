import os
from functools import partial

from PyQt6.QtWidgets import QFileDialog

from airunner.filters.windows.filter_base import FilterBase
from airunner.utils import auto_export_image
from airunner.windows.deterministic_generation_window import DeterministicGenerationWindow
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
        self.actionQuick_Export.triggered.connect(self.quick_export)
        self.actionQuit.triggered.connect(self.quit)
        self.actionPaste.triggered.connect(self.paste_image)
        self.actionCopy.triggered.connect(self.copy_image)
        self.actionCut.triggered.connect(self.cut_image)
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
        PromptBrowser(settings_manager=self.settings_manager, app=self)

    def save_prompt(self):
        self.settings_manager.create_saved_prompt(self.prompt, self.negative_prompt)

    def initialize_filter_actions(self):
        # add more filters:
        for filter in self.settings_manager.get_image_filters():
            action = self.menuFilters.addAction(filter.display_name)
            action.triggered.connect(partial(self.display_filter_window, filter))

    def display_filter_window(self, filter):
        FilterBase(self, filter.name).show()

    def import_image(self):
        file_path, _ = self.display_import_image_dialog(directory=self.settings_manager.path_settings.image_path)
        if file_path == "":
            return
        self.canvas.load_image(file_path)
        self.canvas.update()

    def export_image(self):
        file_path, _ = self.display_file_export_dialog()
        if file_path == "":
            return
        self.canvas.save_image(file_path)

    def quick_export(self):
        if os.path.isdir(self.image_path) is False:
            self.choose_image_export_path()
        if os.path.isdir(self.image_path) is False:
            return
        path = auto_export_image(self.canvas.current_layer.image_data.image, seed=self.seed)
        if path is not None:
            self.set_status_label(f"Image exported to {path}")


    def choose_image_export_path(self):
        # display a dialog to choose the export path
        path = QFileDialog.getExistingDirectory(None, "Select Directory")
        if path == "":
            return
        self.settings_manager.set_value("image_path", path)

    def display_file_export_dialog(self):
        return QFileDialog.getSaveFileName(
            self.window,
            "Export Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.gif)"
        )

    def display_import_image_dialog(self, label="Import Image", directory=""):
        return QFileDialog.getOpenFileName(
            self.window, label, directory, "Image Files (*.png *.jpg *.jpeg)"
        )

    def paste_image(self):
        self.canvas.paste_image_from_clipboard()
        self.canvas.current_layer.layer_widget.set_thumbnail()

    def copy_image(self):
        self.canvas.copy_image()

    def cut_image(self):
        self.canvas.cut_image()

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