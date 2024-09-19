import time
from PIL import Image

from PySide6.QtCore import Signal, QRect, Slot
from PySide6.QtWidgets import QApplication

from airunner.enums import SignalCode, GeneratorSection, ImageCategory, ImagePreset, StableDiffusionVersion, \
    ModelStatus, ModelType
from airunner.settings import PHOTO_REALISTIC_NEGATIVE_PROMPT, ILLUSTRATION_NEGATIVE_PROMPT
from airunner.utils.convert_base64_to_image import convert_base64_to_image
from airunner.utils.random_seed import random_seed
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.generator_form.templates.generatorform_ui import Ui_generator_form


class GeneratorForm(BaseWidget):
    widget_class_ = Ui_generator_form
    changed_signal = Signal(str, object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.seed_override = None
        self.parent = None
        self.current_prompt_value = None
        self.current_negative_prompt_value = None
        self.current_secondary_prompt_value = None
        self.current_secondary_negative_prompt_value = None
        self.initialized = False
        self.showing_past_conversations = False
        self.signal_handlers = {
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: self.on_application_settings_changed_signal,
            SignalCode.SD_GENERATE_IMAGE_SIGNAL: self.on_generate_image_signal,
            SignalCode.APPLICATION_STOP_SD_PROGRESS_BAR_SIGNAL: self.on_stop_image_generator_progress_bar_signal,
            SignalCode.SD_PROGRESS_SIGNAL: self.on_progress_signal,
            SignalCode.GENERATOR_FORM_UPDATE_VALUES_SIGNAL: self.set_form_values,
            SignalCode.LLM_IMAGE_PROMPT_GENERATED_SIGNAL: self.on_llm_image_prompt_generated_signal,
            SignalCode.GENERATE_IMAGE_FROM_IMAGE_SIGNAL: self.handle_generate_image_from_image,
            SignalCode.DO_GENERATE_IMAGE_FROM_IMAGE_SIGNAL: self.do_generate_image_from_image_signal_handler,
            SignalCode.SD_LOAD_PROMPT_SIGNAL: self.on_load_saved_stablediffuion_prompt_signal,
            SignalCode.LOAD_CONVERSATION: self.on_load_conversation,
        }

    def on_load_conversation(self):
        self.ui.generator_form_tabs.setCurrentIndex(1)

    def toggle_secondary_prompts(self):
        settings = self.settings
        if settings["generator_settings"]["version"] != StableDiffusionVersion.SDXL1_0.value:
            if settings["generator_settings"]["version"] == StableDiffusionVersion.SDXL_TURBO.value:
                self.ui.negative_prompt_label.hide()
                self.ui.negative_prompt.hide()
            else:
                self.ui.negative_prompt_label.show()
                self.ui.negative_prompt.show()
            self.ui.croops_coord_top_left_groupbox.hide()
            self.ui.secondary_prompt.hide()
            self.ui.secondary_negative_prompt.hide()
        else:
            self.ui.croops_coord_top_left_groupbox.show()
            self.ui.negative_prompt_label.show()
            self.ui.negative_prompt.show()
            self.ui.secondary_prompt.show()
            self.ui.secondary_negative_prompt.show()


    @property
    def is_txt2img(self):
        return self.generator_section == GeneratorSection.TXT2IMG.value

    @property
    def is_outpaint(self):
        return self.generator_section == GeneratorSection.OUTPAINT.value

    @property
    def generator_section(self):
        return self.settings["pipeline"]

    @property
    def generator_name(self):
        return self.settings["current_image_generator"]

    @property
    def seed(self):
        return self.settings["generator_settings"]["seed"]

    @seed.setter
    def seed(self, val):
        settings = self.settings
        settings["generator_settings"]["seed"] = val
        self.settings = settings

    @property
    def active_rect(self):
        settings = self.settings
        rect = QRect(
            settings["active_grid_settings"]["pos_x"],
            settings["active_grid_settings"]["pos_y"],
            settings["working_width"],
            settings["working_height"]
        )
        rect.translate(-settings["canvas_settings"]["pos_x"], -settings["canvas_settings"]["pos_y"])

        return rect

    def on_load_saved_stablediffuion_prompt_signal(self, index):
        settings = self.settings
        try:
            saved_prompt = settings["saved_prompts"][index]
        except KeyError:
            self.logger.error(f"Unable to load prompt at index {index}")
            saved_prompt = None

        if saved_prompt:
            settings["generator_settings"]["prompt"] = saved_prompt["prompt"]
            settings["generator_settings"]["negative_prompt"] = saved_prompt["negative_prompt"]
            self.settings = settings
            self.set_form_values()

    def handle_image_presets_changed(self, val):
        settings = self.settings
        settings["generator_settings"]["image_preset"] = val
        self.settings = settings

    def handle_generate_image_from_image(self, image):
        pass

    def do_generate_image_from_image_signal_handler(self, res):
        self.do_generate()

    def do_generate(self):
        self.emit_signal(SignalCode.DO_GENERATE_SIGNAL)

    def on_application_settings_changed_signal(self):
        self.toggle_secondary_prompts()
    
    def on_progress_signal(self, message):
        self.handle_progress_bar(message)

    def activate_ai_mode(self):
        ai_mode = self.settings.get("ai_mode", False)
        self.ui.generator_form_tabs.setCurrentIndex(1 if ai_mode is True else 0)

    def action_clicked_button_save_prompts(self):
        self.emit_signal(SignalCode.SD_SAVE_PROMPT_SIGNAL)

    def handle_prompt_changed(self):
        pass

    def handle_negative_prompt_changed(self):
        pass

    def handle_second_prompt_changed(self):
        pass

    def handle_second_negative_prompt_changed(self):
        pass

    def on_generate_image_signal(self):
        self.handle_generate_button_clicked()

    def handle_generate_button_clicked(self):
        self.save_prompt_to_settings()
        self.start_progress_bar()
        self.generate()

    def save_prompt_to_settings(self):
        settings = self.settings

        value = self.ui.prompt.toPlainText()
        self.current_prompt_value = value
        settings["generator_settings"]["prompt"] = value

        value = self.ui.negative_prompt.toPlainText()
        self.current_negative_prompt_value = value
        settings["generator_settings"]["negative_prompt"] = value

        value = self.ui.secondary_prompt.toPlainText()
        self.current_secondary_prompt_value = value
        settings["generator_settings"]["second_prompt"] = value

        value = self.ui.secondary_negative_prompt.toPlainText()
        self.current_secondary_negative_prompt_value = value
        settings["generator_settings"]["second_negative_prompt"] = value

        def get_integer_value(widget):
            try:
                return int(widget.text())
            except ValueError:
                return 0

        x = get_integer_value(self.ui.crops_coord_top_left_x)
        y = get_integer_value(self.ui.crops_coord_top_left_y)
        settings["generator_settings"]["crops_coord_top_left"] = (x, y)

        self.settings = settings

    def handle_interrupt_button_clicked(self):
        self.emit_signal(SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL)

    def generate(self):
        settings = self.settings
        if settings["generator_settings"]["random_seed"]:
            self.seed = random_seed()
        if settings["generator_settings"]["n_samples"] > 1:
            self.emit_signal(SignalCode.ENGINE_STOP_PROCESSING_QUEUE_SIGNAL)
        self.do_generate()
        self.seed_override = None
        self.emit_signal(SignalCode.ENGINE_START_PROCESSING_QUEUE_SIGNAL)

    def do_generate_image(self):
        time.sleep(0.1)
        settings = self.settings

        if settings["generator_settings"]["section"] == GeneratorSection.OUTPAINT.value:
            image = convert_base64_to_image(settings["canvas_settings"]["image"])
            mask = convert_base64_to_image(settings["outpaint_settings"]["image"])

            active_rect = self.active_rect
            overlap_left = max(0, active_rect.left())
            overlap_right = min(settings["working_width"], active_rect.right())
            overlap_top = max(0, active_rect.top())
            overlap_bottom = min(settings["working_height"], active_rect.bottom())

            crop_rect = (overlap_left, overlap_top, overlap_right, overlap_bottom)

            # Crop the image at the overlap position
            cropped_image = image.crop(crop_rect)

            # Create a new black image of the same size as the input image
            new_image = Image.new('RGB', (settings["working_width"], settings["working_height"]), 'black')

            # Paste the cropped image to the top of the new image
            position = (0, 0)
            if active_rect.left() < 0:
                position = (abs(active_rect.left()), 0)
            if active_rect.top() < 0:
                position = (0, abs(active_rect.top()))
            new_image.paste(cropped_image, position)

            self.emit_signal(SignalCode.DO_GENERATE_SIGNAL, {
                "mask_image": mask.convert("RGB"),
                "image": new_image.convert("RGB")
            })
        else:
            self.do_generate()

    def on_llm_image_prompt_generated_signal(self, data):
        prompt = data.get("prompt", None)
        prompt_type = data.get("type", ImageCategory.PHOTO.value)
        self.ui.prompt.setPlainText(prompt)
        if prompt_type == "photo":
            negative_prompt = PHOTO_REALISTIC_NEGATIVE_PROMPT
        else:
            negative_prompt = ILLUSTRATION_NEGATIVE_PROMPT
        self.ui.negative_prompt.setPlainText(negative_prompt)
        self.handle_generate_button_clicked()

    def get_memory_options(self):
        settings = self.settings
        return {
            "use_last_channels": settings["memory_settings"]["use_last_channels"],
            "use_enable_sequential_cpu_offload": settings["memory_settings"]["use_enable_sequential_cpu_offload"],
            "enable_model_cpu_offload": settings["memory_settings"]["enable_model_cpu_offload"],
            "use_attention_slicing": settings["memory_settings"]["use_attention_slicing"],
            "use_tf32": settings["memory_settings"]["use_tf32"],
            "use_cudnn_benchmark": settings["memory_settings"]["use_cudnn_benchmark"],
            "use_enable_vae_slicing": settings["memory_settings"]["use_enable_vae_slicing"],
            "use_accelerated_transformers": settings["memory_settings"]["use_accelerated_transformers"],
            "use_torch_compile": settings["memory_settings"]["use_torch_compile"],
            "use_tiled_vae": settings["memory_settings"]["use_tiled_vae"],
            "use_tome_sd": settings["memory_settings"]["use_tome_sd"],
            "tome_sd_ratio": settings["memory_settings"]["tome_sd_ratio"],
        }

    def handle_quality_effects_changed(self, val):
        print("quality_effects", val)
        settings = self.settings
        settings["generator_settings"]["quality_effects"] = val
        self.settings = settings

    def handle_progress_bar(self, message):
        step = message.get("step")
        total = message.get("total")
        if step == total:
            self.stop_progress_bar()
            return

        if step == 0 and total == 0:
            current = 0
        else:
            try:
                current = (step / total)
            except ZeroDivisionError:
                current = 0
        self.set_progress_bar_value(int(current * 100))
    
    def set_progress_bar_value(self, value):
        progressbar = self.ui.progress_bar
        if not progressbar:
            return
        if progressbar.maximum() == 0:
            progressbar.setRange(0, 100)
        progressbar.setValue(value)
        QApplication.processEvents()

    def start_progress_bar(self):
        self.ui.progress_bar.setFormat("Generating %p%")
        self.ui.progress_bar.setRange(0, 0)
        self.ui.progress_bar.show()

    def showEvent(self, event):
        super().showEvent(event)
        self.activate_ai_mode()
        self.set_form_values()
        self.toggle_secondary_prompts()
        self.initialized = True

    def set_form_values(self):
        settings = self.settings
        self.ui.prompt.blockSignals(True)
        self.ui.negative_prompt.blockSignals(True)
        self.ui.secondary_prompt.blockSignals(True)
        self.ui.secondary_negative_prompt.blockSignals(True)
        self.ui.crops_coord_top_left_x.blockSignals(True)
        self.ui.crops_coord_top_left_y.blockSignals(True)
        self.ui.image_presets.blockSignals(True)
        self.ui.quality_effects.blockSignals(True)

        self.ui.prompt.setPlainText(settings["generator_settings"]["prompt"])
        self.ui.negative_prompt.setPlainText(settings["generator_settings"]["negative_prompt"])
        self.ui.secondary_prompt.setPlainText(settings["generator_settings"]["second_prompt"])
        self.ui.secondary_negative_prompt.setPlainText(settings["generator_settings"]["second_negative_prompt"])
        self.ui.crops_coord_top_left_x.setText(str(settings["generator_settings"]["crops_coord_top_left"][0]))
        self.ui.crops_coord_top_left_y.setText(str(settings["generator_settings"]["crops_coord_top_left"][1]))

        image_presets = [""] + [preset.value for preset in ImagePreset]
        self.ui.image_presets.addItems(image_presets)
        self.ui.image_presets.setCurrentIndex(
            self.ui.image_presets.findText(self.settings["generator_settings"]["image_preset"])
        )

        self.ui.quality_effects.setCurrentText(settings["generator_settings"]["quality_effects"])

        self.ui.prompt.blockSignals(False)
        self.ui.negative_prompt.blockSignals(False)
        self.ui.secondary_prompt.blockSignals(False)
        self.ui.secondary_negative_prompt.blockSignals(False)
        self.ui.crops_coord_top_left_x.blockSignals(False)
        self.ui.crops_coord_top_left_y.blockSignals(False)
        self.ui.image_presets.blockSignals(False)
        self.ui.quality_effects.blockSignals(False)


    def clear_prompts(self):
        self.ui.prompt.setPlainText("")
        self.ui.negative_prompt.setPlainText("")

    def on_stop_image_generator_progress_bar_signal(self):
        self.stop_progress_bar()

    def stop_progress_bar(self):
        progressbar = self.ui.progress_bar
        if not progressbar:
            return
        progressbar.setRange(0, 100)
        progressbar.setValue(100)

        # set text of progressbar to "complete"
        progressbar.setFormat("Complete")
