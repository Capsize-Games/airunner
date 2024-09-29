import json
import re
import time
from PIL import Image

from PySide6.QtCore import Signal, QRect, QThread, QObject, Slot
from PySide6.QtWidgets import QApplication

from airunner.enums import SignalCode, GeneratorSection, ImageCategory, ImagePreset, StableDiffusionVersion
from airunner.mediator_mixin import MediatorMixin
from airunner.settings import PHOTO_REALISTIC_NEGATIVE_PROMPT, ILLUSTRATION_NEGATIVE_PROMPT
from airunner.utils.convert_base64_to_image import convert_base64_to_image
from airunner.utils.random_seed import random_seed
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.generator_form.templates.generatorform_ui import Ui_generator_form
from airunner.windows.main.settings_mixin import SettingsMixin


class SaveGeneratorSettingsWorker(
    QObject,
    MediatorMixin,
    SettingsMixin
):
    def __init__(self, parent):
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        super().__init__()
        self.parent = parent
        self.current_prompt_value = None
        self.current_negative_prompt_value = None
        self.current_secondary_prompt_value = None
        self.current_secondary_negative_prompt_value = None
        self.crops_coord_top_left_x = 0
        self.crops_coord_top_left_y = 0


    def run(self):
        do_update_settings = False
        while True:
            value = self.parent.ui.prompt.toPlainText()
            if value != self.current_prompt_value:
                self.current_prompt_value = value
                do_update_settings = True

            value = self.parent.ui.negative_prompt.toPlainText()
            if value != self.current_negative_prompt_value:
                self.current_negative_prompt_value = value
                do_update_settings = True

            value = self.parent.ui.secondary_prompt.toPlainText()
            if value != self.current_secondary_prompt_value:
                self.current_secondary_prompt_value = value
                do_update_settings = True

            value = self.parent.ui.secondary_negative_prompt.toPlainText()
            if value != self.current_secondary_negative_prompt_value:
                self.current_secondary_negative_prompt_value = value
                do_update_settings = True

            x = self.parent.ui.crops_coord_top_left_x.text()
            y = self.parent.ui.crops_coord_top_left_y.text()
            x = int(x) if x != '' else 0
            y = int(y) if y != '' else 0

            if self.crops_coord_top_left_x != x:
                self.crops_coord_top_left_x = x
                do_update_settings = True
            if self.crops_coord_top_left_y != y:
                self.crops_coord_top_left_y = y
                do_update_settings = True

            if do_update_settings:
                do_update_settings = False
                generator_settings = self.generator_settings
                generator_settings.prompt = self.current_prompt_value
                generator_settings.negative_prompt = self.current_negative_prompt_value
                generator_settings.second_prompt = self.current_secondary_prompt_value
                generator_settings.second_negative_prompt = self.current_secondary_negative_prompt_value
                generator_settings.crops_coord_top_left = (self.crops_coord_top_left_x, self.crops_coord_top_left_y)
                self.save_generator_settings(generator_settings)

            time.sleep(0.1)


class GeneratorForm(BaseWidget):
    widget_class_ = Ui_generator_form
    changed_signal = Signal(str, object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.seed_override = None
        self.parent = None
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
        self.thread = QThread()
        self.worker = SaveGeneratorSettingsWorker(parent=self)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)

    @property
    def is_txt2img(self):
        return self.generator_section == GeneratorSection.TXT2IMG.value

    @property
    def is_outpaint(self):
        return self.generator_section == GeneratorSection.OUTPAINT.value

    @property
    def generator_section(self):
        return self.application_settings.pipeline

    @property
    def generator_name(self):
        return self.application_settings.current_image_generator

    @property
    def seed(self):
        return self.generator_settings.seed

    @seed.setter
    def seed(self, val):
        self.update_generator_settings("seed", val)

    @property
    def active_rect(self):
        rect = QRect(
            self.active_grid_settings.pos_x,
            self.active_grid_settings.pos_y,
            self.application_settings.working_width,
            self.application_settings.working_height
        )
        rect.translate(-self.canvas_settings.pos_x, -self.canvas_settings.pos_y)

        return rect

    def on_application_settings_changed_signal(self, _data):
        self.toggle_secondary_prompts()

    def on_generate_image_signal(self, _data):
        self.handle_generate_button_clicked()

    def on_stop_image_generator_progress_bar_signal(self, _data):
        self.stop_progress_bar()

    def on_progress_signal(self, message):
        self.handle_progress_bar(message)

    def on_llm_image_prompt_generated_signal(self, data):
        data = self.extract_json_from_message(data["message"])
        prompt = data.get("description", None)
        secondary_prompt = data.get("composition", None)
        prompt_type = data.get("type", ImageCategory.PHOTO.value)
        if prompt_type == "photo":
            negative_prompt = PHOTO_REALISTIC_NEGATIVE_PROMPT
        else:
            negative_prompt = ILLUSTRATION_NEGATIVE_PROMPT
        self.ui.prompt.setPlainText(prompt)
        self.ui.negative_prompt.setPlainText(negative_prompt)
        self.ui.secondary_prompt.setPlainText(secondary_prompt)
        self.ui.secondary_negative_prompt.setPlainText(negative_prompt)
        self.handle_generate_button_clicked()

    def handle_generate_image_from_image(self, image):
        pass

    def on_load_conversation(self, _data):
        self.ui.generator_form_tabs.setCurrentIndex(1)

    def toggle_secondary_prompts(self):
        if self.generator_settings.version != StableDiffusionVersion.SDXL1_0.value:
            if self.generator_settings.version == StableDiffusionVersion.SDXL_TURBO.value:
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

    def on_load_saved_stablediffuion_prompt_signal(self, data: dict):
        saved_prompt = data.get("saved_prompt")
        self.ui.prompt.blockSignals(True)
        self.ui.negative_prompt.blockSignals(True)
        self.ui.secondary_prompt.blockSignals(True)
        self.ui.secondary_negative_prompt.blockSignals(True)
        self.ui.prompt.setPlainText(saved_prompt.prompt)
        self.ui.negative_prompt.setPlainText(saved_prompt.negative_prompt)
        self.ui.secondary_prompt.setPlainText(saved_prompt.secondary_prompt)
        self.ui.secondary_negative_prompt.setPlainText(saved_prompt.secondary_negative_prompt)
        self.ui.prompt.blockSignals(False)
        self.ui.negative_prompt.blockSignals(False)
        self.ui.secondary_prompt.blockSignals(False)
        self.ui.secondary_negative_prompt.blockSignals(False)

    def handle_image_presets_changed(self, val):
        self.update_generator_settings("image_preset", val)

    def do_generate_image_from_image_signal_handler(self, _data):
        self.do_generate()

    def do_generate(self):
        self.emit_signal(SignalCode.DO_GENERATE_SIGNAL)

    def activate_ai_mode(self):
        ai_mode = self.application_settings.ai_mode
        self.ui.generator_form_tabs.setCurrentIndex(1 if ai_mode is True else 0)

    def action_clicked_button_save_prompts(self):
        self.emit_signal(SignalCode.SD_SAVE_PROMPT_SIGNAL, {
            "prompt": self.ui.prompt.toPlainText(),
            "negative_prompt": self.ui.negative_prompt.toPlainText(),
            "secondary_prompt": self.ui.secondary_prompt.toPlainText(),
            "secondary_negative_prompt": self.ui.secondary_negative_prompt.toPlainText(),
        })

    def handle_prompt_changed(self):
        pass

    def handle_negative_prompt_changed(self):
        pass

    def handle_second_prompt_changed(self):
        pass

    def handle_second_negative_prompt_changed(self):
        pass

    def handle_generate_button_clicked(self):
        self.start_progress_bar()
        self.generate()

    @Slot()
    def handle_interrupt_button_clicked(self):
        self.emit_signal(SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL)

    def generate(self):
        if self.generator_settings.random_seed:
            self.seed = random_seed()
        if self.generator_settings.n_samples > 1:
            self.emit_signal(SignalCode.ENGINE_STOP_PROCESSING_QUEUE_SIGNAL)
        self.do_generate()
        self.seed_override = None
        self.emit_signal(SignalCode.ENGINE_START_PROCESSING_QUEUE_SIGNAL)

    def do_generate_image(self):
        time.sleep(0.1)

        if self.generator_settings.section == GeneratorSection.OUTPAINT.value:
            image = convert_base64_to_image(self.canvas_settings.image)
            mask = convert_base64_to_image(self.outpaint_settings.image)

            active_rect = self.active_rect
            overlap_left = max(0, active_rect.left())
            overlap_right = min(self.application_settings.working_width, active_rect.right())
            overlap_top = max(0, active_rect.top())
            overlap_bottom = min(self.application_settings.working_height, active_rect.bottom())

            crop_rect = (overlap_left, overlap_top, overlap_right, overlap_bottom)

            # Crop the image at the overlap position
            cropped_image = image.crop(crop_rect)

            # Create a new black image of the same size as the input image
            new_image = Image.new('RGB', (self.application_settings.working_width, self.application_settings.working_height))

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

    def extract_json_from_message(self, message):
        # Regular expression to find the JSON block
        json_pattern = re.compile(r'.*`json\s*({.*?})\s*`.*', re.DOTALL)
        match = json_pattern.search(message)

        if match:
            json_block = match.group(1)
            try:
                # Convert the JSON block to a dictionary
                json_dict = json.loads(json_block)
                return json_dict
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
                return {}
        else:
            print("No JSON block found in the message.")
            return {}

    def get_memory_options(self):
        return {
            "use_last_channels": self.memory_settings.use_last_channels,
            "use_enable_sequential_cpu_offload": self.memory_settings.use_enable_sequential_cpu_offload,
            "enable_model_cpu_offload": self.memory_settings.enable_model_cpu_offload,
            "use_attention_slicing": self.memory_settings.use_attention_slicing,
            "use_tf32": self.memory_settings.use_tf32,
            "use_cudnn_benchmark": self.memory_settings.use_cudnn_benchmark,
            "use_enable_vae_slicing": self.memory_settings.use_enable_vae_slicing,
            "use_accelerated_transformers": self.memory_settings.use_accelerated_transformers,
            "use_torch_compile": self.memory_settings.use_torch_compile,
            "use_tiled_vae": self.memory_settings.use_tiled_vae,
            "use_tome_sd": self.memory_settings.use_tome_sd,
            "tome_sd_ratio": self.memory_settings.tome_sd_ratio,
        }

    def handle_quality_effects_changed(self, val):
        self.update_generator_settings("quality_effects", val)

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
        self.thread.start()

    def set_form_values(self, _data=None):
        self.ui.prompt.blockSignals(True)
        self.ui.negative_prompt.blockSignals(True)
        self.ui.secondary_prompt.blockSignals(True)
        self.ui.secondary_negative_prompt.blockSignals(True)
        self.ui.crops_coord_top_left_x.blockSignals(True)
        self.ui.crops_coord_top_left_y.blockSignals(True)
        self.ui.image_presets.blockSignals(True)
        self.ui.quality_effects.blockSignals(True)

        self.ui.prompt.setPlainText(self.generator_settings.prompt)
        self.ui.negative_prompt.setPlainText(self.generator_settings.negative_prompt)
        self.ui.secondary_prompt.setPlainText(self.generator_settings.second_prompt)
        self.ui.secondary_negative_prompt.setPlainText(self.generator_settings.second_negative_prompt)
        self.ui.crops_coord_top_left_x.setText(str(self.generator_settings.crops_coord_top_left[0]))
        self.ui.crops_coord_top_left_y.setText(str(self.generator_settings.crops_coord_top_left[0]))

        image_presets = [""] + [preset.value for preset in ImagePreset]
        self.ui.image_presets.addItems(image_presets)
        self.ui.image_presets.setCurrentIndex(
            self.ui.image_presets.findText(self.generator_settings.image_preset)
        )

        self.ui.quality_effects.setCurrentText(self.generator_settings.quality_effects)

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
        self.ui.secondary_prompt.setPlainText("")
        self.ui.secondary_negative_prompt.setPlainText("")

    def stop_progress_bar(self):
        progressbar = self.ui.progress_bar
        if not progressbar:
            return
        progressbar.setRange(0, 100)
        progressbar.setValue(100)

        # set text of progressbar to "complete"
        progressbar.setFormat("Complete")
