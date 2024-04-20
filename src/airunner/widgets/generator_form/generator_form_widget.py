import time
from PIL import Image

from PySide6.QtCore import Signal, QRect
from PySide6.QtWidgets import QApplication

from airunner.enums import SignalCode, GeneratorSection, ImageCategory
from airunner.settings import PHOTO_REALISTIC_NEGATIVE_PROMPT, ILLUSTRATION_NEGATIVE_PROMPT
from airunner.utils.create_worker import create_worker
from airunner.utils.convert_base64_to_image import convert_base64_to_image
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.generator_form.templates.generatorform_ui import Ui_generator_form
from airunner.workers.model_scanner_worker import ModelScannerWorker


class GeneratorForm(BaseWidget):
    widget_class_ = Ui_generator_form
    changed_signal = Signal(str, object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.seed_override = None
        self.parent = None
        self.current_prompt_value = None
        self.current_negative_prompt_value = None
        self.initialized = False
        self.ui.generator_form_tabs.tabBar().hide()
        self.activate_ai_mode()

        self.signal_handlers = {
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: self.on_application_settings_changed_signal,
            SignalCode.SD_GENERATE_IMAGE_SIGNAL: self.on_generate_image_signal,
            SignalCode.APPLICATION_STOP_SD_PROGRESS_BAR_SIGNAL: self.on_stop_image_generator_progress_bar_signal,
            SignalCode.SD_PROGRESS_SIGNAL: self.on_progress_signal,
            SignalCode.GENERATOR_FORM_UPDATE_VALUES_SIGNAL: self.set_form_values,
            SignalCode.LLM_IMAGE_PROMPT_GENERATED_SIGNAL: self.on_llm_image_prompt_generated_signal,
            SignalCode.GENERATE_IMAGE_FROM_IMAGE_SIGNAL: self.handle_generate_image_from_image,
            SignalCode.DO_GENERATE_IMAGE_FROM_IMAGE_SIGNAL: self.do_generate_image_from_image_signal_handler,
            SignalCode.SD_LOAD_PROMPT_SIGNAL: self.on_load_saved_stablediffuion_prompt_signal
        }

        self.model_scanner_worker = create_worker(ModelScannerWorker)
        self.model_scanner_worker.add_to_queue("scan_for_models")

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
    def seed(self):
        return self.settings["generator_settings"]["seed"]

    @seed.setter
    def seed(self, val):
        settings = self.settings
        settings["generator_settings"]["seed"] = val
        self.settings = settings

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

    def on_load_saved_stablediffuion_prompt_signal(self, index):
        try:
            saved_prompt = self.settings["saved_prompts"][index]
        except KeyError:
            self.logger.error(f"Unable to load prompt at index {index}")
            saved_prompt = None

        if saved_prompt:
            settings = self.settings
            settings["generator_settings"]["prompt"] = saved_prompt["prompt"]
            settings["generator_settings"]["negative_prompt"] = saved_prompt["negative_prompt"]
            self.settings = settings
            self.set_form_values()

    def handle_generate_image_from_image(self, image):
        pass

    def do_generate_image_from_image_signal_handler(self, res):
        self.call_generate()

    def on_application_settings_changed_signal(self, _message: dict):
        self.activate_ai_mode()
    
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

    def save_prompt_to_settings(self):
        settings = self.settings

        value = self.ui.prompt.toPlainText()
        self.current_prompt_value = value
        settings["generator_settings"]["prompt"] = value

        value = self.ui.negative_prompt.toPlainText()
        self.current_negative_prompt_value = value
        settings["generator_settings"]["negative_prompt"] = value

        self.settings = settings

    def handle_generate_button_clicked(self):
        self.save_prompt_to_settings()
        self.start_progress_bar()
        self.generate()

    def handle_interrupt_button_clicked(self):
        self.emit_signal(SignalCode.INTERRUPT_PROCESS_SIGNAL)

    def generate(self):
        if self.settings["generator_settings"]["n_samples"] > 1:
            self.emit_signal(SignalCode.ENGINE_STOP_PROCESSING_QUEUE_SIGNAL)
        self.call_generate()
        self.seed_override = None
        self.emit_signal(SignalCode.ENGINE_START_PROCESSING_QUEUE_SIGNAL)

    def on_generate_image_signal(self, _message):
        self.start_progress_bar()
        self.generate()

    def do_generate_image(self):
        time.sleep(0.1)

        if self.settings["generator_settings"]["section"] == GeneratorSection.OUTPAINT.value:
            image = convert_base64_to_image(self.settings["canvas_settings"]["image"])
            mask = convert_base64_to_image(self.settings["outpaint_settings"]["image"])

            active_rect = self.active_rect
            overlap_left = max(0, active_rect.left())
            overlap_right = min(self.settings["working_width"], active_rect.right())
            overlap_top = max(0, active_rect.top())
            overlap_bottom = min(self.settings["working_height"], active_rect.bottom())

            crop_rect = (overlap_left, overlap_top, overlap_right, overlap_bottom)

            # Crop the image at the overlap position
            cropped_image = image.crop(crop_rect)

            # Create a new black image of the same size as the input image
            new_image = Image.new('RGB', (self.settings["working_width"], self.settings["working_height"]), 'black')

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
            self.emit_signal(SignalCode.DO_GENERATE_SIGNAL)

    def call_generate(self):
        self.emit_signal(SignalCode.LLM_UNLOAD_SIGNAL, {
            'do_unload_model': self.settings["memory_settings"]["unload_unused_models"],
            'move_unused_model_to_cpu': self.settings["memory_settings"]["move_unused_model_to_cpu"],
            'dtype': self.settings["llm_generator_settings"]["dtype"],
            'callback': lambda: self.do_generate_image()
        })

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
        self.ui.progress_bar.setRange(0, 0)
        self.ui.progress_bar.show()

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

    def on_stop_image_generator_progress_bar_signal(self):
        self.stop_progress_bar()

    def stop_progress_bar(self):
        progressbar = self.ui.progress_bar
        if not progressbar:
            return
        progressbar.setRange(0, 100)
        progressbar.setValue(100)