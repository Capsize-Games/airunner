import json
import re

from PySide6.QtCore import Signal, QRect, Slot

from airunner.enums import (
    SignalCode,
    GeneratorSection,
)
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.generator_form.templates.generatorform_ui import (
    Ui_generator_form,
)
from airunner.data.models import Tab


class GeneratorForm(BaseWidget):
    widget_class_ = Ui_generator_form
    changed_signal = Signal(str, object)

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.GENERATE_IMAGE_FROM_IMAGE_SIGNAL: self.handle_generate_image_from_image,
            SignalCode.DO_GENERATE_IMAGE_FROM_IMAGE_SIGNAL: self.do_generate_image_from_image_signal_handler,
            SignalCode.SD_LOAD_PROMPT_SIGNAL: self.on_load_saved_stablediffuion_prompt_signal,
            SignalCode.BOT_MOOD_UPDATED: self.on_bot_mood_updated,
        }
        super().__init__(*args, **kwargs)
        self.seed_override = None
        self.parent = None
        self.initialized = False
        self.ui.generator_form_tabs.currentChanged.connect(
            self.on_generator_form_tabs_currentChanged
        )
        self.ui.generator_form_tabs.tabBar().setVisible(False)

    @Slot(int)
    def on_generator_form_tabs_currentChanged(self, index: int):
        Tab.update_tabs("left", self.ui.generator_form_tabs, index)

    @property
    def is_txt2img(self):
        return self.pipeline_action == GeneratorSection.TXT2IMG.value

    @property
    def is_outpaint(self):
        return self.pipeline_action == GeneratorSection.OUTPAINT.value

    @property
    def pipeline_action(self):
        return self.generator_settings.pipeline_action

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
        pos = self.active_grid_settings.pos
        rect = QRect(
            pos[0],
            pos[1],
            self.application_settings.working_width,
            self.application_settings.working_height,
        )

        drawing_pad_pos = self.drawing_pad_settings.pos
        rect.translate(-drawing_pad_pos[0], -drawing_pad_pos[1])

        return rect

    def on_bot_mood_updated(self, data):
        pass

    ##########################################################################
    # End LLM Generated Image handlers
    ##########################################################################

    def handle_generate_image_from_image(self, image):
        pass

    def on_load_saved_stablediffuion_prompt_signal(self, data: dict):
        saved_prompt = data.get("saved_prompt")
        self.ui.prompt.blockSignals(True)
        self.ui.negative_prompt.blockSignals(True)
        self.ui.secondary_prompt.blockSignals(True)
        self.ui.secondary_negative_prompt.blockSignals(True)
        self.ui.prompt.setPlainText(saved_prompt.prompt)
        self.ui.negative_prompt.setPlainText(saved_prompt.negative_prompt)
        self.ui.secondary_prompt.setPlainText(saved_prompt.secondary_prompt)
        self.ui.secondary_negative_prompt.setPlainText(
            saved_prompt.secondary_negative_prompt
        )
        self.ui.prompt.blockSignals(False)
        self.ui.negative_prompt.blockSignals(False)
        self.ui.secondary_prompt.blockSignals(False)
        self.ui.secondary_negative_prompt.blockSignals(False)

    def handle_image_presets_changed(self, val):
        self.update_generator_settings("image_preset", val)

    def do_generate_image_from_image_signal_handler(self, _data):
        self.do_generate()

    def do_generate(self, data=None):
        if data:
            finalize = data.get("finalize", None)
            if finalize:
                data = dict(callback=finalize)
            else:
                data = None
        self.api.art.send_request(data=data)

    def action_clicked_button_save_prompts(self):
        self.api.art.save_prompt(
            self.ui.prompt.toPlainText(),
            self.ui.negative_prompt.toPlainText(),
            self.ui.secondary_prompt.toPlainText(),
            self.ui.secondary_negative_prompt.toPlainText(),
        )

    def handle_prompt_changed(self):
        pass

    def handle_negative_prompt_changed(self):
        pass

    def handle_second_prompt_changed(self):
        pass

    def handle_second_negative_prompt_changed(self):
        pass

    @Slot()
    def handle_interrupt_button_clicked(self):
        self.api.art.interrupt_generate()

    def extract_json_from_message(self, message):
        # Regular expression to find the JSON block
        json_pattern = re.compile(r".*`json\s*({.*?})\s*`.*", re.DOTALL)
        match = json_pattern.search(message)

        if match:
            json_block = match.group(1)
            try:
                # Convert the JSON block to a dictionary
                json_dict = json.loads(json_block)
                return json_dict
            except json.JSONDecodeError as e:
                self.logger.error(f"Error decoding JSON block: {e}")
                return {}
        else:
            self.logger.error("No JSON block found in message")
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

    def showEvent(self, event):
        super().showEvent(event)
        self.initialized = True
        active_index = 0
        tabs = Tab.objects.filter_by(section="left")
        for tab in tabs:
            if tab.active:
                active_index = tab.index
                break
        self.ui.generator_form_tabs.setCurrentIndex(active_index)
