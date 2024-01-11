import random

from PIL import Image
from PyQt6.QtCore import pyqtSignal, QRect

from airunner.aihandler.settings import MAX_SEED
from airunner.data.models import ActiveGridSettings, CanvasSettings
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.generator_form.templates.generatorform_ui import Ui_generator_form
from airunner.data.session_scope import session_scope


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
    generate_signal = pyqtSignal(dict)

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
        return self.app.pipeline

    @property
    def generator_name(self):
        return self.app.settings_manager.settings.current_image_generator

    @property
    def generator_settings(self):
        return self.app.settings_manager.generator_settings

    @property
    def random_seed(self):
        return self.app.settings_manager.generator.random_seed

    @property
    def random_latents_seed(self):
        return self.app.settings_manager.generator.random_latents_seed

    @property
    def latents_seed(self):
        return self.app.settings_manager.generator.latents_seed

    @latents_seed.setter
    def latents_seed(self, val):
        self.app.settings_manager.set_value("generator.latents_seed", val)
        self.app.standard_image_panel.ui.seed_widget_latents.ui.lineEdit.setText(str(val))

    @property
    def seed(self):
        return self.app.settings_manager.generator.seed

    @seed.setter
    def seed(self, val):
        self.app.settings_manager.set_value("generator.seed", val)
        self.app.standard_image_panel.ui.seed_widget.ui.lineEdit.setText(str(val))

    @property
    def image_scale(self):
        return self.app.settings_manager.generator.image_guidance_scale

    @property
    def active_rect(self):
        rect = QRect(
            self.app.settings_manager.active_grid_settings.pos_x,
            self.app.settings_manager.active_grid_settings.pos_y,
            self.app.settings_manager.active_grid_settings.width,
            self.app.settings_manager.active_grid_settings.height
        )
        rect.translate(-self.app.settings_manager.canvas_settings.pos_x, -self.app.settings_manager.canvas_settings.pos_y)

        return rect

    @property
    def enable_controlnet(self):
        return self.app.settings_manager.generator.enable_controlnet

    @property
    def controlnet_image(self):
        return self.app.standard_image_panel.ui.controlnet_settings.current_controlnet_image

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui.generator_form_tabs.tabBar().hide()
        self.app.ai_mode_toggled.connect(self.activate_ai_mode)
    
    def activate_ai_mode(self, active):
        self.ui.generator_form_tabs.setCurrentIndex(1 if active is True else 0)
    
    def toggle_advanced_generation(self):
        advanced_mode = self.app.settings_manager.settings.enable_advanced_mode

        # set the splitter sizes
        splitter_sizes = [1, 1, 0 if not advanced_mode else 1]
        
        self.ui.advanced_splitter.setSizes(splitter_sizes)
    
    def handle_changed_signal(self, key, value):
        print("generator_form: handle_changed_signal", key, value)
        if key == "generator.random_seed":
            self.set_primary_seed()
            self.ui.seed_widget.seed = self.seed
            self.ui.seed_widget.update_seed()
        elif key == "generator.random_latents_seed":
            self.set_latents_seed()
            self.ui.seed_widget_latents.latents_seed = self.latents_seed
            self.ui.seed_widget_latents.update_seed()
        elif key == "settings.enable_advanced_mode":
            self.toggle_advanced_generation()

    """
    Slot functions

    The following functions are defined in and connected to the appropriate
    signals in the corresponding ui file.
    """
    def action_clicked_button_save_prompts(self):
        self.app.settings_manager.create_saved_prompt(
            self.app.settings_manager.generator.prompt,
            self.app.settings_manager.generator.negative_prompt
        )

    def handle_prompt_changed(self):
        if not self.initialized:
            return
        self.app.settings_manager.set_value("generator.prompt", self.ui.prompt.toPlainText())

    def handle_negative_prompt_changed(self):
        if not self.initialized:
            return
        self.app.settings_manager.set_value("generator.negative_prompt", self.ui.negative_prompt.toPlainText())

    def toggle_prompt_builder_checkbox(self, toggled):
        pass

    def handle_generate_button_clicked(self):
        self.start_progress_bar()
        self.generate(image=self.app.current_active_image())

    def handle_interrupt_button_clicked(self):
        self.app.client.cancel()
    """
    End Slot functions
    """

    def generate(self, image=None, seed=None):
        if seed is None:
            seed = self.app.standard_image_panel.ui.seed_widget.seed
        if self.app.standard_image_panel.ui.samples_widget.current_value > 1:
            self.app.client.do_process_queue = False
        self.call_generate(image, seed=seed)
        self.seed_override = None
        self.app.client.do_process_queue = True

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
                self.app.settings_manager.generator.enable_input_image
            )
            if enable_input_image:
                input_image = self.app.standard_image_panel.ui.input_image_widget.current_input_image
            elif self.generator_section == "txt2img":
                input_image = override_data.get("input_image", None)
                image = input_image
            image = input_image if not image else image
            override_data["input_image"] = image

            if self.is_upscale and image is None:
                image = self.app.current_active_image()
            
            if self.is_upscale and image is None:
                return

            if image is None:
                if self.is_txt2img:
                    return self.do_generate(seed=seed, override_data=override_data)
                # Create a transparent image the size of self.app.canvas_widget.active_grid_area_rect
                width = self.app.settings_manager.working_width
                height = self.app.settings_manager.working_height
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
                        self.app.settings_manager.working_width, 
                        self.app.settings_manager.working_height
                    ),
                    (255, 255, 255, 0)
                )

                # Get the cropped image
                cropped_outpaint_box_rect = self.active_rect
                # crop_location = (
                #     cropped_outpaint_box_rect.x() - self.app.canvas_widget.image_pivot_point.x(),
                #     cropped_outpaint_box_rect.y() - self.app.canvas_widget.image_pivot_point.y(),
                #     cropped_outpaint_box_rect.width() - self.app.canvas_widget.image_pivot_point.x(),
                #     cropped_outpaint_box_rect.height() - self.app.canvas_widget.image_pivot_point.y()
                # )
                crop_location = (
                    cropped_outpaint_box_rect.x() - self.app.canvas_widget.current_layer.pos_x,
                    cropped_outpaint_box_rect.y() - self.app.canvas_widget.current_layer.pos_y,
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
                "location": QRect(0, 0, self.app.settings_manager.working_width, self.app.settings_manager.working_height)
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

    def do_generate(self, extra_options=None, seed=None, latents_seed=None, do_deterministic=False, override_data=False):
        if not extra_options:
            extra_options = {}

        if self.enable_controlnet:
            extra_options["controlnet_image"] = self.ui.controlnet_settings.current_controlnet_image

        self.set_seed(seed=seed, latents_seed=latents_seed)

        if self.deterministic_data and do_deterministic:
            return self.do_deterministic_generation(extra_options)

        action = self.generator_section

        if not override_data:
            override_data = {}
        
        action = override_data.get("action", action)
        prompt = override_data.get("prompt", self.app.settings_manager.generator.prompt)
        negative_prompt = override_data.get("negative_prompt", self.app.settings_manager.generator.negative_prompt)
        steps = int(override_data.get("steps", self.app.settings_manager.generator.steps))
        strength = float(override_data.get("strength", self.app.settings_manager.generator.strength / 100.0))
        image_guidance_scale = float(override_data.get("image_guidance_scale", self.app.settings_manager.generator.image_guidance_scale / 10000.0 * 100.0))
        scale = float(override_data.get("scale", self.app.settings_manager.generator.scale / 100))
        seed = int(override_data.get("seed", self.app.settings_manager.generator.seed))
        latents_seed = int(override_data.get("latents_seed", self.app.settings_manager.generator.latents_seed))
        ddim_eta = float(override_data.get("ddim_eta", self.app.settings_manager.generator.ddim_eta))
        n_iter = int(override_data.get("n_iter", 1))
        n_samples = int(override_data.get("n_samples", self.app.settings_manager.generator.n_samples))
        # iterate over all keys in model_data
        model_data = {}
        for k,v in override_data.items():
            if k.startswith("model_data_"):
                model_data[k.replace("model_data_", "")] = v
        scheduler = override_data.get("scheduler", self.app.settings_manager.generator.scheduler)
        enable_controlnet = bool(override_data.get("enable_controlnet", self.app.settings_manager.generator.enable_controlnet))
        controlnet = override_data.get("controlnet", self.app.settings_manager.generator.controlnet)
        controlnet_conditioning_scale = float(override_data.get("controlnet_conditioning_scale", self.app.settings_manager.generator.controlnet_guidance_scale))
        width = int(override_data.get("width", self.app.settings_manager.settings.working_width))
        height = int(override_data.get("height", self.app.settings_manager.settings.working_height))
        clip_skip = int(override_data.get("clip_skip", self.app.settings_manager.generator.clip_skip))
        batch_size = int(override_data.get("batch_size", 1))


        # get the model from the database
        name = model_data["name"] if "name" in model_data else self.app.settings_manager.generator.model
        with self.app.settings_manager.model_by_name(name) as model:
            if model:
                # set the model data, first using model_data pulled from the override_data
                model_data = dict(
                    name=model_data.get("name", model.name),
                    path=model_data.get("path", model.path),
                    branch=model_data.get("branch", model.branch),
                    version=model_data.get("version", model.version),
                    category=model_data.get("category", model.category),
                    pipeline_action=model_data.get("pipeline_action", model.pipeline_action),
                    enabled=model_data.get("enabled", model.enabled),
                    default=model_data.get("default", model.is_default)
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
                nsfw_filter = self.app.nsfw_filter
                options = dict(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    steps=steps,
                    ddim_eta=ddim_eta,  # only applies to ddim scheduler
                    n_iter=n_iter,
                    n_samples=n_samples,
                    scale=scale,
                    seed=seed,
                    latents_seed=latents_seed,
                    model=model,
                    model_data=model_data,
                    original_model_data=original_model_data,
                    scheduler=scheduler,
                    model_path=model.path,
                    model_branch=model.branch,
                    # lora=self.available_lora(action),
                    generator_section=self.generator_section,
                    width=width,
                    height=height,
                    do_nsfw_filter=nsfw_filter,
                    pos_x=0,
                    pos_y=0,
                    outpaint_box_rect=self.active_rect,
                    hf_token=self.app.settings_manager.settings.hf_api_key,
                    model_base_path=self.app.settings_manager.path_settings.model_base_path,
                    outpaint_model_path=self.app.settings_manager.path_settings.outpaint_model_path,
                    pix2pix_model_path=self.app.settings_manager.path_settings.pix2pix_model_path,
                    depth2img_model_path=self.app.settings_manager.path_settings.depth2img_model_path,
                    upscale_model_path=self.app.settings_manager.path_settings.upscale_model_path,
                    image_path=self.app.settings_manager.path_settings.image_path,
                    lora_path=self.app.settings_manager.path_settings.lora_path,
                    embeddings_path=self.app.settings_manager.path_settings.embeddings_path,
                    video_path=self.app.settings_manager.path_settings.video_path,
                    clip_skip=clip_skip,
                    batch_size=batch_size,
                    variation=self.app.settings_manager.generator.variation,
                    deterministic_generation=False,
                    input_image=input_image,
                    enable_controlnet=enable_controlnet,
                    controlnet_conditioning_scale=controlnet_conditioning_scale,
                    controlnet=controlnet,
                    allow_online_mode=self.app.allow_online_mode,
                    hf_api_key_read_key=self.app.hf_api_key_read_key,
                    hf_api_key_write_key=self.app.hf_api_key_write_key,
                )

                if self.controlnet_image:
                    options["controlnet_image"] = self.controlnet_image

                if action == "superresolution":
                    options["original_image_width"] = self.app.canvas_widget.current_active_image_data.image.width
                    options["original_image_height"] = self.app.canvas_widget.current_active_image_data.image.height

                if action in ["txt2img", "img2img", "outpaint", "depth2img"]:
                    options[f"strength"] = strength
                elif action in ["pix2pix"]:
                    options[f"image_guidance_scale"] = image_guidance_scale

                """
                Emitting generate_signal with options allows us to pass more options to the dict from
                modal windows such as the image interpolation window.
                """
                self.app.generate_signal.emit(options)

                memory_options = self.get_memory_options()

                data = {
                    "action": action,
                    "options": {
                        **options,
                        **extra_options,
                        **memory_options
                    }
                }
                self.app.client.message = data

    def get_memory_options(self):
        return {
            "use_last_channels": self.app.settings_manager.memory_settings.use_last_channels,
            "use_enable_sequential_cpu_offload": self.app.settings_manager.memory_settings.use_enable_sequential_cpu_offload,
            "enable_model_cpu_offload": self.app.settings_manager.memory_settings.enable_model_cpu_offload,
            "use_attention_slicing": self.app.settings_manager.memory_settings.use_attention_slicing,
            "use_tf32": self.app.settings_manager.memory_settings.use_tf32,
            "use_cudnn_benchmark": self.app.settings_manager.memory_settings.use_cudnn_benchmark,
            "use_enable_vae_slicing": self.app.settings_manager.memory_settings.use_enable_vae_slicing,
            "use_accelerated_transformers": self.app.settings_manager.memory_settings.use_accelerated_transformers,
            "use_torch_compile": self.app.settings_manager.memory_settings.use_torch_compile,
            "use_tiled_vae": self.app.settings_manager.memory_settings.use_tiled_vae,
            "use_tome_sd": self.app.settings_manager.memory_settings.use_tome_sd,
            "tome_sd_ratio": self.app.settings_manager.memory_settings.tome_sd_ratio,
        }

    def set_seed(self, seed=None, latents_seed=None):
        """
        Set the seed - either set to random, deterministic or keep current, then display the seed in the UI.
        :return:
        """
        self.set_primary_seed(seed)
        self.set_latents_seed(latents_seed)
        self.update_seed()

    def update_seed(self):
        self.app.standard_image_panel.ui.seed_widget.update_seed()
        self.app.standard_image_panel.ui.seed_widget_latents.update_seed()

    def set_primary_seed(self, seed=None):
        if self.deterministic_data:
            self.seed = self.deterministic_data["options"][f"seed"]
        elif self.random_seed:
            self.seed = random.randint(0, MAX_SEED)
        elif seed is not None:
            self.seed = seed

    def set_latents_seed(self, latents_seed=None):
        if self.random_latents_seed:
            random.seed()
            latents_seed = random.randint(0, MAX_SEED)
        if latents_seed is not None:
            self.latents_seed = latents_seed

    def start_progress_bar(self):
        self.ui.progress_bar.setRange(0, 0)
        self.ui.progress_bar.show()
        # self.app.message_var.emit({
        #     "message": {
        #         "step": 0,
        #         "total": 0,
        #         "action": self.generator_section,
        #         "image": None,
        #         "data": None,
        #         "tab_section": self.generator_name,
        #     },
        #     "code": MessageCode.PROGRESS
        # })

    def handle_checkbox_change(self, key, widget_name):
        widget = getattr(self.ui, widget_name)
        value = widget.isChecked()
        setattr(self.generator_settings, key, value)
        self.save_db_session()
        self.changed_signal.emit(key, value)

    def initialize(self):
        self.set_form_values()
        self.initialized = True
        self.app.settings_manager.changed_signal.connect(self.handle_changed_signal)

    def handle_settings_manager_changed(self, key, val, settings_manager):
        print("generator_form_widget handle_settings_manager_changed")
        self.set_form_values()

    def clear_prompts(self):
        self.ui.prompt.setPlainText("")
        self.ui.negative_prompt.setPlainText("")

    def set_form_values(self):
        self.set_form_value("prompt", "generator.prompt")
        self.set_form_value("negative_prompt", "generator.negative_prompt")

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
    
    def set_progress_bar_value(self, tab_section, section, value):
        progressbar = self.ui.progress_bar
        if not progressbar:
            return
        if progressbar.maximum() == 0:
            progressbar.setRange(0, 100)
        progressbar.setValue(value)
    
    def stop_progress_bar(self):
        progressbar = self.ui.progress_bar
        if not progressbar:
            return
        progressbar.setRange(0, 100)
        progressbar.setValue(100)

    def update_prompt(self, prompt):
        self.ui.prompt.setPlainText(prompt)

    def update_negative_prompt(self, prompt):
        self.ui.negative_prompt.setPlainText(prompt)
    
    def handle_prompt_builder_button_toggled(self, val):
        self.app.toggle_prompt_builder(val)