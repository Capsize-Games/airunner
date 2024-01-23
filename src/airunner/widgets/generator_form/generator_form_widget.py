import random

from PIL import Image
from PyQt6.QtCore import pyqtSignal, QRect, pyqtSlot

from airunner.aihandler.settings import MAX_SEED
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.generator_form.templates.generatorform_ui import Ui_generator_form
from airunner.aihandler.logger import Logger


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
    logger = Logger(prefix="GeneratorForm")

    @property
    def is_txt2img(self):
        return self.generator_section == "txt2img"

    @property
    def is_outpaint(self):
        return self.generator_section == "outpaint"

    @property
    def is_depth2img(self):
        return self.generator_section == "depth2img"

    @property
    def is_pix2pix(self):
        return self.generator_section == "pix2pix"

    @property
    def is_upscale(self):
        return self.generator_section == "upscale"

    @property
    def is_superresolution(self):
        return self.generator_section == "superresolution"

    @property
    def is_txt2vid(self):
        return self.generator_section == "txt2vid"

    @property
    def generator_section(self):
        return self.settings["pipeline"]

    @property
    def generator_name(self):
        return self.settings["current_image_generator"]

    @property
    def random_seed(self):
        return self.generator_settings["random_seed"]

    @property
    def seed(self):
        return self.generator_settings["seed"]

    @seed.setter
    def seed(self, val):
        settings = self.settings
        settings["generator_settings"]["seed"] = val
        self.settings = settings

    @property
    def image_scale(self):
        return self.generator_settings["image_guidance_scale"]

    @property
    def active_rect(self):
        rect = QRect(
            self.active_grid_settings["pos_x"],
            self.active_grid_settings["pos_y"],
            self.active_grid_settings["width"],
            self.active_grid_settings["height"]
        )
        rect.translate(-self.canvas_settings["pos_x"], -self.canvas_settings["pos_y"])

        return rect

    @property
    def enable_controlnet(self):
        return self.generator_settings["enable_controlnet"]

    @property
    def controlnet_image(self):
        return self.controlnet_settings["image"]

    def on_application_settings_changed_signal(self):
        # if self.initialized:
        #     if self.current_prompt_value != self.generator_settings["prompt"]:
        #         self.current_prompt_value = self.generator_settings["prompt"]
        #         self.ui.prompt.setPlainText(self.current_prompt_value)
        #     if self.current_negative_prompt_value != self.generator_settings["negative_prompt"]:
        #         self.current_negative_prompt_value = self.generator_settings["negative_prompt"]
        #         self.ui.negative_prompt.setPlainText(self.current_negative_prompt_value)
        self.activate_ai_mode()
    
    @pyqtSlot(object)
    def on_progress_signal(self, message):
        self.handle_progress_bar(message)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initialized = False
        self.ui.generator_form_tabs.tabBar().hide()
        self.activate_ai_mode()
        self.register("application_settings_changed_signal", self)
        self.register("generate_image_signal", self)
        self.register("stop_image_generator_progress_bar_signal", self)
        self.register("progress_signal", self)

    def activate_ai_mode(self):
        self.ui.generator_form_tabs.setCurrentIndex(1 if self.settings["ai_mode"] is True else 0)
    
    """
    Slot functions

    The following functions are defined in and connected to the appropriate
    signals in the corresponding ui file.
    """
    def action_clicked_button_save_prompts(self):
        self.emit("save_stablediffusion_prompt_signal")

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
        self.generate(image=self.get_service("current_active_image")())

    def handle_interrupt_button_clicked(self):
        self.emit("engine_cancel_signal")
    """
    End Slot functions
    """

    def generate(self, image=None, seed=None):
        if seed is None:
            seed = self.generator_settings["seed"]
        if self.generator_settings["n_samples"] > 1:
            self.emit("engine_stop_processing_queue_signal")
        self.call_generate(image, seed=seed)
        self.seed_override = None
        self.emit("engine_start_processing_queue")

    def on_generate_image_signal(self, message):
        self.call_generate(**message)

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
                self.generator_settings["enable_input_image"]
            )
            if enable_input_image:
                input_image = self.generator_settings["input_image"]
            elif self.generator_section == "txt2img":
                input_image = override_data.get("input_image", None)
                image = input_image
            image = input_image if not image else image
            override_data["input_image"] = image

            if self.is_upscale and image is None:
                image = self.get_service("current_active_image")()
            
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
                current_layer = self.get_service("current_layer")()
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

    def do_generate(self, extra_options=None, seed=None, do_deterministic=False, override_data=False):
        if not extra_options:
            extra_options = {}

        if self.enable_controlnet:
            extra_options["controlnet_image"] = self.ui.controlnet_settings.current_controlnet_image

        self.set_seed(seed=seed)

        if self.deterministic_data and do_deterministic:
            return self.do_deterministic_generation(extra_options)

        action = self.generator_section

        if not override_data:
            override_data = {}
        
        action = override_data.get("action", action)
        prompt = override_data.get("prompt", self.generator_settings["prompt"])
        negative_prompt = override_data.get("negative_prompt", self.generator_settings["negative_prompt"])
        steps = int(override_data.get("steps", self.generator_settings["steps"]))
        strength = float(override_data.get("strength", self.generator_settings["strength"] / 100.0))
        image_guidance_scale = float(override_data.get("image_guidance_scale", self.generator_settings["image_guidance_scale"] / 10000.0 * 100.0))
        scale = float(override_data.get("scale", self.generator_settings["scale"] / 100))
        seed = int(override_data.get("seed", self.generator_settings["seed"]))
        ddim_eta = float(override_data.get("ddim_eta", self.generator_settings["ddim_eta"]))
        n_iter = int(override_data.get("n_iter", 1))
        n_samples = int(override_data.get("n_samples", self.generator_settings["n_samples"]))
        # iterate over all keys in model_data
        model_data=self.generator_settings
        for k,v in override_data.items():
            if k.startswith("model_data_"):
                model_data[k.replace("model_data_", "")] = v
        scheduler = override_data.get("scheduler", self.generator_settings["scheduler"])
        enable_controlnet = bool(override_data.get("enable_controlnet", self.generator_settings["enable_controlnet"]))
        controlnet = override_data.get("controlnet", self.generator_settings["controlnet"])
        controlnet_conditioning_scale = float(override_data.get("controlnet_conditioning_scale", self.generator_settings["controlnet_guidance_scale"]))
        width = int(override_data.get("width", self.settings["working_width"]))
        height = int(override_data.get("height", self.settings["working_height"]))
        clip_skip = int(override_data.get("clip_skip", self.generator_settings["clip_skip"]))
        batch_size = int(override_data.get("batch_size", 1))


        # get the model from the database
        print(model_data, self.generator_settings["model"])
        name = model_data["name"] if "name" in model_data else self.generator_settings["model"]
        model = self.get_service("ai_model_by_name")(name)
        
        print("MODEL:", model, name)
        # set the model data, first using model_data pulled from the override_data
        model_data = dict(
            name=model_data.get("name", model["name"]),
            path=model_data.get("path", model["path"]),
            branch=model_data.get("branch", model["branch"]),
            version=model_data.get("version", model['version']),
            category=model_data.get("category", model['category']),
            pipeline_action=model_data.get("pipeline_action", model["pipeline_action"]),
            enabled=model_data.get("enabled", model["enabled"]),
            default=model_data.get("default", model["is_default"])
        )

        input_image = override_data.get("input_image", None),
        if input_image:
            # check if input image is a tupil
            if isinstance(input_image, tuple):
                input_image = input_image[0]

        original_model_data = {}
        if input_image is not None:
            if isinstance(input_image, tuple):
                input_image_info = input_image[0].info
            else:
                input_image_info = input_image.info

            keys = [
                "name", 
                "path", 
                "branch", 
                "version", 
                "category", 
                "pipeline_action", 
                "enabled", 
                "default",
            ]
            original_model_data = {
                key: model_data.get(
                    key, input_image_info.get(key, "")) for key in keys
            }

        # get controlnet_dropdown from active tab
        nsfw_filter = self.settings["nsfw_filter"]
        options = dict(
            sd_request=True,
            prompt=prompt,
            negative_prompt=negative_prompt,
            steps=steps,
            ddim_eta=ddim_eta,  # only applies to ddim scheduler
            n_iter=n_iter,
            n_samples=n_samples,
            scale=scale,
            seed=seed,
            model=model['name'],
            model_data=model_data,
            original_model_data=original_model_data,
            scheduler=scheduler,
            model_path=model["path"],
            model_branch=model["branch"],
            # lora=self.available_lora(action),
            generator_section=self.generator_section,
            width=width,
            height=height,
            do_nsfw_filter=nsfw_filter,
            pos_x=0,
            pos_y=0,
            outpaint_box_rect=self.active_rect,
            hf_token=self.settings["hf_api_key_read_key"],
            model_base_path=self.path_settings["base_path"],
            outpaint_model_path=self.path_settings["inpaint_model_path"],
            pix2pix_model_path=self.path_settings["pix2pix_model_path"],
            depth2img_model_path=self.path_settings["depth2img_model_path"],
            upscale_model_path=self.path_settings["upscale_model_path"],
            image_path=self.path_settings["image_path"],
            lora_path=self.path_settings["lora_model_path"],
            embeddings_path=self.path_settings["embeddings_model_path"],
            video_path=self.path_settings["video_path"],
            clip_skip=clip_skip,
            batch_size=batch_size,
            variation=self.generator_settings["variation"],
            deterministic_generation=False,
            input_image=input_image,
            enable_controlnet=enable_controlnet,
            controlnet_conditioning_scale=controlnet_conditioning_scale,
            controlnet=controlnet,
            allow_online_mode=self.settings["allow_online_mode"],
            hf_api_key_read_key=self.settings["hf_api_key_read_key"],
            hf_api_key_write_key=self.settings["hf_api_key_write_key"],
            unload_unused_model=self.memory_settings["unload_unused_models"],
            move_unused_model_to_cpu=self.memory_settings["move_unused_model_to_cpu"],
        )

        if self.controlnet_image:
            options["controlnet_image"] = self.controlnet_image

        if action in ["txt2img", "img2img", "outpaint", "depth2img"]:
            options[f"strength"] = strength
        elif action in ["pix2pix"]:
            options[f"image_guidance_scale"] = image_guidance_scale

        """
        Emitting generate_signal with options allows us to pass more options to the dict from
        modal windows such as the image interpolation window.
        """
        memory_options = self.get_memory_options()

        self.logger.info(f"Attempting to generate image")

        self.emit("image_generate_request_signal", dict(
            action=action,
            options={
                **options,
                **extra_options,
                **memory_options
            }
        ))


    def get_memory_options(self):
        return {
            "use_last_channels": self.memory_settings["use_last_channels"],
            "use_enable_sequential_cpu_offload": self.memory_settings["use_enable_sequential_cpu_offload"],
            "enable_model_cpu_offload": self.memory_settings["enable_model_cpu_offload"],
            "use_attention_slicing": self.memory_settings["use_attention_slicing"],
            "use_tf32": self.memory_settings["use_tf32"],
            "use_cudnn_benchmark": self.memory_settings["use_cudnn_benchmark"],
            "use_enable_vae_slicing": self.memory_settings["use_enable_vae_slicing"],
            "use_accelerated_transformers": self.memory_settings["use_accelerated_transformers"],
            "use_torch_compile": self.memory_settings["use_torch_compile"],
            "use_tiled_vae": self.memory_settings["use_tiled_vae"],
            "use_tome_sd": self.memory_settings["use_tome_sd"],
            "tome_sd_ratio": self.memory_settings["tome_sd_ratio"],
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
        setattr(self.generator_settings, key, value)
        self.save_db_session()
        self.changed_signal.emit(key, value)

    def showEvent(self, event):
        super().showEvent(event)
        self.set_form_values()
        self.initialized = True
    
    def set_form_values(self):
        self.ui.prompt.blockSignals(True)
        self.ui.negative_prompt.blockSignals(True)
        self.ui.prompt.setPlainText(self.generator_settings["prompt"])
        self.ui.negative_prompt.setPlainText(self.generator_settings["negative_prompt"])
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