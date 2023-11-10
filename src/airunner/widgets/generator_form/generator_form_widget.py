import random

from PIL import Image
from PyQt6.QtCore import pyqtSignal, QRect, QTimer

from airunner.aihandler.enums import MessageCode
from airunner.aihandler.settings import MAX_SEED
from airunner.data.db import session
from airunner.data.models import ActionScheduler, AIModel, ActiveGridSettings, CanvasSettings
from airunner.utils import get_session
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.generator_form.templates.generatorform_ui import Ui_generator_form
from airunner.widgets.slider.slider_widget import SliderWidget


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
        try:
            return self.property("generator_section")
        except Exception as e:
            print(e)
            return None

    @property
    def generator_name(self):
        try:
            return self.property("generator_name")
        except Exception as e:
            print(e)
            return None

    @property
    def generator_settings(self):
        return self.settings_manager.find_generator(
            self.generator_section,
            self.generator_name
        )

    @property
    def random_seed(self):
        return self.settings_manager.generator.random_seed

    @property
    def random_latents_seed(self):
        return self.settings_manager.generator.random_latents_seed

    @property
    def latents_seed(self):
        return self.settings_manager.generator.latents_seed

    @latents_seed.setter
    def latents_seed(self, val):
        self.settings_manager.set_value("generator.latents_seed", val)

    @property
    def seed(self):
        return self.settings_manager.generator.seed

    @seed.setter
    def seed(self, val):
        self.settings_manager.set_value("generator.seed", val)

    @property
    def image_scale(self):
        return self.settings_manager.generator.image_guidance_scale

    @property
    def active_rect(self):
        rect = QRect(
            self.active_grid_settings.pos_x,
            self.active_grid_settings.pos_y,
            self.active_grid_settings.width,
            self.active_grid_settings.height
        )
        rect.translate(-self.canvas_settings.pos_x, -self.canvas_settings.pos_y)

        return rect

    @property
    def enable_controlnet(self):
        return self.settings_manager.generator.enable_controlnet

    @property
    def controlnet_image(self):
        return self.ui.controlnet_settings.current_controlnet_image

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_grid_settings = session.query(ActiveGridSettings).first()
        self.canvas_settings = session.query(CanvasSettings).first()
        self.ui.generator_form_tab_widget.tabBar().hide()
        # one shot timer
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(self.initialize)
        timer.start(1000)

    def update_image_input_thumbnail(self):
        self.ui.input_image_widget.set_thumbnail()

    def update_controlnet_settings_thumbnail(self):
        self.ui.controlnet_settings.set_thumbnail()

    """
    Slot functions

    The following functions are defined in and connected to the appropriate
    signals in the corresponding ui file.
    """
    def action_clicked_button_save_prompts(self):
        self.settings_manager.create_saved_prompt(
            self.settings_manager.generator.prompt,
            self.settings_manager.generator.negative_prompt
        )

    def handle_prompt_changed(self):
        if not self.initialized:
            return
        self.settings_manager.set_value("generator.prompt", self.ui.prompt.toPlainText())

    def handle_negative_prompt_changed(self):
        if not self.initialized:
            return
        self.settings_manager.set_value("generator.negative_prompt", self.ui.negative_prompt.toPlainText())

    def toggle_prompt_builder_checkbox(self, toggled):
        pass

    def handle_model_changed(self, name):
        if not self.initialized:
            return
        self.settings_manager.set_value("generator.model", name)
        self.changed_signal.emit("generator.model", name)

    def handle_scheduler_changed(self, name):
        if not self.initialized:
            return
        self.settings_manager.set_value("generator.scheduler", name)
        self.changed_signal.emit("generator.scheduler", name)

    def toggle_variation(self, toggled):
        pass

    def handle_generate_button_clicked(self):
        self.start_progress_bar()
        self.generate()

    def handle_interrupt_button_clicked(self):
        self.app.client.cancel()
    """
    End Slot functions
    """

    def generate(self, image=None, seed=None):
        if seed is None:
            seed = self.ui.seed_widget.seed
        if self.ui.samples_widget.current_value > 1:
            self.app.client.do_process_queue = False
        total_samples = self.ui.samples_widget.current_value if not self.is_txt2vid else 1
        for n in range(total_samples):
            if self.settings_manager.generator.use_prompt_builder and n > 0:
                seed = int(seed) + n
            self.call_generate(image, seed=seed)
        self.seed_override = None
        self.app.client.do_process_queue = True

    def call_generate(self, image=None, seed=None, override_data=None):
        use_pixels = self.generator_section in (
            "txt2img",
            "pix2pix",
            "depth2img",
            "outpaint",
            "controlnet",
            "superresolution",
            "upscale"
        )
        override_data = {} if override_data is None else override_data

        if use_pixels:
            self.start_progress_bar()

            # get input image from input image
            enable_input_image = override_data.get(
                "enable_input_image",
                self.settings_manager.generator.enable_input_image
            )
            if enable_input_image:
                input_image = self.ui.input_image_widget.current_input_image
                image = input_image if not image else image
                override_data["input_image"] = image

            if image is None and self.is_txt2img:
                return self.do_generate(seed=seed, override_data=override_data)
            elif image is None:
                # create a transparent image the size of self.canvas.active_grid_area_rect
                width = self.settings_manager.working_width
                height = self.settings_manager.working_height
                image = Image.new("RGBA", (int(width), int(height)), (0, 0, 0, 0))
            
            use_cropped_image = override_data.get("use_cropped_image", True)
            if use_cropped_image:
                img = image.copy().convert("RGBA")
                new_image = Image.new(
                    "RGBA",
                    (self.settings_manager.working_width, self.settings_manager.working_height),
                    (0, 0, 0))

                cropped_outpaint_box_rect = self.active_rect
                crop_location = (
                    cropped_outpaint_box_rect.x() - self.canvas.image_pivot_point.x(),
                    cropped_outpaint_box_rect.y() - self.canvas.image_pivot_point.y(),
                    cropped_outpaint_box_rect.width() - self.canvas.image_pivot_point.x(),
                    cropped_outpaint_box_rect.height() - self.canvas.image_pivot_point.y()
                )
                new_image.paste(img.crop(crop_location), (0, 0))

                image = new_image.convert("RGB")
            
            # create the mask
            mask = Image.new("RGB", (image.width, image.height), (255, 255, 255))
            for x in range(image.width):
                for y in range(image.height):
                    try:
                        if image.getpixel((x, y))[3] != 0:
                            mask.putpixel((x, y), (0, 0, 0))
                    except IndexError:
                        pass

            self.do_generate({
                "mask": mask,
                "image": image,
                "location": self.canvas.active_grid_area_rect
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
        
        print("strength", override_data.get("strength"), self.settings_manager.generator.strength)
        
        action = override_data.get("action", action)
        prompt = override_data.get("prompt", self.settings_manager.generator.prompt)
        negative_prompt = override_data.get("negative_prompt", self.settings_manager.generator.negative_prompt)
        steps = int(override_data.get("steps", self.settings_manager.generator.steps))
        strength = float(override_data.get("strength", self.settings_manager.generator.strength / 100.0))
        image_guidance_scale = float(override_data.get("image_guidance_scale", self.settings_manager.generator.image_guidance_scale / 10000.0 * 100.0))
        scale = float(override_data.get("scale", self.settings_manager.generator.scale / 100))
        seed = int(override_data.get("seed", self.settings_manager.generator.seed))
        latents_seed = int(override_data.get("latents_seed", self.settings_manager.generator.latents_seed))
        ddim_eta = float(override_data.get("ddim_eta", self.settings_manager.generator.ddim_eta))
        n_iter = int(override_data.get("n_iter", 1))
        n_samples = int(override_data.get("n_samples", self.settings_manager.generator.n_samples))
        # iterate over all keys in model_data
        model_data = {}
        for k,v in override_data.items():
            if k.startswith("model_data_"):
                model_data[k.replace("model_data_", "")] = v
        scheduler = override_data.get("scheduler", self.settings_manager.generator.scheduler)
        enable_controlnet = bool(override_data.get("enable_controlnet", self.settings_manager.generator.enable_controlnet))
        controlnet = override_data.get("controlnet", self.settings_manager.generator.controlnet)
        controlnet_conditioning_scale = float(override_data.get("controlnet_conditioning_scale", self.settings_manager.generator.controlnet_guidance_scale))
        width = int(override_data.get("width", self.settings_manager.working_width))
        height = int(override_data.get("height", self.settings_manager.working_height))
        clip_skip = int(override_data.get("clip_skip", self.settings_manager.generator.clip_skip))

        # get the model from the database
        model = self.settings_manager.models.filter_by(
            name=model_data["name"] if "name" in model_data \
                else self.settings_manager.generator.model
        ).first()

        # set the model data, first using model_data pulled from the override_data
        model_data = {
            "name": model_data.get("name", model.name),
            "path": model_data.get("path", model.path),
            "branch": model_data.get("branch", model.branch),
            "version": model_data.get("version", model.version),
            "category": model_data.get("category", model.category),
            "pipeline_action": model_data.get("pipeline_action", model.pipeline_action),
            "enabled": model_data.get("enabled", model.enabled),
            "default": model_data.get("default", model.is_default)
        }

        # get controlnet_dropdown from active tab
        options = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "steps": steps,
            "ddim_eta": ddim_eta,  # only applies to ddim scheduler
            "n_iter": n_iter,
            "n_samples": n_samples,
            "scale": scale,
            "seed": seed,
            "latents_seed": latents_seed,
            "model": model,
            "model_data": model_data,
            "scheduler": scheduler,
            "model_path": model.path,
            "model_branch": model.branch,
            # "lora": self.available_lora(action),
            "controlnet_conditioning_scale": controlnet_conditioning_scale,
            "generator_section": self.generator_section,
            "width": width,
            "height": height,
            "do_nsfw_filter": self.settings_manager.nsfw_filter,
            "pos_x": 0,
            "pos_y": 0,
            "outpaint_box_rect": self.active_rect,
            "hf_token": self.settings_manager.hf_api_key,
            "model_base_path": self.settings_manager.path_settings.model_base_path,
            "outpaint_model_path": self.settings_manager.path_settings.outpaint_model_path,
            "pix2pix_model_path": self.settings_manager.path_settings.pix2pix_model_path,
            "depth2img_model_path": self.settings_manager.path_settings.depth2img_model_path,
            "upscale_model_path": self.settings_manager.path_settings.upscale_model_path,
            "gif_path": self.settings_manager.path_settings.gif_path,
            "image_path": self.settings_manager.path_settings.image_path,
            "lora_path": self.settings_manager.lora_path,
            "embeddings_path": self.settings_manager.path_settings.embeddings_path,
            "video_path": self.settings_manager.path_settings.video_path,
            "clip_skip": clip_skip,
            "variation": self.settings_manager.generator.variation,
            "deterministic_generation": False,
        }

        options["input_image"] = override_data.get("input_image", None)
        
        options["enable_controlnet"] = enable_controlnet
        options["controlnet"] = controlnet

        if self.controlnet_image:
            options["controlnet_image"] = self.controlnet_image

        if action == "superresolution":
            options["original_image_width"] = self.canvas.current_active_image_data.image.width
            options["original_image_height"] = self.canvas.current_active_image_data.image.height

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
        print(data)
        self.app.client.message = data

    def do_deterministic_generation(self, extra_options):
        action = self.deterministic_data["action"]
        options = self.deterministic_data["options"]
        options[f"prompt"] = self.deterministic_data[f"prompt"][self.deterministic_index]
        memory_options = self.get_memory_options()
        data = {
            "action": action,
            "options": {
                **options,
                **extra_options,
                **memory_options,
                "batch_size": self.settings_manager.deterministic_settings.batch_size,
                "deterministic_generation": True,
                "deterministic_seed": self.settings_manager.deterministic_settings.seed,
                "deterministic_style": self.settings_manager.deterministic_settings.style,
            }
        }
        self.app.client.message = data

    def get_memory_options(self):
        return {
            "use_last_channels": self.settings_manager.memory_settings.use_last_channels,
            "use_enable_sequential_cpu_offload": self.settings_manager.memory_settings.use_enable_sequential_cpu_offload,
            "enable_model_cpu_offload": self.settings_manager.memory_settings.enable_model_cpu_offload,
            "use_attention_slicing": self.settings_manager.memory_settings.use_attention_slicing,
            "use_tf32": self.settings_manager.memory_settings.use_tf32,
            "use_cudnn_benchmark": self.settings_manager.memory_settings.use_cudnn_benchmark,
            "use_enable_vae_slicing": self.settings_manager.memory_settings.use_enable_vae_slicing,
            "use_accelerated_transformers": self.settings_manager.memory_settings.use_accelerated_transformers,
            "use_torch_compile": self.settings_manager.memory_settings.use_torch_compile,
            "use_tiled_vae": self.settings_manager.memory_settings.use_tiled_vae,
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
        self.ui.seed_widget.update_seed()
        self.ui.seed_widget_latents.update_seed()

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

    def save_db_session(self):
        from airunner.utils import save_session
        save_session()

    def handle_checkbox_change(self, key, widget_name):
        widget = getattr(self.ui, widget_name)
        value = widget.isChecked()
        setattr(self.generator_settings, key, value)
        self.save_db_session()
        self.changed_signal.emit(key, value)

    def initialize(self):
        self.settings_manager.generator_section = self.generator_section
        self.settings_manager.generator_name = self.generator_name
        self.set_form_values()
        self.load_models()
        self.load_schedulers()
        self.set_controlnet_settings_properties()
        self.set_input_image_widget_properties()

        # listen to emitted signal from self.settings_manager.changed_signal
        self.settings_manager.changed_signal.connect(self.handle_settings_manager_changed)

        # find all SliderWidget widgets in the template and call initialize
        for widget in self.findChildren(SliderWidget):
            try:
                current_value = getattr(
                    self.generator_settings,
                    widget.property("settings_property").split(".")[1]
                )
            except Exception as e:
                current_value = None
            if current_value is not None:
                widget.setProperty("current_value", current_value)
            widget.initialize()

        self.ui.seed_widget.setProperty("generator_section", self.generator_section)
        self.ui.seed_widget.setProperty("generator_name", self.generator_name)
        # self.ui.seed_widget.initialize(
        #     self.generator_section,
        #     self.generator_name
        # )

        self.ui.seed_widget_latents.setProperty("generator_section", self.generator_section)
        self.ui.seed_widget_latents.setProperty("generator_name", self.generator_name)
        # self.ui.seed_widget_latents.initialize(
        #     self.generator_section,
        #     self.generator_name
        # )
        self.initialized = True

    def handle_settings_manager_changed(self, key, val, settings_manager):
        if settings_manager.generator_section == self.settings_manager.generator_section and settings_manager.generator_name == self.settings_manager.generator_name:
            self.set_form_values()

    def set_controlnet_settings_properties(self):
        self.ui.controlnet_settings.initialize(
            self.generator_name,
            self.generator_section
        )

    def set_input_image_widget_properties(self):
        self.ui.input_image_widget.initialize(
            self.generator_name,
            self.generator_section
        )
        self.ui.controlnet_settings.initialize(
            self.generator_name,
            self.generator_section
        )

    def clear_prompts(self):
        self.ui.prompt.setPlainText("")
        self.ui.negative_prompt.setPlainText("")

    def load_models(self):
        self.ui.model.blockSignals(True)
        self.clear_models()

        models = session.query(AIModel).filter(
            AIModel.category == self.generator_name,
            AIModel.pipeline_action == self.generator_section
        ).all()
        model_names = [model.name for model in models]

        self.ui.model.addItems(model_names)
        current_model = self.settings_manager.generator.model
        if current_model != "":
            self.ui.model.setCurrentText(current_model)
        else:
            self.settings_manager.set_value("generator.model", self.ui.model.currentText())
        self.ui.model.blockSignals(False)

    def load_schedulers(self):
        self.ui.scheduler.blockSignals(True)
        session = get_session()
        schedulers = session.query(ActionScheduler).filter(
            ActionScheduler.section == self.generator_section,
            ActionScheduler.generator_name == self.generator_name
        ).all()
        scheduler_names = [s.scheduler.display_name for s in schedulers]
        self.ui.scheduler.addItems(scheduler_names)

        current_scheduler = self.settings_manager.generator.scheduler
        if current_scheduler != "":
            self.ui.scheduler.setCurrentText(current_scheduler)
        else:
            self.settings_manager.set_value("generator.scheduler", self.ui.scheduler.currentText())
        self.ui.scheduler.blockSignals(False)

    def set_form_values(self):
        self.set_form_value("prompt", "generator.prompt")
        self.set_form_value("negative_prompt", "generator.negative_prompt")
        self.set_form_value("use_prompt_builder_checkbox", "generator.use_prompt_builder")
        self.set_form_value("use_prompt_builder_checkbox", "generator.use_prompt_builder")
        self.set_form_property("steps_widget", "current_value", "generator.steps")
        self.set_form_property("scale_widget", "current_value", "generator.scale")

    def clear_models(self):
        self.ui.model.clear()

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
