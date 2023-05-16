import os
import random
import cv2
import numpy as np
from PIL import Image
from PyQt6 import uic
from PyQt6.QtCore import QPoint, QRect
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea
from PyQt6.uic.exceptions import UIFileException

from aihandler.settings import MAX_SEED, AVAILABLE_SCHEDULERS_BY_ACTION, MODELS
from airunner.windows.video import VideoPopup


class GeneratorMixin:
    lora_loaded = False

    @property
    def width(self):
        return int(self.settings_manager.settings.working_width.get())

    @width.setter
    def width(self, val):
        self.settings_manager.settings.working_width.set(val)
        self.canvas.update()

    @property
    def height(self):
        return int(self.settings_manager.settings.working_height.get())

    @height.setter
    def height(self, val):
        self.settings_manager.settings.working_height.set(val)
        self.canvas.update()

    @property
    def steps(self):
        return self.settings.steps.get()

    @steps.setter
    def steps(self, val):
        self.settings.steps.set(val)

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

    def initialize(self):
        sections = ["txt2img", "img2img", "depth2img", "pix2pix", "outpaint", "controlnet", "txt2vid"]
        self.tabs = {}
        for tab in self.sections:
            self.tabs[tab] = uic.loadUi(os.path.join("pyqt/generate_form.ui"))

        for tab in self.tabs:
            if tab != "controlnet":
                self.tabs[tab].controlnet_label.deleteLater()
                self.tabs[tab].controlnet_dropdown.deleteLater()
            else:
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
            if tab in ["txt2img", "pix2pix", "outpaint", "super_resolution", "txt2vid"]:
                self.tabs[tab].strength.deleteLater()
            if tab in ["txt2img", "img2img", "depth2img", "outpaint", "controlnet", "super_resolution", "txt2vid"]:
                self.tabs[tab].image_scale_box.deleteLater()
            if tab in ["txt2vid"]:
                self.tabs[tab].scheduler_label.deleteLater()
                self.tabs[tab].scheduler_dropdown.deleteLater()

        for tab in sections:
            self.window.tabWidget.addTab(self.tabs[tab], tab)

        # iterate over each tab and connect steps_slider with steps_spinbox
        for tab_name in self.tabs.keys():
            tab = self.tabs[tab_name]

            tab.steps_slider.valueChanged.connect(lambda val, _tab=tab: self.handle_steps_slider_change(val, _tab))
            tab.steps_spinbox.valueChanged.connect(lambda val, _tab=tab: self.handle_steps_spinbox_change(val, _tab))

            # load models by section
            self.load_model_by_section(tab, tab_name)

            # on change of tab.model_dropdown set the model in self.settings_manager
            tab.model_dropdown.currentIndexChanged.connect(
                lambda val, _tab=tab, _section=tab_name: self.set_model(_tab, _section, val)
            )

            # set schedulers for each tab
            if tab_name not in ["txt2vid"]:
                tab.scheduler_dropdown.addItems(AVAILABLE_SCHEDULERS_BY_ACTION[tab_name])
                # on change of tab.scheduler_dropdown set the scheduler in self.settings_manager
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

        # assign callback to generate function on tab
        self.window.tabWidget.currentChanged.connect(self.tab_changed_callback)

        # add callbacks
        for tab in sections:
            self.tabs[tab].generate.clicked.connect(self.generate_callback)
        # super_resolution_form.generate.clicked.connect(self.generate_callback)

        self.initialize_size_form_elements()
        self.initialize_size_sliders()
        self.initialize_lora()

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

        self.stop_progress_bar(data["action"])
        if nsfw_content_detected and self.settings_manager.settings.nsfw_filter.get():
            self.message_handler("NSFW content detected, try again.", error=True)
        else:
            if data["action"] != "outpaint" and self.settings_manager.settings.image_to_new_layer.get():
                self.canvas.add_layer()
            self.canvas.image_handler(image, data)
            self.message_handler("")
            self.show_layers()

    def handle_steps_slider_change(self, val, tab):
        tab.steps_spinbox.setValue(int(val))
        self.steps = int(val)

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
        #self.new_layer()
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

    def generate(
        self,
        do_generate=False,
        image=None,
        mask=None
    ):
        if self.use_pixels:
            self.requested_image = image
            self.start_progress_bar(self.current_section)
            try:
                image = self.canvas.current_layer.images[0].image
            except IndexError:
                image = None

            if image is None:
                # create a transparent image the size of self.canvas.active_grid_area_rect
                width = self.settings_manager.settings.working_width.get()
                height = self.settings_manager.settings.working_height.get()
                image = Image.new("RGBA", (int(width), int(height)), (0, 0, 0, 0))

            lines = self.canvas.current_layer.lines
            # combine lines with image
            for line in lines:
                # convert PIL.Image to numpy array
                image = np.array(image)
                start: QPoint = line.start_point
                end: QPoint = line.end_point
                color: QColor = line._pen["color"]
                image = cv2.line(
                    image,
                    (start.x(), start.y()),
                    (end.x(), end.y()),
                    (color.red(), color.green(), color.blue()),
                    int(line._pen["width"]))
                # convert numpy array to PIL.Image
                image = Image.fromarray(image)

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
        # get the name of the model from the model_dropdown
        sm = self.settings_manager.settings
        sm.set_namespace(action)

        if sm.random_seed.get():
            # randomize seed
            seed = random.randint(0, MAX_SEED)
            sm.seed.set(seed)
            # set random_seed on current tab
            self.tabs[action].seed.setText(str(seed))
        if action in ("txt2img", "img2img", "pix2pix", "depth2img", "txt2vid"):
            samples = sm.n_samples.get()
        else:
            samples = 1

        prompt = self.tabs[action].prompt.toPlainText()
        negative_prompt = self.tabs[action].negative_prompt.toPlainText()
        if self.random_seed:
            seed = random.randint(0, MAX_SEED)
            self.settings.seed.set(seed)
        else:
            seed = sm.seed.get()
        # set model, model_path and model_branch
        # model = sm.model_var.get()

        # set the model data
        model = tab.model_dropdown.currentText()
        model_branch = None
        section_name = action
        if section_name in ["txt2img", "img2img"]:
            section_name = "generate"
        if model in MODELS[section_name]:
            model_path = MODELS[section_name][model]["path"]
            model_branch = MODELS[section_name][model].get("branch", "main")
        elif model not in self.models:
            model_names = list(MODELS[section_name].keys())
            model = model_names[0]
            model_path = MODELS[section_name][model]["path"]
            model_branch = MODELS[section_name][model].get("branch", "main")
        else:
            model_path = model

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
            f"{action}_steps": sm.steps.get(),
            f"{action}_ddim_eta": sm.ddim_eta.get(),  # only applies to ddim scheduler
            f"{action}_n_iter": 1,
            f"{action}_width": sm.working_width.get(),
            f"{action}_height": sm.working_height.get(),
            f"{action}_n_samples": samples,
            f"{action}_scale": sm.scale.get() / 100,
            f"{action}_seed": seed,
            f"{action}_model": model,
            f"{action}_scheduler": sm.scheduler_var.get(),
            f"{action}_model_path": model_path,
            f"{action}_model_branch": model_branch,
            f"{action}_lora": self.settings_manager.settings.available_loras[action],
            f"width": sm.working_width.get(),
            f"height": sm.working_height.get(),
            "do_nsfw_filter": self.settings_manager.settings.nsfw_filter.get(),
            "model_base_path": sm.model_base_path.get(),
            "pos_x": 0,
            "pos_y": 0,
            "outpaint_box_rect": self.active_rect,
            "hf_token": self.settings_manager.settings.hf_api_key.get(),
            "use_controlnet": use_controlnet,
            "controlnet": controlnet,
        }
        if action == "superresolution":
            options["original_image_width"] = self.canvas.current_active_image.width
            options["original_image_height"] = self.canvas.current_active_image.height

        if action in ["img2img", "depth2img", "pix2pix", "controlnet"]:
            options[f"{action}_strength"] = sm.strength.get() / 100.0

        if action == "pix2pix":
            options[f"pix2pix_image_guidance_scale"] = sm.pix2pix_image_guidance_scale.get()
        memory_options = {
            "use_last_channels": sm.use_last_channels.get(),
            "use_enable_sequential_cpu_offload": sm.use_enable_sequential_cpu_offload.get(),
            "enable_model_cpu_offload": sm.enable_model_cpu_offload.get(),
            "use_attention_slicing": sm.use_attention_slicing.get(),
            "use_tf32": sm.use_tf32.get(),
            "use_cudnn_benchmark": sm.use_cudnn_benchmark.get(),
            "use_enable_vae_slicing": sm.use_enable_vae_slicing.get(),
            "use_xformers": sm.use_xformers.get(),
            "use_accelerated_transformers": sm.use_accelerated_transformers.get(),
            "use_torch_compile": sm.use_torch_compile.get(),
            "use_tiled_vae": sm.use_tiled_vae.get(),
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
        self.canvas.update()

    def set_default_values(self, section, tab):
        self.override_section = section
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
        self.override_section = None

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

    def initialize_lora(self):
        self.lora_loaded = False
        self.settings_manager.settings.lora_path.my_signal.connect(self.refresh_lora)
        self.refresh_lora()

    def refresh_lora(self):
        self.settings_manager.settings.available_loras = {}
        for tab_name in self.tabs.keys():
            tab = self.tabs[tab_name]
            self.load_lora_tab(tab, tab_name)

    def available_loras(self, tab_name):
        base_path = self.settings_manager.settings.model_base_path.get()
        lora_path = self.settings_manager.settings.lora_path.get() or "lora"
        if lora_path == "lora":
            lora_path = os.path.join(base_path, lora_path)
        if not os.path.exists(lora_path):
            return []
        if tab_name not in self.settings_manager.settings.available_loras.keys():
            self.settings_manager.settings.available_loras[tab_name] = []
            self.settings_manager.enable_save()
            self.settings_manager.settings.available_loras[tab_name] = self.get_list_of_available_loras(tab_name, lora_path)
            self.settings_manager.save_settings()
        return self.settings_manager.settings.available_loras[tab_name]

    def get_list_of_available_loras(self, tab_name, lora_path, lora_names=None):
        if lora_names is None:
            lora_names = []
        if not os.path.exists(lora_path):
            return lora_names
        possible_line_endings = ["ckpt", "safetensors", "bin"]
        for f in os.listdir(lora_path):
            if os.path.isdir(os.path.join(lora_path, f)):
                lora_names = self.get_list_of_available_loras(tab_name, os.path.join(lora_path, f), lora_names)
            if f.split(".")[-1] in possible_line_endings:
                name = f.split(".")[0]
                scale = 100.0
                enabled = True
                # check if we have scale in self.settings_manager.settings.available_loras[tab_name]
                if tab_name in self.settings_manager.settings.available_loras:
                    loras = self.settings_manager.settings.available_loras[tab_name] or []
                    for lora in loras:
                        if lora["name"] == name:
                            scale = lora["scale"]
                            enabled = lora["enabled"]
                            break
                lora_names.append({
                    "name": name,
                    "scale": scale,
                    "enabled": enabled,
                    "loaded": False
                })
        return lora_names

    def load_lora_tab(self, tab, tab_name=None):
        container = QWidget()
        container.setLayout(QVBoxLayout())
        for lora in self.available_loras(tab_name):
            lora_widget = self.load_template("lora_simplified")
            #lora_widget.enabledCheckbox.setText(lora["name"])
            lora_widget.label.setText(lora["name"])
            # scale = lora["scale"]
            # enabled = lora["enabled"]
            # lora_widget.scaleSlider.setValue(int(scale))
            # lora_widget.scaleSpinBox.setValue(scale / 100)
            # lora_widget.enabledCheckbox.setChecked(enabled)
            container.layout().addWidget(lora_widget)
            # lora_widget.scaleSlider.valueChanged.connect(
            #     lambda value, _lora_widget=lora_widget, _lora=lora, _tab_name=tab_name:
            #     self.handle_lora_slider(_lora, _lora_widget, value, _tab_name))
            # lora_widget.scaleSpinBox.valueChanged.connect(
            #     lambda value, _lora_widget=lora_widget, _lora=lora, _tab_name=tab_name:
            #     self.handle_lora_spinbox(_lora, _lora_widget, value, _tab_name))
            # lora_widget.enabledCheckbox.stateChanged.connect(
            #     lambda value, _lora=lora, _tab_name=tab_name:
            #     self.toggle_lora(lora, value, _tab_name))
        # add a vertical spacer to the end of the container
        container.layout().addStretch()
        # display tabs of tab.PromptTabsSection which is a QTabWidget
        tab.lora_scroll_area.setWidget(container)

    def load_template(self, template_name):
        try:
            return uic.loadUi(
                os.path.join("pyqt", f"{template_name}.ui"))
        except UIFileException:
            return None

    def toggle_lora(self, lora, value, tab_name):
        for n in range(len(self.available_loras(tab_name))):
            if self.settings_manager.settings.available_loras[tab_name][n]["name"] == lora["name"]:
                self.settings_manager.settings.available_loras[tab_name][n]["enabled"] = value == 2
        self.settings_manager.save_settings()

    def handle_lora_slider(self, lora, lora_widget, value, tab_name):
        for n in range(len(self.available_loras(tab_name))):
            if self.settings_manager.settings.available_loras[tab_name][n]["name"] == lora["name"]:
                self.settings_manager.settings.available_loras[tab_name][n]["scale"] = value / 100
        lora_widget.scaleSpinBox.setValue(lora["scale"])
        self.settings_manager.save_settings()

    def handle_lora_spinbox(self, lora, lora_widget, value, tab_name):
        for n in range(len(self.available_loras(tab_name))):
            if self.settings_manager.settings.available_loras[tab_name][n]["name"] == lora["name"]:
                self.settings_manager.settings.available_loras[tab_name][n]["scale"] = value * 100
        lora_widget.scaleSlider.setValue(int(lora["scale"]))
        self.settings_manager.save_settings()