import json
import re
import time

from PySide6.QtCore import Signal, QRect, QThread, QObject, Slot
from PySide6.QtWidgets import QApplication

from airunner.data.models import ShortcutKeys
from airunner.enums import SignalCode, GeneratorSection, ImageCategory, ImagePreset, StableDiffusionVersion, \
    ModelStatus, ModelType, LLMActionType
from airunner.mediator_mixin import MediatorMixin
from airunner.settings import PHOTO_REALISTIC_NEGATIVE_PROMPT, ILLUSTRATION_NEGATIVE_PROMPT
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
                generator_settings.crops_coord_top_left = dict(
                    x=self.crops_coord_top_left_x,
                    y=self.crops_coord_top_left_y
                )
                generator_settings.save()

            time.sleep(0.1)


class GeneratorForm(BaseWidget):
    widget_class_ = Ui_generator_form
    changed_signal = Signal(str, object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conversation = None
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
            SignalCode.BOT_MOOD_UPDATED: self.on_bot_mood_updated,
            SignalCode.KEYBOARD_SHORTCUTS_UPDATED: self.on_keyboard_shortcuts_updated,
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL: self.on_model_status_changed_signal,
        }
        self.thread = QThread()
        self.worker = SaveGeneratorSettingsWorker(parent=self)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)

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
        rect = QRect(
            self.active_grid_settings.pos_x,
            self.active_grid_settings.pos_y,
            self.application_settings.working_width,
            self.application_settings.working_height
        )
        rect.translate(-self.drawing_pad_settings.x_pos, -self.drawing_pad_settings.y_pos)

        return rect

    def on_keyboard_shortcuts_updated(self):
        self._set_keyboard_shortcuts()

    def on_application_settings_changed_signal(self, _data):
        self.toggle_secondary_prompts()

    def on_bot_mood_updated(self, data):
        self._set_chatbot_mood(data["mood"])

    def on_generate_image_signal(self, _data):
        self.handle_generate_button_clicked()

    def on_stop_image_generator_progress_bar_signal(self, _data):
        self.stop_progress_bar()

    def on_progress_signal(self, message):
        self.handle_progress_bar(message)

    ##########################################################################
    # LLM Generated Image handlers
    ##########################################################################
    def on_llm_image_prompt_generated_signal(self, data):
        """
        This slot is called after an LLM has generated the prompts for an image.
        It sets the prompts in the generator form UI and continues the image generation process.
        """

        # Send a messagae to the user as chatbot letting them know that the image is generating
        self.emit_signal(
            SignalCode.LLM_TEXT_STREAMED_SIGNAL,
            dict(
                message="Your image is generating...",
                is_first_message=True,
                is_end_of_message=True,
                name=self.chatbot.name,
                action=LLMActionType.GENERATE_IMAGE
            )
        )

        # Unload non-Stable Diffusion models
        self.emit_signal(SignalCode.UNLOAD_NON_SD_MODELS, dict(
            callback=self.unload_llm_callback
        ))
        # Set the prompts in the generator form UI
        data = data["message"]
        prompt = data.get("prompt", None)
        secondary_prompt = data.get("secondary_prompt", None)
        prompt_type = data.get("type", ImageCategory.PHOTO.value)
        if prompt_type == "photo":
            negative_prompt = PHOTO_REALISTIC_NEGATIVE_PROMPT
        else:
            negative_prompt = ILLUSTRATION_NEGATIVE_PROMPT
        self.ui.prompt.setPlainText(prompt)
        self.ui.negative_prompt.setPlainText(negative_prompt)
        self.ui.secondary_prompt.setPlainText(secondary_prompt)
        self.ui.secondary_negative_prompt.setPlainText(negative_prompt)

    def unload_llm_callback(self, data:dict=None):
        """
        Callback function to be called after the LLM has been unloaded.
        """
        if not self.application_settings.sd_enabled:
            # If SD is not enabled, enable it and then emit a signal to generate the image
            # The callback function is handled by the signal handler for the SD_LOAD_SIGNAL.
            # The finalize function is a callback which is called after the image has been generated.
            self.emit_signal(SignalCode.TOGGLE_SD_SIGNAL, dict(
                callback=self.handle_generate_button_clicked,
                finalize=self.finalize_image_generated_by_llm
            ))
        else:
            # If SD is already enabled, emit a signal to generate the image.
            # The finalize function is a callback which is called after the image has been generated.
            self.handle_generate_button_clicked(dict(
                finalize=self.finalize_image_generated_by_llm
            ))

    def finalize_image_generated_by_llm(self, data):
        """
        Callback function to be called after the image has been generated.
        """

        # Create a message to be sent to the user as a chatbot message
        image_generated_message = dict(
            message="Your image has been generated",
            is_first_message=True,
            is_end_of_message=True,
            name=self.chatbot.name,
            action=LLMActionType.GENERATE_IMAGE
        )

        self.emit_signal(SignalCode.TOGGLE_SD_SIGNAL, dict(
            callback=lambda d: self.emit_signal(SignalCode.LOAD_NON_SD_MODELS, dict(
                callback=lambda d: self.emit_signal(
                    SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                    image_generated_message
                )
            ))
        ))
    ##########################################################################
    # End LLM Generated Image handlers
    ##########################################################################

    def _set_chatbot_mood(self, mood=None):
        self.ui.mood_label.setText(mood if mood else self.conversation.bot_mood if self.conversation else "")

    def handle_generate_image_from_image(self, image):
        pass

    def on_load_conversation(self, data):
        self.conversation = data["conversation"]
        self._set_chatbot_mood()
        self.ui.generator_form_tabs.setCurrentIndex(1)

    def toggle_secondary_prompts(self):
        if self.generator_settings.version != StableDiffusionVersion.SDXL1_0.value:
            self.ui.croops_coord_top_left_groupbox.hide()
        else:
            self.ui.croops_coord_top_left_groupbox.show()

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

    def do_generate(self, data=None):
        if data:
            finalize = data.get("finalize", None)
            if finalize:
                data = dict(
                    callback=finalize
                )
            else:
                data = None
        self.emit_signal(SignalCode.DO_GENERATE_SIGNAL, data)

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

    def handle_generate_button_clicked(self, data=None):
        self.start_progress_bar()
        self.generate(data)

    @Slot()
    def handle_interrupt_button_clicked(self):
        self.emit_signal(SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL)

    def generate(self, data=None):
        if self.generator_settings.random_seed:
            self.seed = random_seed()
        self.do_generate(data)
        self.seed_override = None

    def do_generate_image(self):
        time.sleep(0.1)
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

    def on_model_status_changed_signal(self, data):
        if data["model"] is ModelType.SD:
            if data["status"] is not ModelStatus.LOADING:
                self.stop_progress_bar(do_clear=True)
                self.ui.generate_button.setEnabled(True)
                self.ui.interrupt_button.setEnabled(True)
            else:
                self.start_progress_bar()
                self.ui.generate_button.setEnabled(False)
                self.ui.interrupt_button.setEnabled(False)

    def showEvent(self, event):
        super().showEvent(event)
        self.activate_ai_mode()
        self.set_form_values()
        self.toggle_secondary_prompts()
        self.initialized = True
        self.thread.start()
        self._set_chatbot_mood()

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
        self.ui.crops_coord_top_left_x.setText(str(self.generator_settings.crops_coord_top_left["x"]))
        self.ui.crops_coord_top_left_y.setText(str(self.generator_settings.crops_coord_top_left["y"]))

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

    def stop_progress_bar(self, do_clear=False):
        progressbar = self.ui.progress_bar
        if not progressbar:
            return
        progressbar.setRange(0, 100)
        if do_clear:
            progressbar.setValue(0)
            progressbar.setFormat("")
        else:
            progressbar.setValue(100)
            progressbar.setFormat("Complete")

    def _set_keyboard_shortcuts(self):
        generate_image_key = ShortcutKeys.objects.filter_by(
            display_name="Generate Image"
        ).first()
        interrupt_key = ShortcutKeys.objects.filter_by(
            display_name="Interrupt"
        ).first()
        if generate_image_key:
            self.ui.generate_button.setShortcut(generate_image_key.key)
            self.ui.generate_button.setToolTip(f"{generate_image_key.display_name} ({generate_image_key.text})")
        if interrupt_key:
            self.ui.interrupt_button.setShortcut(interrupt_key.key)
            self.ui.interrupt_button.setToolTip(f"{interrupt_key.display_name} ({interrupt_key.text})")
        
