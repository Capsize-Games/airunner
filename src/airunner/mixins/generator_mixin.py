import os
import random
from PIL import Image
from PyQt6 import uic
from PyQt6.QtCore import QRect, pyqtSignal, Qt, QPoint
from PyQt6.QtGui import QShortcut, QKeySequence
from PyQt6.uic.exceptions import UIFileException
from airunner.aihandler.settings import MAX_SEED
from airunner.aihandler.enums import MessageCode
from airunner.data.models import AIModel
from airunner.windows.video import VideoPopup
from airunner.mixins.lora_mixin import LoraMixin
from PIL import PngImagePlugin


class GeneratorMixin(LoraMixin):
    generate_signal = pyqtSignal(dict)
    deterministic_generation_window = None
    deterministic_images = []
    deterministic_data = None
    seed_override = None  # used when generating multiple samples

    @property
    def deterministic(self):
        return self.settings_manager.generator.deterministic

    @deterministic.setter
    def deterministic(self, val):
        self.settings_manager.set_value("generator.deterministic", val == True)

    @property
    def model_base_path(self):
        return self.settings_manager.path_settings.model_base_path

    @model_base_path.setter
    def model_base_path(self, val):
        self.settings_manager.set_value("model_base_path", val)

    @property
    def working_width(self):
        return int(self.settings_manager.working_width)

    @working_width.setter
    def working_width(self, val):
        self.settings_manager.set_value("working_width", val)
        self.set_final_size_label()
        self.canvas.update()

    @property
    def working_height(self):
        return int(self.settings_manager.working_height)

    @working_height.setter
    def working_height(self, val):
        self.settings_manager.set_value("working_height", val)
        self.set_final_size_label()
        self.canvas.update()

    @property
    def steps(self):
        return self.settings_manager.generator.steps

    @steps.setter
    def steps(self, val):
        self.settings_manager.set_value("generator.steps", val)

    @property
    def ddim_eta(self):
        return self.settings_manager.ddim_eta

    @ddim_eta.setter
    def ddim_eta(self, val):
        self.settings_manager.set_value("generator.ddim_eta", val)

    @property
    def prompt(self):
        return self.settings_manager.generator.prompt

    @prompt.setter
    def prompt(self, val):
        self.settings_manager.set_value("generator.prompt", val)

    @property
    def negative_prompt(self):
        return self.settings_manager.generator.negative_prompt

    @negative_prompt.setter
    def negative_prompt(self, val):
        self.settings_manager.set_value("generator.negative_prompt", val)

    @property
    def scale(self):
        return self.settings_manager.generator.scale

    @scale.setter
    def scale(self, val):
        self.settings_manager.set_value("generator.scale", val)

    @property
    def image_scale(self):
        return self.settings_manager.generator.image_guidance_scale

    @image_scale.setter
    def image_scale(self, val):
        self.settings_manager.set_value("generator.image_scale", val)

    @property
    def strength(self):
        return self.settings_manager.generator.strength

    @strength.setter
    def strength(self, val):
        self.settings_manager.set_value("generator.strength", val)

    @property
    def enable_controlnet(self):
        return self.settings_manager.generator.enable_controlnet

    @enable_controlnet.setter
    def enable_controlnet(self, val):
        self.settings_manager.set_value("generator.enable_controlnet", val)

    @property
    def controlnet(self):
        controlnet = self.settings_manager.generator.controlnet
        if controlnet == "":
            return None
        return controlnet

    @controlnet.setter
    def controlnet(self, val):
        self.settings_manager.set_value("generator.controlnet", val)

    @property
    def use_prompt_builder_checkbox(self):
        val = self.settings_manager.use_prompt_builder_checkbox
        return val == True or val == 2

    @use_prompt_builder_checkbox.setter
    def use_prompt_builder_checkbox(self, val):
        self.settings_manager.set_value("use_prompt_builder_checkbox", val == True or val == 2)

    @property
    def controlnet_guidance_scale(self):
        return self.settings_manager.generator.controlnet_guidance_scale

    @controlnet_guidance_scale.setter
    def controlnet_guidance_scale(self, val):
        self.settings_manager.set_value("generator.controlnet_scale", val)

    @property
    def variation(self):
        return self.settings_manager.generator.variation

    @variation.setter
    def variation(self, val):
        self.settings_manager.set_value("generator.variation", val)

    @property
    def seed(self):
        return self.settings_manager.generator.seed

    @seed.setter
    def seed(self, val):
        self.settings_manager.set_value("generator.seed", val)

    @property
    def random_seed(self):
        return self.settings_manager.generator.random_seed

    @random_seed.setter
    def random_seed(self, val):
        self.settings_manager.set_value("generator.random_seed", val)

    @property
    def latents_seed(self):
        return self.settings_manager.generator.latents_seed

    @latents_seed.setter
    def latents_seed(self, val):
        self.settings_manager.set_value("generator.latents_seed", val)

    @property
    def random_latents_seed(self):
        return self.settings_manager.generator.random_latents_seed

    @random_latents_seed.setter
    def random_latents_seed(self, val):
        self.settings_manager.set_value("generator.random_latents_seed", val)

    @property
    def clip_skip(self):
        return self.settings_manager.generator.clip_skip

    @clip_skip.setter
    def clip_skip(self, val):
        self.settings_manager.set_value("generator.clip_skip", val)

    @property
    def samples(self):
        return self.settings_manager.generator.n_samples

    @samples.setter
    def samples(self, val):
        self.settings_manager.set_value("generator.n_samples", val)

    @property
    def model(self):
        return self.settings_manager.generator.model

    @model.setter
    def model(self, val):
        self.settings_manager.set_value("generator.model", val)

    @property
    def scheduler(self):
        return self.settings_manager.generator.scheduler

    @scheduler.setter
    def scheduler(self, val):
        self.settings_manager.set_value("generator.scheduler", val)

    def update_prompt(self, prompt):
        self.generator_tab_widget.set_prompt(prompt)

    def update_negative_prompt(self, prompt):
        self.generator_tab_widget.set_negative_prompt(prompt)

    def initialize(self):
        # self.tool_menu_widget.initialize()
        self.initialize_lora()

        self.input_event_manager.register_keypress("generate", self.generate_callback)

    def update_controlnet(self, tab, index):
        controlnet = self.tabs[tab].controlnet_dropdown.itemText(index)
        controlnet = controlnet.lower()
        if controlnet == "":
            controlnet = None
        self.settings_manager.set_value("generator.controlnet", controlnet)

    def set_final_size_label(self, tab=None):
        if tab is None:
            tab = self.tabs[self.current_section]

        """
        Early return to hack aronud final size for now
        """
        return

        image = self.canvas.current_layer.image_data.image
        if image:
            if self.do_upscale_by_active_grid:
                width = self.settings_manager.working_width
                height = self.settings_manager.working_height
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
        self.client.cancel()

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

    def generate_callback(self):
        self.generate()

    def generate_deterministic_callback(self):
        self.deterministic = True
        self.generate()
        self.deterministic = False

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

    @property
    def deterministic_seed(self):
        if not self._deterministic_seed:
            self._deterministic_seed = self.seed
        return self._deterministic_seed

    @deterministic_seed.setter
    def deterministic_seed(self, val):
        self._deterministic_seed = val

    def new_batch(self, index, image, data):
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

    def generate(self, image=None, seed=None):
        if seed is None:
            seed = self.seed
        if self.samples > 1:
            self.client.do_process_queue = False
        total_samples = self.samples if not self.is_txt2vid else 1
        for n in range(total_samples):
            if self.use_prompt_builder_checkbox and n > 0:
                seed = int(seed) + n
            self.call_generate(image, seed=seed)
        self.seed_override = None
        self.client.do_process_queue = True

    def call_generate(self, image=None, seed=None):
        if self.current_section in ("upscale", "superresolution") and self.do_upscale_full_image:
            image_data = self.canvas.current_layer.image_data
            if image_data:
                location = image_data.position
            else:
                location = QPoint(0, 0)
            image = self.generator_tab_widget.current_input_image
            if image is None:
                self.message_var.emit({
                    "code": MessageCode.ERROR,
                    "message": "No image to upscale",
                })
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
            self.start_progress_bar()
            self.do_generate({
                "mask": image.convert("RGB"),
                "image": image.convert("RGB"),
                "location": location
            }, seed=seed)
        elif self.use_pixels:
            self.requested_image = image
            self.start_progress_bar()
            image = self.generator_tab_widget.current_input_image

            if image is None and self.action == "txt2img":
                return self.do_generate(seed=seed)
            elif image is None:
                # create a transparent image the size of self.canvas.active_grid_area_rect
                width = self.settings_manager.working_width
                height = self.settings_manager.working_height
                image = Image.new("RGBA", (int(width), int(height)), (0, 0, 0, 0))

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
            }, seed=seed)
        elif self.action == "vid2vid":
            images = self.prep_video()
            self.do_generate({
                "images": images
            }, seed=seed)
        else:
            self.do_generate(seed=seed)

    def start_progress_bar(self):
        # progressBar: QProgressBar = self.tabs[section].progressBar
        # progressBar.setRange(0, 0)
        self.generator_tab_widget.start_progress_bar(
            self.current_generator, self.current_section)

    def set_seed(self, seed=None, latents_seed=None):
        """
        Set the seed - either set to random, deterministic or keep current, then display the seed in the UI.
        :return:
        """
        self.set_primary_seed(seed)
        self.set_latents_seed(latents_seed)
        self.generator_tab_widget.update_seed()

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
                "batch_size": self.tool_menu_widget.deterministic_widget.batch_size,
                "deterministic_generation": True,
                "deterministic_seed": self.deterministic_seed,
                "deterministic_style": self.tool_menu_widget.deterministic_widget.deterministic_style
            }
        }
        self.client.message = data

    def do_generate(self, extra_options=None, seed=None, latents_seed=None):
        if not extra_options:
            extra_options = {}

        if self.enable_controlnet:
            extra_options["input_image"] = self.generator_tab_widget.current_controlnet_input_image

        self.set_seed(seed=seed, latents_seed=latents_seed)
        seed = self.seed
        latents_seed = self.latents_seed

        if self.deterministic_data and self.deterministic:
            return self.do_deterministic_generation(extra_options)

        action = self.current_section

        prompt = self.prompt
        negative_prompt = self.negative_prompt

        # set the model data
        model = self.settings_manager.models.filter_by(name=self.model).first()
        model_path = model.path
        model_branch = model.branch
        model_data = {
            "name": model.name,
            "path": model.path,
            "branch": model.branch,
            "version": model.version,
            "category": model.category,
            "pipeline_action": model.pipeline_action,
            "enabled": model.enabled,
            "default": model.default
        }

        # get controlnet_dropdown from active tab
        options = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "steps": self.steps,
            "ddim_eta": self.ddim_eta,  # only applies to ddim scheduler
            "n_iter": 1,
            "n_samples": self.samples,
            "scale": self.scale / 100,
            "seed": seed,
            "latents_seed": latents_seed,
            "model": self.model,
            "model_data": model_data,
            "scheduler": self.scheduler,
            "model_path": model_path,
            "model_branch": model_branch,
            "lora": self.available_lora(action),
            "controlnet_conditioning_scale": self.controlnet_guidance_scale,
            "generator_section": self.current_generator,
            "width": self.working_width,
            "height": self.working_height,
            "do_nsfw_filter": self.settings_manager.nsfw_filter,
            "pos_x": 0,
            "pos_y": 0,
            "outpaint_box_rect": self.active_rect,
            "hf_token": self.settings_manager.hf_api_key,
            "batch_size": self.tool_menu_widget.deterministic_widget.batch_size if self.deterministic else 1,
            "deterministic_generation": self.deterministic,
            "deterministic_style": self.tool_menu_widget.deterministic_widget.deterministic_style,
            "deterministic_seed": None,
            "model_base_path": self.model_base_path,
            "outpaint_model_path": self.settings_manager.path_settings.outpaint_model_path,
            "pix2pix_model_path": self.settings_manager.path_settings.pix2pix_model_path,
            "depth2img_model_path": self.settings_manager.path_settings.depth2img_model_path,
            "upscale_model_path": self.settings_manager.path_settings.upscale_model_path,
            "gif_path": self.settings_manager.path_settings.gif_path,
            "image_path": self.settings_manager.path_settings.image_path,
            "lora_path": self.settings_manager.lora_path,
            "embeddings_path": self.settings_manager.path_settings.embeddings_path,
            "video_path": self.settings_manager.path_settings.video_path,
            "clip_skip": self.clip_skip,
            "variation": self.variation
        }

        options["enable_controlnet"] = self.enable_controlnet
        options["controlnet"] = self.controlnet

        if self.generator_tab_widget.controlnet_image:
            options["controlnet_image"] = self.generator_tab_widget.controlnet_image

        if action == "superresolution":
            options["original_image_width"] = self.canvas.current_active_image_data.image.width
            options["original_image_height"] = self.canvas.current_active_image_data.image.height

        if action in ["txt2img", "img2img", "outpaint", "depth2img"]:
            options[f"strength"] = self.strength / 10000.0
        elif action in ["pix2pix"]:
            options[f"image_guidance_scale"] = self.image_scale / 10000.0 * 100.0

        """
        Emitting generate_signal with options allows us to pass more options to the dict from
        modal windows such as the image interpolation window.
        """
        self.generate_signal.emit(options)

        memory_options = self.get_memory_options()

        data = {
            "action": action,
            "options": {
                **options,
                **extra_options,
                **memory_options
            }
        }
        self.client.message = data

    def tab_changed_callback(self, index):
        self.set_final_size_label()
        self.canvas.update()

    def load_template(self, template_name):
        try:
            return uic.loadUi(
                os.path.join("pyqt", f"{template_name}.ui"))
        except UIFileException:
            return None

    def clear_status_message(self):
        self.message_var.set("")
