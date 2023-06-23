import os
import random
from PIL import Image
from PyQt6 import uic
from PyQt6.QtCore import QRect, pyqtSignal
from PyQt6.uic.exceptions import UIFileException
from aihandler.settings import MAX_SEED, AVAILABLE_SCHEDULERS_BY_ACTION, MODELS
from airunner.windows.video import VideoPopup
from airunner.utils import load_default_models, load_models_from_path
from airunner.mixins.lora_mixin import LoraMixin
from PIL import PngImagePlugin


class GeneratorMixin(LoraMixin):
    generate_signal = pyqtSignal(dict)

    @property
    def available_models(self):
        return MODELS

    @property
    def model_base_path(self):
        return self.settings.model_base_path.get()

    @model_base_path.setter
    def model_base_path(self, val):
        self.settings.model_base_path.set(val)

    @property
    def width(self):
        return int(self.settings_manager.settings.working_width.get())

    @width.setter
    def width(self, val):
        self.settings_manager.settings.working_width.set(val)
        self.set_final_size_label()
        self.canvas.update()

    @property
    def height(self):
        return int(self.settings_manager.settings.working_height.get())

    @height.setter
    def height(self, val):
        self.settings_manager.settings.working_height.set(val)
        self.set_final_size_label()
        self.canvas.update()

    @property
    def steps(self):
        return self.settings.steps.get()

    @steps.setter
    def steps(self, val):
        self.settings.steps.set(val)

    @property
    def ddim_eta(self):
        return self.settings.ddim_eta.get()

    @ddim_eta.setter
    def ddim_eta(self, val):
        self.settings.ddim_eta.set(val)

    @property
    def prompt(self):
        return self.settings.prompt.get()

    @prompt.setter
    def prompt(self, val):
        self.settings.prompt.set(val)

    @property
    def negative_prompt(self):
        return self.settings.negative_prompt.get()

    @negative_prompt.setter
    def negative_prompt(self, val):
        self.settings.negative_prompt.set(val)

    @property
    def scale(self):
        return self.settings.scale.get()

    @scale.setter
    def scale(self, val):
        self.settings.scale.set(val)

    @property
    def image_scale(self):
        return self.settings.image_guidance_scale.get()

    @image_scale.setter
    def image_scale(self, val):
        self.settings.image_guidance_scale.set(val)

    @property
    def strength(self):
        return self.settings.strength.get()

    @strength.setter
    def strength(self, val):
        self.settings.strength.set(val)

    @property
    def seed(self):
        return self.settings.seed.get()

    @seed.setter
    def seed(self, val):
        self.settings.seed.set(val)

    @property
    def random_seed(self):
        return self.settings.random_seed.get()

    @random_seed.setter
    def random_seed(self, val):
        self.settings.random_seed.set(val)

    @property
    def samples(self):
        return self.settings.n_samples.get()

    @samples.setter
    def samples(self, val):
        self.settings.n_samples.set(val)

    @property
    def model(self):
        return self.settings.model_var.get()

    @model.setter
    def model(self, val):
        self.settings.model_var.set(val)

    @property
    def scheduler(self):
        return self.settings.scheduler_var.get()

    @scheduler.setter
    def scheduler(self, val):
        self.settings.scheduler_var.set(val)

    @property
    def downscale_amount(self):
        return self.settings.downscale_amount.get()

    @downscale_amount.setter
    def downscale_amount(self, val):
        self.settings.downscale_amount.set(val)

    @property
    def do_upscale_by_active_grid(self):
        return self.settings.do_upscale_by_active_grid.get()

    @do_upscale_by_active_grid.setter
    def do_upscale_by_active_grid(self, val):
        self.settings.do_upscale_by_active_grid.set(val)

    @property
    def do_upscale_full_image(self):
        return self.settings.do_upscale_full_image.get()

    @do_upscale_full_image.setter
    def do_upscale_full_image(self, val):
        self.settings.do_upscale_full_image.set(val)

    @property
    def image_to_new_layer(self):
        return self.settings_manager.settings.image_to_new_layer.get()

    def update_prompt(self, prompt):
        self.tabs[self.current_section].prompt.setPlainText(prompt)

    def update_negative_prompt(self, prompt):
        self.tabs[self.current_section].negative_prompt.setPlainText(prompt)

    def initialize(self):
        # create an emitter that will be triggered when generate is called
        self.settings_manager.settings.model_base_path.my_signal.connect(self.refresh_model_list)
        for tab_section in self._tabs.keys():  # iterate over each tab section (stablediffusion, kandinsky)
            self.override_tab_section = tab_section
            for tab in self.tabs.keys():  # iterate over each section within the tab section (txt2img, img2img, etc)
                self.tabs[tab] = uic.loadUi(os.path.join("pyqt/generate_form.ui"))

                # Remove embeddings and LoRA for Kandinsky sections as they are not supported
                if tab_section == "kandinsky":
                    self.tabs[tab].PromptTabsSection.removeTab(2)
                    self.tabs[tab].PromptTabsSection.removeTab(1)

                # set up the override_section for the tab so that we can force which tab is active
                # this is a hack in order to get around the auto-switching of tabs when the user
                # changes the section
                override_section = tab
                self.override_section = override_section

                # Initialize controlnet dropdown for controlnet section
                if tab == "controlnet":
                    controlnet_options = [
                        "Canny",
                        "MLSD",
                        "Depth",
                        "Normal",
                        "Segmentation",
                        "Lineart",
                        "Openpose",
                        "Scribble",
                        "Softedge",
                        "Pixel2Pixel",
                        "Inpaint",
                        "Shuffle",
                        "Anime",
                    ]
                    for option in controlnet_options:
                        self.tabs[tab].controlnet_dropdown.addItem(option)

                """
                The generator widget contains many different settings, however not all settings are
                available to each section. Rather than creating a new widget for each section, it is
                easier to delete the settings that are not available for a given section.
                """
                # delete strength slider for given sections
                if tab in ["txt2img", "pix2pix", "outpaint", "upscale", "superresolution", "txt2vid"]:
                    self.tabs[tab].strength.deleteLater()

                # delete image scale box for given sections
                if tab in ["txt2img", "img2img", "depth2img", "outpaint", "controlnet", "superresolution", "txt2vid"]:
                    self.tabs[tab].image_scale_box.deleteLater()

                # delete the sample slider for given sections
                if tab in ["upscale", "superresolution"]:
                    self.tabs[tab].samples_groupbox.deleteLater()
                    self.tabs[tab].full_image_radiobutton.setChecked(self.do_upscale_full_image == True)
                    self.tabs[tab].active_grid_radiobutton.setChecked(self.do_upscale_by_active_grid == True)
                    # handle radiobutton change
                    self.tabs[tab].full_image_radiobutton.toggled.connect(
                        lambda val, _tab=self.tabs[tab]: self.handle_upscale_full_image_change(val, _tab)
                    )
                    self.tabs[tab].active_grid_radiobutton.toggled.connect(
                        lambda val, _tab=self.tabs[tab]: self.handle_upscale_active_grid_change(val, _tab)
                    )
                    self.tabs[tab].downscale_spinbox.setValue(self.downscale_amount)
                    self.tabs[tab].downscale_spinbox.valueChanged.connect(
                        lambda val, _tab=self.tabs[tab]: self.handle_downscale_spinbox_change(val, _tab)
                    )
                    self.set_final_size_label(self.tabs[tab])
                else:
                    # delete downscale settings for sections that are not upscale or superresolution
                    self.tabs[tab].downscale_settings.deleteLater()
                    self.tabs[tab].downscale_settings_radiobuttons.deleteLater()
                    self.tabs[tab].downscale_settings_sizes.deleteLater()
                    self.tabs[tab].active_grid_radiobutton.deleteLater()
                    self.tabs[tab].full_image_radiobutton.deleteLater()
                    self.tabs[tab].downscale_label.deleteLater()
                    self.tabs[tab].downscale_amount_container.deleteLater()
                    self.tabs[tab].downscale_spinbox.deleteLater()
                    self.tabs[tab].final_size_label.deleteLater()
                    self.tabs[tab].final_size.deleteLater()

                # delete controlnet settings for sections that are not controlnet
                if tab != "controlnet":
                    self.tabs[tab].controlnet_label.deleteLater()
                    self.tabs[tab].controlnet_dropdown.deleteLater()

                self.tabs[tab].interrupt_button.clicked.connect(self.interrupt)

        self.override_section = None

        for tab_section in self._tabs.keys():
            self.override_tab_section = tab_section
            for tab in self.tabs.keys():
                display_name = tab
                if display_name == "outpaint":
                    display_name = "inpaint / outpaint"

                if tab_section == "stablediffusion":
                    self.window.stableDiffusionTabWidget.addTab(self.tabs[tab], display_name)
                else:
                    self.window.kandinskyTabWidget.addTab(self.tabs[tab], display_name)

                self.tabs[tab].generate.clicked.connect(self.generate_callback)

            # iterate over each tab and connect steps_slider with steps_spinbox
            for tab_name in self.tabs.keys():
                self.override_section = tab_name
                tab = self.tabs[tab_name]

                tab.toggleAllLora.clicked.connect(lambda checked, _tab=tab: self.toggle_all_lora(checked, _tab))

                # tab.prompt is QPlainTextEdit - on text change, call handle_prompt_change
                tab.prompt.textChanged.connect(lambda _tab=tab: self.handle_prompt_change(_tab))
                tab.negative_prompt.textChanged.connect(lambda _tab=tab: self.handle_negative_prompt_change(_tab))

                tab.steps_slider.valueChanged.connect(lambda val, _tab=tab: self.handle_steps_slider_change(val, _tab))
                tab.steps_spinbox.valueChanged.connect(lambda val, _tab=tab: self.handle_steps_spinbox_change(val, _tab))

                # load models by section
                self.load_model_by_section(tab_section, tab, tab_name)

                # on change of tab.model_dropdown set the model in self.settings_manager
                tab.model_dropdown.currentIndexChanged.connect(
                    lambda val, _tab=tab, _section=tab_name: self.set_model(_tab, _section, val)
                )

                # set schedulers for each tab
                scheduler_action = tab_name
                if tab_section == "kandinsky":
                    scheduler_action = f"kandinsky_{tab_name}"
                tab.scheduler_dropdown.addItems(AVAILABLE_SCHEDULERS_BY_ACTION[scheduler_action])
                tab.scheduler_dropdown.currentIndexChanged.connect(
                    lambda val, _tab=tab, _section=tab_name: self.set_scheduler(_tab, _section, val)
                )

                # scale slider
                tab.scale_slider.valueChanged.connect(lambda val, _tab=tab: self.handle_scale_slider_change(val, _tab))
                tab.scale_spinbox.valueChanged.connect(lambda val, _tab=tab: self.handle_scale_spinbox_change(val, _tab))

                tab.image_scale_slider.valueChanged.connect(
                    lambda val, _tab=tab: self.handle_image_scale_slider_change(val, _tab))
                tab.image_scale_spinbox.valueChanged.connect(
                    lambda val, _tab=tab: self.handle_image_scale_spinbox_change(val, _tab))

                # strength slider
                section = tab_name
                strength = 0
                if section in ["img2img", "depth2img", "controlnet"]:
                    if section == "img2img":
                        strength = self.settings_manager.settings.img2img_strength.get()
                    elif section == "depth2img":
                        strength = self.settings_manager.settings.depth2img_strength.get()
                    elif section == "controlnet":
                        strength = self.settings_manager.settings.controlnet_strength.get()
                    tab.strength_slider.setValue(int(strength))
                    tab.strength_spinbox.setValue(strength / 100)
                    tab.strength_slider.valueChanged.connect(
                        lambda val, _tab=tab: self.handle_strength_slider_change(val, _tab))
                    tab.strength_spinbox.valueChanged.connect(
                        lambda val, _tab=tab: self.handle_strength_spinbox_change(val, _tab))

                if section == "txt2vid":
                    # change the label tab.samples_groupbox label to "Frames"
                    tab.samples_groupbox.setTitle("Frames")

                tab.seed.textChanged.connect(lambda _tab=tab: self.text_changed(_tab))
                tab.random_checkbox.stateChanged.connect(
                    lambda val, _tab=tab: self.handle_random_checkbox_change(val, _tab))

                tab.random_checkbox.setChecked(self.random_seed is True)

                # samples slider
                tab.samples_slider.valueChanged.connect(
                    lambda val, _tab=tab: self.handle_samples_slider_change(val, _tab))
                tab.samples_spinbox.valueChanged.connect(
                    lambda val, _tab=tab: self.handle_samples_spinbox_change(val, _tab))

                # if samples is greater than 1 enable the interrupt_button
                if tab.samples_spinbox.value() > 1:
                    tab.interrupt_button.setEnabled(tab.samples_spinbox.value() > 1)
                self.set_default_values(tab_name, tab)
                self.override_section = None

            # assign callback to generate function on tab
            if tab_section == "stablediffusion":
                self.window.stableDiffusionTabWidget.currentChanged.connect(self.tab_changed_callback)
            else:
                self.window.kandinskyTabWidget.currentChanged.connect(self.tab_changed_callback)

        self.override_tab_section = None

        self.initialize_size_form_elements()
        self.initialize_size_sliders()
        self.initialize_lora()

    def handle_downscale_spinbox_change(self, value, tab):
        current_value = self.downscale_amount
        new_value = value
        if value == 1:
            if value > current_value or value == current_value:
                new_value = 2
            else:
                new_value = 0
        self.downscale_amount = value
        tab.downscale_spinbox.setValue(new_value)
        self.set_final_size_label(tab)

    def set_final_size_label(self, tab=None):
        if tab is None:
            tab = self.tabs[self.current_section]

        if self.current_section not in ["upscale", "superresolution"]:
            return

        image = self.canvas.current_layer.image_data.image
        if image:
            if self.do_upscale_by_active_grid:
                width = self.settings_manager.settings.working_width.get()
                height = self.settings_manager.settings.working_height.get()
            else:
                width = image.width
                height = image.height
        else:
            width = 0
            height = 0

        if self.downscale_amount > 0:
            width = width // self.downscale_amount
            height = height // self.downscale_amount

        if self.current_section == "upscale":
            width = width * 2
            height = height * 2
        elif self.current_section == "superresolution":
            width = width * 4
            height = height * 4

        # set final_size label text
        tab.final_size.setText(f"{width}x{height}")

    def handle_upscale_full_image_change(self, value, tab):
        self.do_upscale_full_image = value
        self.do_upscale_by_active_grid = value == False
        self.set_final_size_label(tab)

    def handle_upscale_active_grid_change(self, value, tab):
        self.do_upscale_by_active_grid = value
        self.do_upscale_full_image = value == False
        self.set_final_size_label(tab)

    def interrupt(self):
        print("Interrupting...")
        self.client.sd_runner.cancel()

    def refresh_model_list(self):
        for i, section in enumerate(self._tabs[self.currentTabSection].keys()):
            tab = self.tabWidget.widget(i)
            self.clear_model_list(tab)
            self.load_model_by_section(self.currentTabSection, tab, section)

    def clear_model_list(self, tab):
        tab.model_dropdown.clear()

    def load_model_by_section(self, tab_section, tab, section_name):
        if section_name in ["txt2img", "img2img"]:
            section_name = "generate"

        models = self.models if self.models else []
        default_models = load_default_models(tab_section, section_name)
        path = ""
        if section_name == "depth2img":
            path = self.settings_manager.settings.depth2img_model_path.get()
        elif section_name == "pix2pix":
            path = self.settings_manager.settings.pix2pix_model_path.get()
        elif section_name == "outpaint":
            path = self.settings_manager.settings.outpaint_model_path.get()
        elif section_name == "upscale":
            path = self.settings_manager.settings.upscale_model_path.get()
        if not path or path == "":
            path = self.settings_manager.settings.model_base_path.get()

        if tab_section == "stablediffusion":
            new_models = load_models_from_path(path)
            default_models += new_models
        models += default_models
        self.models = models

        tab.model_dropdown.addItems(default_models)

    def reset_settings(self):
        self.settings_manager.reset_settings_to_default()
        for tab_name in self.tabs.keys():
            tab = self.tabs[tab_name]
            self.set_default_values(tab_name, tab)
        self.canvas.update()


    def text_changed(self, tab):
        try:
            val = int(tab.seed.toPlainText())
            self.seed = val
        except ValueError:
            pass

    def handle_random_checkbox_change(self, val, _tab):
        if val == 2:
            self.random_seed = True
        else:
            self.random_seed = False
        _tab.seed.setEnabled(not self.random_seed)

    def video_handler(self, data):
        filename = data["video_filename"]
        VideoPopup(settings_manager=self.settings_manager, file_path=filename)

    def image_handler(self, image, data, nsfw_content_detected):
        if data["action"] == "txt2vid":
            return self.video_handler(data)

        if self.settings_manager.settings.auto_export_images.get():
            self.auto_export_image(image, data)

        self.stop_progress_bar(data["action"])
        if nsfw_content_detected and self.settings_manager.settings.nsfw_filter.get():
            self.message_handler("NSFW content detected, try again.", error=True)
        else:
            if data["action"] != "outpaint" and self.image_to_new_layer and self.canvas.current_layer.image_data.image is not None:
                self.canvas.add_layer()
            # print width and height of image
            self.canvas.image_handler(image, data)
            self.message_handler("")
            self.show_layers()

    def load_metadata(self, metadata):
        if metadata:
            action = metadata.get("action")
            prompt = None
            negative_prompt = None
            if "prompt" in metadata:
                prompt = metadata.get("prompt", "")
            if "negative_prompt" in metadata:
                negative_prompt = metadata.get("negative_prompt", "")
            scale = metadata.get("scale", None)
            seed = metadata.get("seed", None)
            steps = metadata.get("steps", None)
            ddim_eta = metadata.get("ddim_eta", None)
            n_iter = metadata.get("n_iter", None)
            n_samples = metadata.get("n_samples", None)
            model = metadata.get("model", None)
            # model_branch = metadata.get("model_branch", None)
            scheduler = metadata.get("scheduler", None)
            if prompt is not None:
                self.tabs[action].prompt.setPlainText(prompt)
            if negative_prompt is not None:
                self.tabs[action].negative_prompt.setPlainText(negative_prompt)
            if scale:
                scale = float(scale)
                self.tabs[action].scale_spinbox.setValue(float(scale))
                self.tabs[action].scale_slider.setValue(int(float(scale) * 100))
            if seed:
                self.tabs[action].seed.setPlainText(seed)
            if steps:
                steps = int(steps)
                self.tabs[action].steps_spinbox.setValue(steps)
                self.tabs[action].steps_slider.setValue(steps)
            if ddim_eta:
                ddim_eta = float(ddim_eta)
                self.tabs[action].ddim_eta_spinbox.setValue(ddim_eta)
                self.tabs[action].ddim_eta_slider.setValue(ddim_eta * 100)
            if n_iter:
                n_iter = int(n_iter)
                try:
                    self.tabs[action].n_iter_spinbox.setValue(n_iter)
                except AttributeError:
                    pass
                try:
                    self.tabs[action].n_iter_slider.setValue(n_iter)
                except AttributeError:
                    pass
            if n_samples:
                n_samples = int(n_samples)
                self.tabs[action].samples_spinbox.setValue(n_samples)
                self.tabs[action].samples_slider.setValue(n_samples)
            if model:
                self.tabs[action].model_dropdown.setCurrentText(model)
            if scheduler:
                self.tabs[action].scheduler_dropdown.setCurrentText(scheduler)

    def prepare_metadata(self, data):
        if not self.settings_manager.settings.export_metadata.get() or \
                self.settings_manager.settings.image_export_type.get() != "png":
            return None
        metadata = PngImagePlugin.PngInfo()
        options = data["options"]
        action = data["action"]
        metadata.add_text("action", action)
        if self.settings_manager.settings.image_export_metadata_prompt.get() is True:
            metadata.add_text("prompt", options[f'{action}_prompt'])
        if self.settings_manager.settings.image_export_metadata_negative_prompt.get() is True:
            metadata.add_text("negative_prompt", options[f'{action}_negative_prompt'])
        if self.settings_manager.settings.image_export_metadata_scale.get() is True:
            metadata.add_text("scale", str(options[f"{action}_scale"]))
        if self.settings_manager.settings.image_export_metadata_seed.get() is True:
            metadata.add_text("seed", str(options[f"{action}_seed"]))
        if self.settings_manager.settings.image_export_metadata_steps.get() is True:
            metadata.add_text("steps", str(options[f"{action}_steps"]))
        if self.settings_manager.settings.image_export_metadata_ddim_eta.get() is True:
            metadata.add_text("ddim_eta", str(options[f"{action}_ddim_eta"]))
        if self.settings_manager.settings.image_export_metadata_iterations.get() is True:
            metadata.add_text("n_iter", str(options[f"{action}_n_iter"]))
        if self.settings_manager.settings.image_export_metadata_samples.get() is True:
            metadata.add_text("n_samples", str(options[f"{action}_n_samples"]))
        if self.settings_manager.settings.image_export_metadata_model.get() is True:
            metadata.add_text("model", str(options[f"{action}_model"]))
        if self.settings_manager.settings.image_export_metadata_model_branch.get() is True:
            metadata.add_text("model_branch", str(options[f"{action}_model_branch"]))
        if self.settings_manager.settings.image_export_metadata_scheduler.get() is True:
            metadata.add_text("scheduler", str(options[f"{action}_scheduler"]))
        return metadata

    def auto_export_image(self, image, data):
        """
        Export image along with stats to image_path
        :return:
        """
        if data["action"] == "txt2vid":
            return
        base_path = self.settings_manager.settings.model_base_path.get()
        image_path = self.settings_manager.settings.image_path.get()
        image_path = "images" if image_path == "" else image_path
        path = os.path.join(base_path, image_path) if image_path == "images" else image_path
        if not os.path.exists(path):
            os.makedirs(path)
        # check for existing files, if they exist, increment the filename. filename should be in the format
        # <action>_<seed>_<N>.png
        extension = f".{self.settings_manager.settings.image_export_type.get()}"
        filename = data["action"] + "_" + str(self.seed)
        if os.path.exists(os.path.join(path, filename + extension)):
            i = 1
            while os.path.exists(os.path.join(path, filename + "_" + str(i) + extension)):
                i += 1
            filename = filename + "_" + str(i)
        metadata = self.prepare_metadata(data)
        if metadata:
            image.save(os.path.join(path, filename + extension), pnginfo=metadata)
        else:
            image.save(os.path.join(path, filename + extension))

    def handle_steps_slider_change(self, val, tab):
        tab.steps_spinbox.setValue(int(val))
        self.steps = int(val)

    def handle_prompt_change(self, tab):
        self.prompt = tab.prompt.toPlainText()

    def handle_negative_prompt_change(self, tab):
        self.negative_prompt = tab.negative_prompt.toPlainText()

    def handle_steps_spinbox_change(self, val, tab):
        tab.steps_slider.setValue(int(val))
        self.steps = int(val)

    def handle_scale_slider_change(self, val, tab):
        tab.scale_spinbox.setValue(val / 100.0)
        self.scale = val

    def handle_image_scale_slider_change(self, val, tab):
        tab.image_scale_spinbox.setValue(val / 100.0)
        try:
            self.image_scale = val
        except:
            pass

    def handle_image_scale_spinbox_change(self, val, tab):
        tab.image_scale_slider.setValue(int(val * 100))
        try:
            self.image_scale = val * 100
        except:
            pass

    def handle_scale_spinbox_change(self, val, tab):
        tab.scale_slider.setValue(int(val * 100))
        self.scale = val * 100

    def handle_strength_slider_change(self, val, tab):
        tab.strength_spinbox.setValue(val / 100.0)
        self.strength = val

    def handle_strength_spinbox_change(self, val, tab):
        tab.strength_slider.setValue(int(val * 100))
        self.strength = val

    def handle_seed_spinbox_change(self, val, tab):
        tab.seed.setText(str(int(val)))
        self.seed = int(val)

    def handle_samples_slider_change(self, val, tab):
        tab.samples_spinbox.setValue(int(val))
        self.samples = int(val)
        tab.interrupt_button.setEnabled(tab.samples_spinbox.value() > 1)

    def handle_samples_spinbox_change(self, val, tab):
        tab.samples_slider.setValue(int(val))
        self.samples = int(val)
        tab.interrupt_button.setEnabled(tab.samples_spinbox.value() > 1)

    def set_model(self, tab, section, val):
        model = tab.model_dropdown.currentText()
        self.model = model

    def set_scheduler(self, tab, section, val):
        scheduler = tab.scheduler_dropdown.currentText()
        self.scheduler = scheduler

    def generate_callback(self):
        # check that the correct model is in use for txt2vid
        if self.current_section == "txt2vid" and self.tabs[self.current_section].model_dropdown.currentText() != "damo-vilab":
            self.error_handler("Must use damo-vilab model with txt2vid")
        else:
            self.generate(True)


    def prep_video(self):
        pass

    @property
    def active_rect(self):
        rect = QRect(
            self.canvas.active_grid_area_rect.x(),
            self.canvas.active_grid_area_rect.y(),
            self.canvas.active_grid_area_rect.width(),
            self.canvas.active_grid_area_rect.height(),
        )
        rect.translate(-self.canvas.pos_x, -self.canvas.pos_y)

        return rect

    def tab_has_embeddings(self, tab):
        return tab not in ["upscale", "superresolution", "txt2vid"]

    def generate(self, image=None):
        if self.current_section in ("upscale", "superresolution") and self.do_upscale_full_image:
            image_data = self.canvas.current_layer.image_data
            image = image_data.image if image_data else None
            if image is None:
                self.error_handler("No image to upscale")
                return
            downscale_amount = self.downscale_amount
            if downscale_amount > 0:
                # downscale the image first
                image = image.resize(
                    (
                        int(image.width // downscale_amount),
                        int(image.height // downscale_amount),
                    ),
                    Image.BICUBIC,
                )
            self.requested_image = image
            self.start_progress_bar(self.current_section)
            self.do_generate({
                "mask": image.convert("RGB"),
                "image": image.convert("RGB"),
                "location": image_data.position
            })
        elif self.use_pixels:
            self.requested_image = image
            self.start_progress_bar(self.current_section)
            image_data = self.canvas.current_layer.image_data
            image = image_data.image if image_data else None

            if image is None:
                # create a transparent image the size of self.canvas.active_grid_area_rect
                width = self.settings_manager.settings.working_width.get()
                height = self.settings_manager.settings.working_height.get()
                image = Image.new("RGBA", (int(width), int(height)), (0, 0, 0, 0))

            img = image.copy().convert("RGBA")
            new_image = Image.new(
                "RGBA",
                (self.settings.working_width.get(), self.settings.working_height.get()),
                (0, 0, 0))

            cropped_outpaint_box_rect = self.active_rect
            crop_location = (
                cropped_outpaint_box_rect.x() - self.canvas.image_pivot_point.x(),
                cropped_outpaint_box_rect.y() - self.canvas.image_pivot_point.y(),
                cropped_outpaint_box_rect.width() - self.canvas.image_pivot_point.x(),
                cropped_outpaint_box_rect.height() - self.canvas.image_pivot_point.y()
            )
            new_image.paste(img.crop(crop_location), (0, 0))
            # save new_image to disc
            mask = Image.new("RGB", (new_image.width, new_image.height), (255, 255, 255))
            for x in range(new_image.width):
                for y in range(new_image.height):
                    try:
                        if new_image.getpixel((x, y))[3] != 0:
                            mask.putpixel((x, y), (0, 0, 0))
                    except IndexError:
                        pass

            # convert image to rgb
            image = new_image.convert("RGB")
            self.do_generate({
                "mask": mask,
                "image": image,
                "location": self.canvas.active_grid_area_rect
            })
        elif self.action == "vid2vid":
            images = self.prep_video()
            self.do_generate({
                "images": images
            })
        else:
            self.do_generate()

    def start_progress_bar(self, section):
        # progressBar: QProgressBar = self.tabs[section].progressBar
        # progressBar.setRange(0, 0)
        if self.progress_bar_started:
            return
        self.progress_bar_started = True
        self.tqdm_callback_triggered = False
        self.stop_progress_bar(section)
        self.tabs[section].progressBar.setRange(0, 0)
        self.tqdm_var.set({
            "step": 0,
            "total": 0,
            "action": section,
            "image": None,
            "data": None
        })

    def stop_progress_bar(self, section):
        self.tabs[section].progressBar.reset()
        self.tabs[section].progressBar.setRange(0, 100)

    def do_generate(self, extra_options=None):
        if not extra_options:
            extra_options = {}

        # self.start_progress_bar(self.current_section)

        action = self.current_section
        tab = self.tabs[action]

        if self.random_seed:
            # randomize seed
            seed = random.randint(0, MAX_SEED)
            self.seed = seed
            # set random_seed on current tab
            self.tabs[action].seed.setText(str(seed))
        if action in ("txt2img", "img2img", "pix2pix", "depth2img", "txt2vid"):
            samples = self.samples
        else:
            samples = 1

        prompt = self.tabs[action].prompt.toPlainText()
        negative_prompt = self.tabs[action].negative_prompt.toPlainText()
        if self.random_seed:
            seed = random.randint(0, MAX_SEED)
            self.settings.seed.set(seed)
        else:
            seed = self.seed

        # set the model data
        model = tab.model_dropdown.currentText()
        model_branch = None
        section_name = action
        if section_name in ["txt2img", "img2img"]:
            section_name = "generate"

        section_name = f"{self.currentTabSection}_{section_name}"

        if model in self.available_models[section_name]:
            model_path = self.available_models[section_name][model]["path"]
            model_branch = self.available_models[section_name][model].get("branch", "main")
        elif model not in self.models:
            model_names = list(self.available_models[section_name].keys())
            model = model_names[0]
            model_path = self.available_models[section_name][model]["path"]
            model_branch = self.available_models[section_name][model].get("branch", "main")
        else:
            path = self.settings_manager.settings.model_base_path.get()
            if action == "depth2img":
                path = self.settings_manager.settings.depth2img_model_path.get()
            elif action == "pix2pix":
                path = self.settings_manager.settings.pix2pix_model_path.get()
            elif action == "outpaint":
                path = self.settings_manager.settings.outpaint_model_path.get()
            elif action == "upscale":
                path = self.settings_manager.settings.upscale_model_path.get()
            model_path = os.path.join(path, model)

        # get controlnet_dropdown from active tab
        use_controlnet = False
        controlnet = ""
        if action == "controlnet":
            controlnet_dropdown = self.tabs[action].controlnet_dropdown
            # get controlnet from controlnet_dropdown
            controlnet = controlnet_dropdown.currentText()
            controlnet = controlnet.lower()
            use_controlnet = controlnet != "none"

        options = {
            f"{action}_prompt": prompt,
            f"{action}_negative_prompt": negative_prompt,
            f"{action}_steps": self.steps,
            f"{action}_ddim_eta": self.ddim_eta,  # only applies to ddim scheduler
            f"{action}_n_iter": 1,
            f"{action}_width": self.width,
            f"{action}_height": self.height,
            f"{action}_n_samples": samples,
            f"{action}_scale": self.scale / 100,
            f"{action}_seed": seed,
            f"{action}_model": model,
            f"{action}_scheduler": self.scheduler,
            f"{action}_model_path": model_path,
            f"{action}_model_branch": model_branch,
            f"{action}_lora": self.available_lora(action),
            f"generator_section": self.currentTabSection,
            f"width": self.width,
            f"height": self.height,
            "do_nsfw_filter": self.settings_manager.settings.nsfw_filter.get(),
            "model_base_path": self.model_base_path,
            "pos_x": 0,
            "pos_y": 0,
            "outpaint_box_rect": self.active_rect,
            "hf_token": self.settings_manager.settings.hf_api_key.get(),
            "use_controlnet": use_controlnet,
            "controlnet": controlnet,
        }

        if action == "superresolution":
            options["original_image_width"] = self.canvas.current_active_image_data.image.width
            options["original_image_height"] = self.canvas.current_active_image_data.image.height

        if action in ["img2img", "depth2img", "pix2pix", "controlnet"]:
            options[f"{action}_strength"] = self.strength / 100.0

        if action == "pix2pix":
            options[f"pix2pix_image_guidance_scale"] = self.image_scale

        """
        Emitting generate_signal with options allows us to pass more options to the dict from
        modal windows such as the image interpolation window.
        """
        self.generate_signal.emit(options)

        memory_options = {
            "use_last_channels": self.settings_manager.settings.use_last_channels.get(),
            "use_enable_sequential_cpu_offload": self.settings_manager.settings.use_enable_sequential_cpu_offload.get(),
            "enable_model_cpu_offload": self.settings_manager.settings.enable_model_cpu_offload.get(),
            "use_attention_slicing": self.settings_manager.settings.use_attention_slicing.get(),
            "use_tf32": self.settings_manager.settings.use_tf32.get(),
            "use_cudnn_benchmark": self.settings_manager.settings.use_cudnn_benchmark.get(),
            "use_enable_vae_slicing": self.settings_manager.settings.use_enable_vae_slicing.get(),
            "use_accelerated_transformers": self.settings_manager.settings.use_accelerated_transformers.get(),
            "use_torch_compile": self.settings_manager.settings.use_torch_compile.get(),
            "use_tiled_vae": self.settings_manager.settings.use_tiled_vae.get(),
        }

        data = {
            "action": action,
            "options": {
                **options,
                **extra_options,
                **memory_options
            }
        }
        # data = self.do_generate_data_injection(data)  # TODO: Extensions
        self.client.message = data

    """
    TODO: Extensions
    def do_generate_data_injection(self, data):
        for extension in self.settings_manager.settings.active_extensions.get():
            data = extension.generate_data_injection(data)
        return data
    """

    def tab_changed_callback(self, index):
        self.set_final_size_label()
        self.canvas.update()

    def set_default_values(self, section, tab):
        tab.prompt.setPlainText(self.prompt)
        tab.negative_prompt.setPlainText(self.negative_prompt)
        tab.steps_spinbox.setValue(self.steps)
        tab.scale_spinbox.setValue(self.scale / 100)
        if section == "pix2pix":
            val = self.settings_manager.settings.pix2pix_image_guidance_scale.get()
            tab.image_scale_spinbox.setValue(val / 100)
            if type(val) == float:
                val = int(val * 100)
            tab.image_scale_slider.setValue(val)
        try:
            tab.strength_spinbox.setValue(self.strength / 100)
        except:
            pass
        tab.seed.setText(str(self.seed))
        tab.samples_spinbox.setValue(self.samples)
        tab.model_dropdown.setCurrentText(self.model)
        try:
            tab.scheduler_dropdown.setCurrentText(self.scheduler)
        except RuntimeError:
            pass

    def handle_width_slider_change(self, val):
        self.window.width_spinbox.setValue(val)
        self.width = val

    def handle_width_spinbox_change(self, val):
        self.window.width_slider.setValue(int(val))
        self.width = int(val)

    def handle_height_slider_change(self, val):
        self.window.height_spinbox.setValue(int(val))
        self.height = int(val)

    def handle_height_spinbox_change(self, val):
        self.window.height_slider.setValue(int(val))
        self.height = int(val)

    def update_brush_size(self, val):
        self.settings_manager.settings.mask_brush_size.set(val)
        self.window.brush_size_spinbox.setValue(val)

    def brush_spinbox_change(self, val):
        self.settings_manager.settings.mask_brush_size.set(val)
        self.window.brush_size_slider.setValue(val)

    def initialize_size_form_elements(self):
        # width form elements
        self.window.width_slider.valueChanged.connect(lambda val: self.handle_width_slider_change(val))
        self.window.width_spinbox.valueChanged.connect(lambda val: self.handle_width_spinbox_change(val))

        # height form elements
        self.window.height_slider.valueChanged.connect(lambda val: self.handle_height_slider_change(val))
        self.window.height_spinbox.valueChanged.connect(lambda val: self.handle_height_spinbox_change(val))

    def initialize_size_sliders(self):
        self.window.width_slider.setValue(self.width)
        self.window.height_slider.setValue(self.height)
        self.window.width_spinbox.setValue(self.width)
        self.window.height_spinbox.setValue(self.height)
        self.window.brush_size_slider.setValue(self.settings.mask_brush_size.get())
        self.window.brush_size_slider.valueChanged.connect(self.update_brush_size)
        self.window.brush_size_spinbox.valueChanged.connect(self.brush_spinbox_change)
        self.window.brush_size_slider.setValue(self.settings_manager.settings.mask_brush_size.get())
        self.window.brush_size_spinbox.setValue(self.settings_manager.settings.mask_brush_size.get())
        self.set_size_form_element_step_values()

    def load_template(self, template_name):
        try:
            return uic.loadUi(
                os.path.join("pyqt", f"{template_name}.ui"))
        except UIFileException:
            return None
