import os
import random
from PIL import Image
from PyQt6 import uic
from PyQt6.QtCore import QRect, pyqtSignal, Qt
from PyQt6.QtGui import QShortcut, QKeySequence
from PyQt6.uic.exceptions import UIFileException
from aihandler.settings import MAX_SEED, MODELS, MessageCode
from airunner.windows.video import VideoPopup
from airunner.mixins.lora_mixin import LoraMixin
from PIL import PngImagePlugin


class GeneratorMixin(LoraMixin):
    generate_signal = pyqtSignal(dict)
    deterministic_generation_window = None
    deterministic_images = []
    deterministic_data = None

    @property
    def deterministic_var(self):
        return self.settings.deterministic

    @property
    def deterministic(self):
        return self.deterministic_var.get()

    @deterministic.setter
    def deterministic(self, val):
        self.deterministic_var.set(val == True)

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
    def working_width(self):
        return int(self.settings_manager.settings.working_width.get())

    @working_width.setter
    def working_width(self, val):
        self.settings_manager.settings.working_width.set(val)
        self.set_final_size_label()
        self.canvas.update()

    @property
    def working_height(self):
        return int(self.settings_manager.settings.working_height.get())

    @working_height.setter
    def working_height(self, val):
        self.settings_manager.settings.working_height.set(val)
        self.set_final_size_label()
        self.canvas.update()

    @property
    def steps_var(self):
        return self.settings.steps

    @property
    def steps(self):
        return self.steps_var.get()

    @steps.setter
    def steps(self, val):
        self.steps_var.set(val)

    @property
    def ddim_eta(self):
        return self.settings.ddim_eta.get()

    @ddim_eta.setter
    def ddim_eta(self, val):
        self.settings.ddim_eta.set(val)

    @property
    def prompt_var(self):
        return self.settings.prompt

    @property
    def prompt(self):
        return self.prompt_var.get()

    @prompt.setter
    def prompt(self, val):
        self.prompt_var.set(val)

    @property
    def negative_prompt_var(self):
        return self.settings.negative_prompt

    @property
    def negative_prompt(self):
        return self.negative_prompt_var.get()

    @negative_prompt.setter
    def negative_prompt(self, val):
        self.negative_prompt_var.set(val)

    @property
    def scale_var(self):
        return self.settings.scale

    @property
    def scale(self):
        return self.scale_var.get()

    @scale.setter
    def scale(self, val):
        self.scale_var.set(val)

    @property
    def image_scale_var(self):
        return self.settings.image_guidance_scale

    @property
    def image_scale(self):
        return self.image_scale_var.get()

    @image_scale.setter
    def image_scale(self, val):
        self.image_scale_var.set(val)

    @property
    def strength_var(self):
        return self.settings.strength

    @property
    def strength(self):
        return self.strength_var.get()

    @strength.setter
    def strength(self, val):
        self.strength_var.set(val)

    @property
    def zeroshot_var(self):
        return self.settings.zeroshot

    @property
    def zeroshot(self):
        return self.zeroshot_var.get()

    @zeroshot.setter
    def zeroshot(self, val):
        self.zeroshot_var.set(val)

    @property
    def enable_controlnet_var(self):
        return self.settings.enable_controlnet

    @property
    def enable_controlnet(self):
        return self.enable_controlnet_var.get()

    @enable_controlnet.setter
    def enable_controlnet(self, val):
        self.enable_controlnet_var.set(val)

    @property
    def controlnet_var(self):
        return self.settings.controlnet_var

    @property
    def controlnet(self):
        controlnet = self.controlnet_var.get()
        if controlnet == "":
            return None
        return controlnet

    @controlnet.setter
    def controlnet(self, val):
        self.controlnet_var.set(val)

    @property
    def use_prompt_builder_checkbox_var(self):
        return self.settings.use_prompt_builder_checkbox

    @property
    def use_prompt_builder_checkbox(self):
        val = self.use_prompt_builder_checkbox_var.get()
        return val == 2 or val == True

    @use_prompt_builder_checkbox.setter
    def use_prompt_builder_checkbox(self, val):
        self.use_prompt_builder_checkbox_var.set(val == True or val == 2)

    @property
    def controlnet_scale_var(self):
        return self.settings.controlnet_guidance_scale

    @property
    def controlnet_guidance_scale(self):
        return self.controlnet_scale_var.get()

    @controlnet_guidance_scale.setter
    def controlnet_guidance_scale(self, val):
        self.controlnet_scale_var.set(val)

    @property
    def seed_var(self):
        return self.settings.seed

    @property
    def seed(self):
        return self.seed_var.get()

    @seed.setter
    def seed(self, val):
        self.seed_var.set(val)

    @property
    def random_seed_var(self):
        return self.settings.random_seed

    @property
    def random_seed(self):
        return self.random_seed_var.get()

    @random_seed.setter
    def random_seed(self, val):
        self.random_seed_var.set(val)

    @property
    def samples_var(self):
        return self.settings.n_samples

    @property
    def samples(self):
        return self.samples_var.get()

    @samples.setter
    def samples(self, val):
        self.samples_var.set(val)

    @property
    def model_var(self):
        return self.settings.model_var

    @property
    def model(self):
        return self.model_var.get()

    @model.setter
    def model(self, val):
        self.model_var.set(val)

    @property
    def scheduler_var(self):
        return self.settings.scheduler_var

    @property
    def scheduler(self):
        return self.scheduler_var.get()

    @scheduler.setter
    def scheduler(self, val):
        self.scheduler_var.set(val)

    @property
    def downscale_amount_var(self):
        return self.settings.downscale_amount

    @property
    def downscale_amount(self):
        return self.downscale_amount_var.get()

    @downscale_amount.setter
    def downscale_amount(self, val):
        self.downscale_amount_var.set(val)

    @property
    def do_upscale_by_active_grid_var(self):
        return self.settings.do_upscale_by_active_grid

    @property
    def do_upscale_by_active_grid(self):
        return self.do_upscale_by_active_grid_var.get()

    @do_upscale_by_active_grid.setter
    def do_upscale_by_active_grid(self, val):
        self.do_upscale_by_active_grid_var.set(val)

    @property
    def do_upscale_full_image_var(self):
        return self.settings.do_upscale_full_image

    @property
    def do_upscale_full_image(self):
        return self.do_upscale_full_image_var.get()

    @do_upscale_full_image.setter
    def do_upscale_full_image(self, val):
        self.do_upscale_full_image_var.set(val)

    @property
    def image_to_new_layer(self):
        return self.settings_manager.settings.image_to_new_layer.get()

    def update_prompt(self, prompt):
        self.generator_tab_widget.set_prompt(prompt)

    def update_negative_prompt(self, prompt):
        self.generator_tab_widget.set_negative_prompt(prompt)

    def initialize(self):
        self.tool_menu_widget.initialize()
        self.initialize_lora()

        # listen to F5 keypress and call self.generate_callback
        self.generate_shortcut = QShortcut(QKeySequence(Qt.Key.Key_F5), self)
        self.generate_shortcut.activated.connect(self.generate_callback)

    def update_controlnet(self, tab, index):
        controlnet = self.tabs[tab].controlnet_dropdown.itemText(index)
        controlnet = controlnet.lower()
        if controlnet == "":
            controlnet = None
        self.settings.controlnet_var.set(controlnet)

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

    def generate_callback(self):
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

    def new_batch(self, index, image, data):
        """
        Generate a batch of images using deterministic geneartion based on a previous deterministic generation
        batch. The previous seed that was chosen should be re-used with the index added to it to generate the new
        batch of images.
        :return:
        """
        action = data["action"]
        if not data["options"]["deterministic_seed"]:
            data["options"][f"{action}_seed"] = data["options"][f"{action}_seed"] + index
        self.deterministic_data = data
        self.deterministic_index = index
        self.generate(image)
        self.deterministic_data = None
        self.deterministic_images = None

    def generate(self, image=None):
        if self.current_section in ("upscale", "superresolution") and self.do_upscale_full_image:
            image_data = self.canvas.current_layer.image_data
            image = image_data.image if image_data else None
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
                "location": image_data.position
            })
        elif self.use_pixels:
            self.requested_image = image
            self.start_progress_bar()
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

    def start_progress_bar(self):
        # progressBar: QProgressBar = self.tabs[section].progressBar
        # progressBar.setRange(0, 0)
        self.generator_tab_widget.start_progress_bar(
            self.currentTabSection, self.current_section)

    def set_seed(self):
        """
        Set the seed - either set to random, deterministic or keep current, then display the seed in the UI.
        :return:
        """
        if self.deterministic_data:
            action = self.deterministic_data["action"]
            self.seed = self.deterministic_data["options"][f"{action}_seed"]
        elif self.random_seed:
            seed = random.randint(0, MAX_SEED)
            self.seed = seed
        self.generator_tab_widget.data[self.currentTabSection][self.current_section]["seed"].setText(str(self.seed))

    def get_memory_options(self):
        return {
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

    def do_deterministic_generation(self, extra_options):
        action = self.deterministic_data["action"]
        options = self.deterministic_data["options"]
        options[f"{action}_prompt"] = self.deterministic_data[f"{action}_prompt"][self.deterministic_index]
        memory_options = self.get_memory_options()
        data = {
            "action": action,
            "options": {
                **options,
                **extra_options,
                **memory_options,
                "deterministic_generation": True,
                "deterministic_seed": True,
            }
        }
        self.client.message = data

    def do_generate(self, extra_options=None):
        if not extra_options:
            extra_options = {}

        self.set_seed()

        if self.deterministic_data and self.deterministic:
            return self.do_deterministic_generation(extra_options)

        # self.start_progress_bar(self.current_section)

        action = self.current_section
        tab = self.tabs[action]

        self.settings.seed.set(self.seed)

        if action in ("txt2img", "img2img", "pix2pix", "depth2img", "txt2vid"):
            samples = self.samples
        else:
            samples = 1

        prompt = self.prompt
        negative_prompt = self.negative_prompt

        # set the model data
        model = self.model
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
        options = {
            f"{action}_prompt": prompt,
            f"{action}_negative_prompt": negative_prompt,
            f"{action}_steps": self.steps,
            f"{action}_ddim_eta": self.ddim_eta,  # only applies to ddim scheduler
            f"{action}_n_iter": 1,
            f"{action}_width": self.working_width,
            f"{action}_height": self.working_height,
            f"{action}_n_samples": samples,
            f"{action}_scale": self.scale / 100,
            f"{action}_seed": self.seed,
            f"{action}_model": model,
            f"{action}_scheduler": self.scheduler,
            f"{action}_model_path": model_path,
            f"{action}_model_branch": model_branch,
            f"{action}_lora": self.available_lora(action),
            f"{action}_controlnet_conditioning_scale": self.controlnet_guidance_scale,
            f"generator_section": self.currentTabSection,
            f"width": self.working_width,
            f"height": self.working_height,
            "do_nsfw_filter": self.settings_manager.settings.nsfw_filter.get(),
            "model_base_path": self.model_base_path,
            "pos_x": 0,
            "pos_y": 0,
            "outpaint_box_rect": self.active_rect,
            "hf_token": self.settings_manager.settings.hf_api_key.get(),
            "enable_controlnet": self.enable_controlnet and self.controlnet is not None,
            "controlnet": self.controlnet,
            "deterministic_generation": self.deterministic,
            "deterministic_seed": False,
            "zeroshot": self.zeroshot
        }

        if action == "superresolution":
            options["original_image_width"] = self.canvas.current_active_image_data.image.width
            options["original_image_height"] = self.canvas.current_active_image_data.image.height

        if action in ["txt2img", "img2img", "outpaint", "depth2img", "pix2pix"]:
            options[f"{action}_strength"] = self.strength / 100.0

        if action == "pix2pix":
            options[f"pix2pix_image_guidance_scale"] = self.image_scale

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

    def load_template(self, template_name):
        try:
            return uic.loadUi(
                os.path.join("pyqt", f"{template_name}.ui"))
        except UIFileException:
            return None

    def clear_status_message(self):
        self.message_var.set("")
