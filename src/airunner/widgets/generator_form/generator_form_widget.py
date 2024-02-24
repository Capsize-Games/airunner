import random

from PIL import Image
from PyQt6.QtCore import pyqtSignal, QRect

from airunner.aihandler.stablediffusion.sd_request import SDRequest
from airunner.enums import SignalCode, ServiceCode, GeneratorSection, ImageCategory
from airunner.aihandler.settings import MAX_SEED
from airunner.settings import PHOTO_REALISTIC_NEGATIVE_PROMPT, ILLUSTRATION_NEGATIVE_PROMPT
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.generator_form.templates.generatorform_ui import Ui_generator_form


class GeneratorForm(BaseWidget):
    widget_class_ = Ui_generator_form
    changed_signal = pyqtSignal(str, object)
    deterministic_generation_window = None
    deterministic_images = []
    deterministic_data = None
    deterministic = False
    seed_override = None
    deterministic_index = 0
    deterministic_seed = None
    initialized = False
    parent = None
    current_prompt_value = None
    current_negative_prompt_value = None

    @property
    def is_txt2img(self):
        return self.generator_section == GeneratorSection.TXT2IMG.value

    @property
    def is_outpaint(self):
        return self.generator_section == GeneratorSection.OUTPAINT.value

    @property
    def is_depth2img(self):
        return self.generator_section == GeneratorSection.DEPTH2IMG.value

    @property
    def is_pix2pix(self):
        return self.generator_section == GeneratorSection.PIX2PIX.value

    @property
    def is_upscale(self):
        return self.generator_section == GeneratorSection.UPSCALE.value

    @property
    def is_superresolution(self):
        return False  # deprecated

    @property
    def is_txt2vid(self):
        return False  # deprecated

    @property
    def generator_section(self):
        return self.settings["pipeline"]

    @property
    def generator_name(self):
        return self.settings["current_image_generator"]

    @property
    def random_seed(self):
        return self.settings["generator_settings"]["random_seed"]

    @property
    def seed(self):
        return self.settings["generator_settings"]["seed"]

    @seed.setter
    def seed(self, val):
        settings = self.settings
        settings["generator_settings"]["seed"] = val
        self.settings = settings

    @property
    def image_scale(self):
        return self.settings["generator_settings"]["image_guidance_scale"]

    @property
    def active_rect(self):
        rect = QRect(
            self.settings["active_grid_settings"]["pos_x"],
            self.settings["active_grid_settings"]["pos_y"],
            self.settings["active_grid_settings"]["width"],
            self.settings["active_grid_settings"]["height"]
        )
        rect.translate(-self.settings["canvas_settings"]["pos_x"], -self.settings["canvas_settings"]["pos_y"])

        return rect

    @property
    def enable_controlnet(self):
        return self.settings["generator_settings"]["enable_controlnet"]

    @property
    def controlnet_image(self):
        return self.settings["controlnet_settings"]["image"]

    def on_application_settings_changed_signal(self):
        self.activate_ai_mode()
    
    def on_progress_signal(self, message):
        self.handle_progress_bar(message)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initialized = False
        self.ui.generator_form_tabs.tabBar().hide()
        self.activate_ai_mode()
        self.register(SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL, self.on_application_settings_changed_signal)
        self.register(SignalCode.SD_GENERATE_IMAGE_SIGNAL, self.on_generate_image_signal)
        self.register(SignalCode.APPLICATION_STOP_SD_PROGRESS_BAR_SIGNAL, self.on_stop_image_generator_progress_bar_signal)
        self.register(SignalCode.SD_PROGRESS_SIGNAL, self.on_progress_signal)
        self.register(SignalCode.GENERATOR_FORM_UPDATE_VALUES_SIGNAL, self.set_form_values)
        self.register(SignalCode.LLM_IMAGE_PROMPT_GENERATED_SIGNAL, self.on_llm_image_prompt_generated_signal)

    def activate_ai_mode(self):
        ai_mode = self.settings.get("ai_mode", False)
        self.ui.generator_form_tabs.setCurrentIndex(1 if ai_mode is True else 0)
    
    """
    Slot functions

    The following functions are defined in and connected to the appropriate
    signals in the corresponding ui file.
    """
    def action_clicked_button_save_prompts(self):
        self.emit(SignalCode.SD_SAVE_PROMPT_SIGNAL)

    def handle_prompt_changed(self):
        settings = self.settings
        value = self.ui.prompt.toPlainText()
        self.current_prompt_value = value
        settings["generator_settings"]["prompt"] = value
        self.settings = settings

    def handle_negative_prompt_changed(self):
        settings = self.settings
        value = self.ui.negative_prompt.toPlainText()
        self.current_negative_prompt_value = value
        settings["generator_settings"]["negative_prompt"] = value
        self.settings = settings

    def handle_generate_button_clicked(self):
        self.start_progress_bar()
        self.generate(image=self.get_service(ServiceCode.CURRENT_ACTIVE_IMAGE)())

    def handle_interrupt_button_clicked(self):
        self.emit(SignalCode.ENGINE_CANCEL_SIGNAL)
    """
    End Slot functions
    """

    def generate(self, image=None, seed=None):
        if seed is None:
            seed = self.settings["generator_settings"]["seed"]
        if self.settings["generator_settings"]["n_samples"] > 1:
            self.emit(SignalCode.ENGINE_STOP_PROCESSING_QUEUE_SIGNAL)
        self.call_generate(image, seed=seed)
        self.seed_override = None
        self.emit(SignalCode.ENGINE_START_PROCESSING_QUEUE_SIGNAL)

    def on_generate_image_signal(self, message):
        self.call_generate(
            image=message["image"],
            override_data=message["meta_data"]
        )

    def call_generate(self, image=None, seed=None, override_data=None):
        override_data = {} if override_data is None else override_data

        if self.generator_section in (
            "txt2img",
            "pix2pix",
            "depth2img",
            "outpaint",
            "controlnet",
            "superresolution",
            "upscale"
        ):
            self.start_progress_bar()

            # Get input image from input image
            enable_input_image = override_data.get(
                "enable_input_image",
                self.settings["generator_settings"]["input_image_settings"]["enable_input_image"]
            )
            if enable_input_image:
                input_image = self.settings["generator_settings"]["input_image"]
            elif self.generator_section == "txt2img":
                input_image = override_data.get("input_image", None)
                image = input_image
            image = input_image if not image else image
            override_data["input_image"] = image

            if self.is_upscale and image is None:
                image = self.get_service(ServiceCode.CURRENT_ACTIVE_IMAGE)()
            
            if self.is_upscale and image is None:
                return

            if image is None:
                if self.is_txt2img:
                    return self.do_generate(seed=seed, override_data=override_data)
                # Create a transparent image the size of  active_grid_area_rect
                width = self.settings["working_width"]
                height = self.settings["working_height"]
                image = Image.new("RGBA", (int(width), int(height)), (0, 0, 0, 0))
            
            use_cropped_image = override_data.get("use_cropped_image", True)
            original_image = image.copy()
            if use_cropped_image:
                # Create a copy of the image and paste the cropped image into it

                # Copy the image and convert to RGBA
                img = image.copy().convert("RGBA")

                # Create a new image
                new_image = Image.new(
                    "RGBA",
                    (
                        self.settings["working_width"], 
                        self.settings["working_height"]
                    ),
                    (255, 255, 255, 0)
                )

                # Get the cropped image
                cropped_outpaint_box_rect = self.active_rect
                current_layer = self.get_service(ServiceCode.CURRENT_LAYER)()
                crop_location = (
                    cropped_outpaint_box_rect.x() - current_layer["pos_x"],
                    cropped_outpaint_box_rect.y() - current_layer["pos_y"],
                    cropped_outpaint_box_rect.width(),
                    cropped_outpaint_box_rect.height()
                )

                # Paste the cropped image into the new image
                new_image.paste(img.crop(crop_location), (0, 0))

                # Convert the new image to RGB and assign it to image variable
            else:
                new_image = image

            # Create the mask image
            mask = Image.new("RGB", (new_image.width, new_image.height), (255, 255, 255))
            for x in range(new_image.width):
                for y in range(new_image.height):
                    try:
                        if new_image.getpixel((x, y))[3] != 0:
                            mask.putpixel((x, y), (0, 0, 0))
                    except IndexError:
                        pass
            
            # Save the mask and input image for debugging
            image = new_image.convert("RGB")

            # Generate a new image using the mask and input image
            self.do_generate({
                "mask": mask,
                "image": image,
                "original_image": original_image,
                "location": QRect(0, 0, self.settings["working_width"], self.settings["working_height"])
            }, seed=seed, override_data=override_data)
        elif self.generator_section == "vid2vid":
            images = self.prep_video()
            self.do_generate({
                "images": images
            }, seed=seed)
        else:
            self.do_generate(seed=seed, override_data=override_data)

    def prep_video(self):
        return []

    def on_llm_image_prompt_generated_signal(self, data):
        prompt = data.get("prompt", None)
        prompt_type = data.get("type", ImageCategory.PHOTO.value)
        self.ui.prompt.setPlainText(prompt)
        if prompt_type == "photo":
            negative_prompt = PHOTO_REALISTIC_NEGATIVE_PROMPT
        else:
            negative_prompt = ILLUSTRATION_NEGATIVE_PROMPT
        self.ui.negative_prompt.setPlainText(negative_prompt)
        self.handle_prompt_changed()
        self.handle_negative_prompt_changed()
        self.handle_generate_button_clicked()

    def do_generate(
        self,
        extra_options: dict = None,
        seed: int = None,
        override_data: dict = None
    ):
        if not extra_options:
            extra_options = {}

        # TODO: fix controlnet
        # if self.enable_controlnet:
        #     extra_options["controlnet_image"] = self.ui.controlnet_settings.current_controlnet_image

        self.set_seed(seed=seed)

        self.logger.info(f"Attempting to generate image")

        action = self.generator_section
        model_data = self.settings["generator_settings"]
        for k, v in override_data.items():
            if k.startswith("model_data_"):
                model_data[k.replace("model_data_", "")] = v
        name = model_data["name"] if "name" in model_data else self.settings["generator_settings"]["model"]
        model = self.get_service("ai_model_by_name")(name)
        prompt = override_data.get("prompt", self.settings["generator_settings"]["prompt"])
        negative_prompt = override_data.get("negative_prompt", self.settings["generator_settings"]["negative_prompt"])
        model_data = {
            "name": model_data.get("name", model["name"]),
            "path": model_data.get("path", model["path"]),
            "branch": model_data.get("branch", model["branch"]),
            "version": model_data.get("version", model['version']),
            "category": model_data.get("category", model['category']),
            "pipeline_action": model_data.get("pipeline_action", model["pipeline_action"]),
            "enabled": model_data.get("enabled", model["enabled"]),
            "default": model_data.get("default", model["is_default"])
        }
        self.emit(
            SignalCode.SD_IMAGE_GENERATE_REQUEST_SIGNAL,
            SDRequest()(
                model=model,
                model_data=model_data,
                settings=self.settings,
                override_data=override_data,
                prompt=prompt,
                negative_prompt=negative_prompt,
                action=action,
                active_rect=[] if not self.active_rect else self.active_rect,
                generator_section=self.generator_section,
                enable_controlnet=self.enable_controlnet,
                controlnet_image=self.controlnet_image,
                memory_options=self.get_memory_options(),
                extra_options=extra_options,
            )
        )


    def get_memory_options(self):
        return {
            "use_last_channels": self.settings["memory_settings"]["use_last_channels"],
            "use_enable_sequential_cpu_offload": self.settings["memory_settings"]["use_enable_sequential_cpu_offload"],
            "enable_model_cpu_offload": self.settings["memory_settings"]["enable_model_cpu_offload"],
            "use_attention_slicing": self.settings["memory_settings"]["use_attention_slicing"],
            "use_tf32": self.settings["memory_settings"]["use_tf32"],
            "use_cudnn_benchmark": self.settings["memory_settings"]["use_cudnn_benchmark"],
            "use_enable_vae_slicing": self.settings["memory_settings"]["use_enable_vae_slicing"],
            "use_accelerated_transformers": self.settings["memory_settings"]["use_accelerated_transformers"],
            "use_torch_compile": self.settings["memory_settings"]["use_torch_compile"],
            "use_tiled_vae": self.settings["memory_settings"]["use_tiled_vae"],
            "use_tome_sd": self.settings["memory_settings"]["use_tome_sd"],
            "tome_sd_ratio": self.settings["memory_settings"]["tome_sd_ratio"],
        }

    def set_seed(self, seed=None):
        """
        Set the seed - either set to random, deterministic or keep current, then display the seed in the UI.
        :return:
        """
        self.set_primary_seed(seed)

    def set_primary_seed(self, seed=None):
        if self.deterministic_data:
            self.seed = self.deterministic_data["options"][f"seed"]
        elif self.random_seed:
            self.seed = random.randint(0, MAX_SEED)
        elif seed is not None:
            self.seed = seed

    def handle_progress_bar(self, message):
        step = message.get("step")
        total = message.get("total")
        action = message.get("action")
        tab_section = message.get("tab_section")

        if step == 0 and total == 0:
            current = 0
        else:
            try:
                current = (step / total)
            except ZeroDivisionError:
                current = 0
        self.set_progress_bar_value(tab_section, action, int(current * 100))
    
    def set_progress_bar_value(self, tab_section, section, value):
        progressbar = self.ui.progress_bar
        if not progressbar:
            return
        if progressbar.maximum() == 0:
            progressbar.setRange(0, 100)
        progressbar.setValue(value)

    def start_progress_bar(self):
        self.ui.progress_bar.setRange(0, 0)
        self.ui.progress_bar.show()

    def handle_checkbox_change(self, key, widget_name):
        widget = getattr(self.ui, widget_name)
        value = widget.isChecked()
        setattr(self.settings["generator_settings"], key, value)
        self.save_db_session()
        self.changed_signal.emit(key, value)

    def showEvent(self, event):
        super().showEvent(event)
        self.set_form_values()
        self.initialized = True

    def set_form_values(self):
        self.ui.prompt.blockSignals(True)
        self.ui.negative_prompt.blockSignals(True)
        self.ui.prompt.setPlainText(self.settings["generator_settings"]["prompt"])
        self.ui.negative_prompt.setPlainText(self.settings["generator_settings"]["negative_prompt"])
        self.ui.prompt.blockSignals(False)
        self.ui.negative_prompt.blockSignals(False)

    def clear_prompts(self):
        self.ui.prompt.setPlainText("")
        self.ui.negative_prompt.setPlainText("")

    def new_batch(self, index, image, data):
        self.new_batch(index, image, data)
        """
        Generate a batch of images using deterministic geneartion based on a previous deterministic generation
        batch. The previous seed that was chosen should be re-used with the index added to it to generate the new
        batch of images.
        :return:
        """
        if not data["options"]["deterministic_seed"]:
            data["options"][f"seed"] = int(data["options"][f"seed"]) + index
            seed = data["options"][f"seed"]
        else:
            seed = data["options"][f"deterministic_seed"]
        self.deterministic_seed = int(seed) + index
        self.deterministic_data = data
        self.deterministic_index = index
        self.deterministic = True
        self.generate(image, seed=self.deterministic_seed)
        self.deterministic = False
        self.deterministic_data = None
        self.deterministic_images = None
    
    def on_stop_image_generator_progress_bar_signal(self):
        self.stop_progress_bar()

    def stop_progress_bar(self):
        progressbar = self.ui.progress_bar
        if not progressbar:
            return
        progressbar.setRange(0, 100)
        progressbar.setValue(100)