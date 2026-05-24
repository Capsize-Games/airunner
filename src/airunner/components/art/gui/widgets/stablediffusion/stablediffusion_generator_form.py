from typing import Dict
import json
import re
import time

from PySide6.QtCore import (
    Signal,
    QRect,
    QThread,
    QObject,
    Slot,
    QSettings,
)
from PySide6.QtWidgets import QApplication, QWidget

from airunner.components.application.data import ShortcutKeys
from airunner.components.model_management import ModelResourceManager
from airunner.components.model_management.types import ModelState
from airunner.enums import (
    normalize_art_version,
    SignalCode,
    GeneratorSection,
    ModelStatus,
    ModelType,
    StableDiffusionVersion,
)
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.utils.application import random_seed
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.art.gui.widgets.stablediffusion.templates.stablediffusion_generator_form_ui import (
    Ui_stablediffusion_generator_form,
)
from airunner.components.art.gui.widgets.stablediffusion.prompt_container_widget import (
    PromptContainerWidget,
)
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)


class SaveGeneratorSettingsWorker(
    MediatorMixin,
    SettingsMixin,
    QObject,
):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self._running = True
        self.current_prompt_value = None
        self.current_negative_prompt_value = None
        self.current_secondary_prompt_value = None
        self.current_secondary_negative_prompt_value = None

    def stop(self) -> None:
        """Stop the settings worker loop."""
        self._running = False

    def run(self):
        do_update_settings = False
        while self._running:
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

            if do_update_settings:
                do_update_settings = False
                # Update individual fields using the proper update methods
                self.parent.update_generator_settings(
                    prompt=self.current_prompt_value
                )
                self.parent.update_generator_settings(
                    negative_prompt=self.current_negative_prompt_value
                )
                self.parent.update_generator_settings(
                    second_prompt=self.current_secondary_prompt_value
                )
                self.parent.update_generator_settings(
                    second_negative_prompt=self.current_secondary_negative_prompt_value,
                )

            time.sleep(0.1)


class StableDiffusionGeneratorForm(BaseWidget):
    widget_class_ = Ui_stablediffusion_generator_form
    changed_signal = Signal(str, object)
    _prompt_containers: Dict[str, QWidget] = {}
    icons = [
        ("chevron-up", "generate_button"),
        ("circle-stop", "interrupt_button"),
        ("circle", "infinite_images_button"),
    ]
    _splitters = ["generator_form_splitter"]

    def __init__(self, *args, **kwargs):
        self._pending_llm_image = None
        self.signal_handlers = {
            SignalCode.SD_GENERATE_IMAGE_SIGNAL: self.on_generate_image_signal,
            SignalCode.APPLICATION_STOP_SD_PROGRESS_BAR_SIGNAL: self.on_stop_image_generator_progress_bar_signal,
            SignalCode.SD_PROGRESS_SIGNAL: self.on_progress_signal,
            SignalCode.GENERATOR_FORM_UPDATE_VALUES_SIGNAL: self.set_form_values,
            SignalCode.LLM_IMAGE_PROMPT_GENERATED_SIGNAL: self.on_llm_image_prompt_generated_signal,
            SignalCode.GENERATE_IMAGE_FROM_IMAGE_SIGNAL: self.handle_generate_image_from_image,
            SignalCode.DO_GENERATE_IMAGE_FROM_IMAGE_SIGNAL: self.do_generate_image_from_image_signal_handler,
            SignalCode.SD_LOAD_PROMPT_SIGNAL: self.on_load_saved_stablediffuion_prompt_signal,
            SignalCode.BOT_MOOD_UPDATED: self.on_bot_mood_updated,
            SignalCode.KEYBOARD_SHORTCUTS_UPDATED: self.on_keyboard_shortcuts_updated,
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL: self.on_model_status_changed_signal,
            SignalCode.CLEAR_PROMPTS: self.clear_prompts,
            SignalCode.WIDGET_ELEMENT_CHANGED: self.on_widget_element_changed,
            SignalCode.SD_ADDITIONAL_PROMPT_DELETE_SIGNAL: self.on_delete_prompt_clicked,
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: self.on_application_settings_changed,
        }
        super().__init__(*args, **kwargs)
        self.seed_override = None
        self.parent = None
        self.initialized = False
        self._generation_in_progress = False
        self._backend_progress_started = False
        self._waiting_for_backend_progress = False
        self._busy_progress_models = set()
        self.thread = QThread()
        self.worker = SaveGeneratorSettingsWorker(parent=self)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._stop_worker_thread)
        self._sd_version = normalize_art_version(
            self.generator_settings.version
        )
        self._toggle_sdxl_form_elements()
        self.ui.infinite_images_button.blockSignals(True)
        self.ui.infinite_images_button.setChecked(
            self.generator_settings.generate_infinite_images
            if self.generator_settings.generate_infinite_images is not None
            else False
        )
        self.ui.infinite_images_button.blockSignals(False)
        self._set_progress_bar_idle()
        self._set_generation_button_visibility(False)
        self._initialize_image_mode()

    def _set_generation_button_visibility(
        self, is_generating: bool
    ) -> None:
        """Show only the active action button for art generation."""
        ui = getattr(self, "ui", None)
        if ui is None:
            return

        generate_button = getattr(ui, "generate_button", None)
        interrupt_button = getattr(ui, "interrupt_button", None)

        if generate_button is not None:
            generate_button.setVisible(not is_generating)
        if interrupt_button is not None:
            interrupt_button.setVisible(is_generating)

    @property
    def is_sd_xl_or_turbo(self) -> bool:
        return (
            self._sd_version == StableDiffusionVersion.SDXL1_0.value
            or self._sd_version == StableDiffusionVersion.SDXL_TURBO.value
        )

    @property
    def uses_negative_prompt(self) -> bool:
        """Check if the current model version uses negative prompts.

        Z-Image models don't use negative prompts.
        """
        no_negative_prompt_versions = (
            StableDiffusionVersion.Z_IMAGE_TURBO.value,
        )
        return self._sd_version not in no_negative_prompt_versions

    @property
    def supports_compel(self) -> bool:
        """Check if the current model version supports compel (additional prompts).

        Z-Image models don't support compel.
        """
        no_compel_versions = (
            StableDiffusionVersion.Z_IMAGE_TURBO.value,
        )
        return self._sd_version not in no_compel_versions

    @Slot()
    def on_image_mode_combobox_currentIndexChanged(self):
        index = self.ui.image_mode_combobox.currentIndex()
        if index == 0:
            self._enable_text_to_image_mode()
        elif index == 1:
            self._enable_image_to_image_mode()
        elif index == 2:
            self._enable_inpaint_mode()

    def _initialize_image_mode(self) -> None:
        if self.outpaint_settings.enabled:
            index = 2
            self._set_image_mode_widgets(False, True)
            self._set_input_mode_state(False, True, emit_signal=False)
        elif self.image_to_image_settings.enabled:
            index = 1
            self._set_image_mode_widgets(True, False)
            self._set_input_mode_state(True, False, emit_signal=False)
        else:
            index = 0
            self._set_image_mode_widgets(False, False)
            self._set_input_mode_state(False, False, emit_signal=False)

        self.ui.image_mode_combobox.blockSignals(True)
        self.ui.image_mode_combobox.setCurrentIndex(index)
        self.ui.image_mode_combobox.blockSignals(False)

    def _set_image_mode_widgets(
        self,
        show_image_to_image: bool,
        show_inpaint: bool,
    ) -> None:
        self.ui.image_to_image_settings.setVisible(show_image_to_image)
        self.ui.inpaint_settings.setVisible(show_inpaint)

    def _set_input_mode_state(
        self,
        image_to_image_enabled: bool,
        inpaint_enabled: bool,
        emit_signal: bool = True,
    ) -> None:
        image_updated = self._update_input_mode_enabled(
            "image_to_image_settings", image_to_image_enabled
        )
        inpaint_updated = self._update_input_mode_enabled(
            "outpaint_settings", inpaint_enabled
        )
        if emit_signal:
            self._emit_input_mode_change(
                "image_to_image_settings",
                image_to_image_enabled,
                image_updated,
            )
            self._emit_input_mode_change(
                "outpaint_settings",
                inpaint_enabled,
                inpaint_updated,
            )

    def _update_input_mode_enabled(
        self, settings_key: str, enabled: bool
    ) -> bool:
        current_enabled = getattr(getattr(self, settings_key), "enabled", False)
        if current_enabled == enabled:
            return False
        if settings_key == "image_to_image_settings":
            self.update_image_to_image_settings(enabled=enabled)
        else:
            self.update_outpaint_settings(enabled=enabled)
        return True

    def _emit_input_mode_change(
        self, settings_key: str, enabled: bool, changed: bool
    ) -> None:
        if not changed:
            return
        self.api.art.canvas.input_image_changed(
            settings_key,
            "enabled",
            enabled,
        )

    def _enable_text_to_image_mode(self):
        self._set_image_mode_widgets(False, False)
        self._set_input_mode_state(False, False)

    def _enable_image_to_image_mode(self):
        self._set_image_mode_widgets(True, False)
        self._set_input_mode_state(True, False)

    def _enable_inpaint_mode(self):
        self._set_image_mode_widgets(False, True)
        self._set_input_mode_state(False, True)

    @Slot()
    def on_generate_button_clicked(self):
        # Validate if generation can proceed
        from airunner.components.model_management import ModelResourceManager
        from PySide6.QtWidgets import QMessageBox

        resource_manager = ModelResourceManager()
        can_generate, reason = resource_manager.can_perform_operation(
            "text_to_image", self.generator_settings.model_name
        )

        if not can_generate:
            QMessageBox.warning(
                self,
                "Application Busy",
                f"Cannot generate image:\n\n{reason}\n\n"
                f"Please wait for the current operation to complete.",
            )
            return

        self.handle_generate_button_clicked()

    @Slot()
    def on_interrupt_button_clicked(self):
        self._set_generation_button_visibility(False)
        self.api.art.canvas.interrupt_image_generation()

    def on_delete_prompt_clicked(self, data: Dict):
        prompt_id = data.get("prompt_id", None)
        if prompt_id is None:
            self.logger.error(f"Unable to delete prompt")
            return
        prompt_container = self._prompt_containers[prompt_id]
        self.ui.additional_prompts_container_layout.removeWidget(
            prompt_container
        )
        prompt_container.deleteLater()
        self._prompt_containers.pop(prompt_id)

        # Save the updated prompt containers after deletion
        self.save_prompt_containers_to_settings()

    def on_application_settings_changed(self, data: Dict):
        if data.get("setting_name") == "generator_settings":
            self.on_widget_element_changed(data)
            # if data.get("column_name") in ("use_compel",):
            #     self._toggle_compel_form_elements(data.get("value", True))

    def on_widget_element_changed(self, data: Dict):
        # self._toggle_compel_form_elements(self.generator_settings.use_compel)
        column = data.get("element", None) or data.get("column_name", None)
        val = data.get("value", None)

        if column in ("use_compel",):
            self._toggle_compel_form_elements(val)
        elif column in ("sd_version", "version"):
            self._sd_version = normalize_art_version(val)
            self._toggle_sdxl_form_elements()

    def _toggle_compel_form_elements(self, value: bool):
        self.logger.debug("Toggle compel form elements")
        # Iterate over all widgets in the layout and enable/disable them
        for i in range(self.ui.additional_prompts_container_layout.count()):
            widget = self.ui.additional_prompts_container_layout.itemAt(
                i
            ).widget()
            if widget:
                widget.show() if value else widget.hide()

    def _toggle_sdxl_form_elements(self):
        if self.is_sd_xl_or_turbo:
            self.ui.sdxl_settings_container.show()
            self.ui.secondary_prompt.show()
            self.ui.secondary_negative_prompt.show()
        else:
            self.ui.sdxl_settings_container.hide()
            self.ui.secondary_prompt.hide()
            self.ui.secondary_negative_prompt.hide()

        # Toggle negative prompt visibility based on model version
        self._toggle_negative_prompt_visibility()

        # Toggle add prompt button visibility based on compel support
        self._toggle_add_prompt_button_visibility()

    def _toggle_negative_prompt_visibility(self):
        """Show/hide negative prompt based on whether the model uses it.

        Z-Image models don't use negative prompts.
        """
        if self.uses_negative_prompt:
            self.ui.layoutWidget1.show()
        else:
            self.ui.layoutWidget1.hide()

    def _toggle_add_prompt_button_visibility(self):
        """Show/hide add prompt button based on whether the model supports compel.

        Z-Image models don't support compel, so the add prompt button should
        be hidden for these models.
        """
        if self.supports_compel:
            self.ui.add_prompt_button.show()
        else:
            self.ui.add_prompt_button.hide()
            # Also hide any existing additional prompt containers
            self._toggle_compel_form_elements(False)

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
    def seed(self):
        return self.generator_settings.seed

    @seed.setter
    def seed(self, val):
        self.update_generator_settings(seed=val)

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

    def on_keyboard_shortcuts_updated(self):
        self._set_keyboard_shortcuts()

    def on_bot_mood_updated(self, data):
        pass

    def on_generate_image_signal(self, _data):
        self.handle_generate_button_clicked()

    def on_stop_image_generator_progress_bar_signal(self, data: Dict):
        data = data or {}
        self.stop_progress_bar(data.get("do_clear", False))

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
        # Extract payload and update UI/settings first to avoid races
        msg = data["message"]
        self.update_application_settings(working_width=msg["width"])
        self.update_application_settings(working_height=msg["height"])
        self.update_generator_settings(image_preset=msg.get("image_type", ""))

        prompt = msg.get("prompt", "")
        secondary_prompt = msg.get("second_prompt", "")

        # Update UI fields immediately
        self.ui.prompt.setPlainText(prompt)
        self.ui.secondary_prompt.setPlainText(secondary_prompt)

        # Ensure infinite images is off
        if self.ui.infinite_images_button.isChecked():
            self.ui.infinite_images_button.blockSignals(True)
            self.ui.infinite_images_button.setChecked(False)
            self.ui.infinite_images_button.blockSignals(False)
            self.update_generator_settings(generate_infinite_images=False)

        # Generate directly - ModelResourceManager will handle model swapping
        gen_data = {
            "prompt": prompt,
            "second_prompt": secondary_prompt,
        }
        self.handle_generate_button_clicked(gen_data)

    # Defer actual generation to unload_llm_callback so we can inject finalize

    def unload_llm_callback(self, _data: dict = None):
        """
        Callback function to be called after the LLM has been unloaded.
        """
        # SD has been loaded by the load balancer; trigger generation now with finalize
        # and the exact prompts we stashed to avoid any race with UI/settings writes.
        gen_data = {
            "finalize": self.finalize_image_generated_by_llm,
        }
        if hasattr(self, "_pending_llm_image") and self._pending_llm_image:
            gen_data.update(self._pending_llm_image)
        self.handle_generate_button_clicked(gen_data)

    def finalize_image_generated_by_llm(self, _data):
        """
        Callback function to be called after the image has been generated.

        ModelResourceManager will automatically handle model swapping as needed
        when the LLM is used next, so we can directly call the finalize method.
        """
        self.api.llm.finalize_image_generated_by_llm(_data)

    ##########################################################################
    # End LLM Generated Image handlers
    ##########################################################################

    def connect_prompt_container_signals(self, prompt_container):
        """Connects the textChanged signals of a prompt container to save settings on edit."""
        prompt_container.ui.prompt.textChanged.connect(
            self.on_additional_prompt_text_changed
        )
        prompt_container.ui.secondary_prompt.textChanged.connect(
            self.on_additional_prompt_text_changed
        )

    def on_additional_prompt_text_changed(self):
        """Slot to save prompt containers when any additional prompt text is changed."""
        self.save_prompt_containers_to_settings()

    @Slot()
    def on_add_prompt_button_clicked(self):
        additional_prompts_container_layout = (
            self.ui.additional_prompts_container_layout
        )
        prompt_container = PromptContainerWidget()
        prompt_container.prompt_id = len(self._prompt_containers.keys())
        additional_prompts_container_layout.addWidget(prompt_container)

        # store prompt container in self._prompt_containers
        self._prompt_containers[prompt_container.prompt_id] = prompt_container

        # Connect signals for saving on text change
        self.connect_prompt_container_signals(prompt_container)

        # Save the updated prompt containers
        self.save_prompt_containers_to_settings()

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

    def do_generate_image_from_image_signal_handler(self, _data):
        self.do_generate()

    def _build_generate_request(self, data=None):
        data = data or {}
        callback = data.get("finalize", None)
        print("*"*100)
        print("Building image request for generation with data:")
        additional_prompts = [
            {
                "prompt": container.get_prompt(),
                "prompt_secondary": container.get_prompt_secondary(),
            }
            for _prompt_id, container in self._prompt_containers.items()
        ]
        print("*"*100)
        print("calling api.art.canvas.create_image_request with additional_prompts:")
        return self.api.art.canvas.create_image_request(
            additional_prompts=additional_prompts, callback=callback
        )

    @staticmethod
    def _uses_loaded_generation_progress(image_request) -> bool:
        model_path = str(getattr(image_request, "model_path", "") or "").strip()
        if not model_path:
            return False
        resource_manager = ModelResourceManager()
        return resource_manager.get_model_state(model_path) is ModelState.LOADED

    def do_generate(self, data=None):
        print("*"*100)
        print("stablediffusion_generator_form.do_generate() called")
        data = data or {}
        image_request = data.get("image_request")
        if image_request is None:
            print("*"*100)
            print("Calling _build_generate_request to construct image request for generation")
            image_request = self._build_generate_request(data)
        print("*"*100)
        print(f"calling api.art.send_request with image_request: {image_request}")
        self.api.art.send_request(image_request=image_request)

    @Slot()
    def on_save_prompts_button_clicked(self):
        self.api.art.save_prompt(
            prompt=self.ui.prompt.toPlainText(),
            negative_prompt=self.ui.negative_prompt.toPlainText(),
            secondary_prompt=self.ui.secondary_prompt.toPlainText(),
            secondary_negative_prompt=self.ui.secondary_negative_prompt.toPlainText(),
        )

    def handle_generate_button_clicked(self, data=None):
        request_data = dict(data or {})
        image_request = request_data.get("image_request")
        if image_request is None:
            try:
                image_request = self._build_generate_request(request_data)
            except Exception:
                image_request = None
            if image_request is not None:
                request_data["image_request"] = image_request

        self._generation_in_progress = True
        self._backend_progress_started = False
        self._waiting_for_backend_progress = True
        self._set_generation_button_visibility(True)
        if self._uses_loaded_generation_progress(image_request):
            self.set_progress_bar_value(0)
        else:
            self.start_progress_bar()
        self.generate(request_data or None)

    @Slot(bool)
    def on_infinite_images_button_toggled(self, val: bool):
        self.update_generator_settings(generate_infinite_images=val)

    @Slot(str)
    def on_target_size_width_textChanged(self, val: str):
        val = 0 if val == "" or val is None else val
        target_size = self.generator_settings.target_size
        target_size = target_size or {}
        target_size["width"] = int(val)
        self.update_generator_settings(target_size=target_size)

    @Slot(str)
    def on_target_size_height_textChanged(self, val: str):
        val = 0 if val == "" or val is None else val
        target_size = self.generator_settings.target_size
        target_size = target_size or {}
        target_size["height"] = int(val)
        self.update_generator_settings(target_size=target_size)

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
            "use_tiled_vae": self.memory_settings.use_tiled_vae,
            "use_tome_sd": self.memory_settings.use_tome_sd,
            "tome_sd_ratio": self.memory_settings.tome_sd_ratio,
        }

    def handle_progress_bar(self, message):
        step = message.get("step")
        total = message.get("total")
        if step is None or total in (None, 0):
            return

        if int(step) <= 0 and not getattr(
            self,
            "_backend_progress_started",
            False,
        ):
            return

        self._waiting_for_backend_progress = False
        self._backend_progress_started = True

        try:
            current = step / total
        except ZeroDivisionError:
            current = 0
        value = int(current * 100)
        if value >= 100:
            self.set_progress_bar_value(100)
            self.ui.progress_bar.setFormat("Processing")
        else:
            self.set_progress_bar_value(value)

    def set_progress_bar_value(self, value):
        progressbar = self.ui.progress_bar
        if not progressbar:
            return
        if progressbar.maximum() == 0:
            progressbar.setRange(0, 100)
        progressbar.setFormat("Generating %p%")
        progressbar.setValue(value)
        QApplication.processEvents()

    def start_progress_bar(self):
        progressbar = self.ui.progress_bar
        progressbar.setFormat("Preparing...")
        progressbar.setRange(0, 0)
        progressbar.show()
        QApplication.processEvents()

    def _set_progress_bar_idle(self):
        progressbar = getattr(self.ui, "progress_bar", None)
        if not progressbar:
            return
        progressbar.setRange(0, 100)
        progressbar.setValue(0)
        progressbar.setFormat("")

    def _progress_models(self):
        models = getattr(self, "_busy_progress_models", None)
        if models is None:
            models = set()
            self._busy_progress_models = models
        return models

    @staticmethod
    def _tracks_progress_model(model):
        return model in (ModelType.SD, ModelType.RMBG)

    def _handle_loading_progress_model(self, model):
        self._progress_models().add(model)
        should_start = model is ModelType.RMBG or (
            not self._generation_in_progress
            or not self._backend_progress_started
        )
        if should_start:
            self.start_progress_bar()
        if model is ModelType.SD:
            self.ui.generate_button.setEnabled(False)
            self.ui.interrupt_button.setEnabled(False)

    def _handle_idle_progress_model(self, model):
        self._progress_models().discard(model)
        if model is ModelType.SD:
            self.ui.generate_button.setEnabled(True)
            self.ui.interrupt_button.setEnabled(True)
        if self._waiting_for_backend_progress:
            return
        if getattr(self, "_generation_in_progress", False):
            return
        if self._progress_models():
            return
        self._set_progress_bar_idle()

    def on_model_status_changed_signal(self, data):
        model = data.get("model")
        if not self._tracks_progress_model(model):
            return
        if data.get("status") is ModelStatus.LOADING:
            self._handle_loading_progress_model(model)
            return
        self._handle_idle_progress_model(model)

    def showEvent(self, event):
        if not self.initialized:
            super().showEvent(event)
            self.set_form_values()
            self.initialized = True
            self.thread.start()

            # Restore prompt containers when widget is shown
            self.restore_prompt_containers_from_settings()

    def closeEvent(self, event):
        """Stop the background settings worker before teardown."""
        self._stop_worker_thread()
        super().closeEvent(event)

    def _stop_worker_thread(self) -> None:
        """Shut down the prompt settings worker thread safely."""
        if not hasattr(self, "thread") or not self.thread.isRunning():
            return
        self.worker.stop()
        self.thread.quit()
        if self.thread.wait(1000):
            return
        self.thread.terminate()
        self.thread.wait(1000)

    def set_form_values(self, _data=None):
        self.ui.prompt.blockSignals(True)
        self.ui.negative_prompt.blockSignals(True)
        self.ui.secondary_prompt.blockSignals(True)
        self.ui.secondary_negative_prompt.blockSignals(True)

        self.ui.prompt.setPlainText(self.generator_settings.prompt)
        self.ui.negative_prompt.setPlainText(
            self.generator_settings.negative_prompt
        )
        self.ui.secondary_prompt.setPlainText(
            self.generator_settings.second_prompt
        )
        self.ui.secondary_negative_prompt.setPlainText(
            self.generator_settings.second_negative_prompt
        )

        self.ui.prompt.blockSignals(False)
        self.ui.negative_prompt.blockSignals(False)
        self.ui.secondary_prompt.blockSignals(False)
        self.ui.secondary_negative_prompt.blockSignals(False)

    def clear_prompts(self):
        self.ui.prompt.setPlainText("")
        self.ui.negative_prompt.setPlainText("")
        self.ui.secondary_prompt.setPlainText("")
        self.ui.secondary_negative_prompt.setPlainText("")

    def stop_progress_bar(self, do_clear=False):
        self._generation_in_progress = False
        self._backend_progress_started = False
        self._waiting_for_backend_progress = False
        self._set_generation_button_visibility(False)
        progressbar = self.ui.progress_bar
        if not progressbar:
            return
        if do_clear:
            self._set_progress_bar_idle()
        else:
            progressbar.setRange(0, 100)
            progressbar.setValue(100)
            progressbar.setFormat("Complete")

    def _set_keyboard_shortcuts(self):
        generate_image_key = ShortcutKeys.objects.filter_by_first(
            display_name="Generate Image"
        )
        interrupt_key = ShortcutKeys.objects.filter_by_first(
            display_name="Interrupt"
        )
        if generate_image_key:
            self.ui.generate_button.setShortcut(generate_image_key.key)
            self.ui.generate_button.setToolTip(
                f"{generate_image_key.display_name} ({generate_image_key.text})"
            )
        if interrupt_key:
            self.ui.interrupt_button.setShortcut(interrupt_key.key)
            self.ui.interrupt_button.setToolTip(
                f"{interrupt_key.display_name} ({interrupt_key.text})"
            )

    def save_prompt_containers_to_settings(self):
        """Save all additional prompt containers to QSettings."""
        if not self.initialized:
            return

        settings = QSettings()
        settings.beginGroup("sd_additional_prompts")

        # Clear existing settings first
        settings.remove("")

        # Save the number of containers
        settings.setValue("count", len(self._prompt_containers))

        # Save each container's data
        for i, (prompt_id, container) in enumerate(
            self._prompt_containers.items()
        ):
            settings.setValue(f"prompt_{i}_id", prompt_id)
            settings.setValue(f"prompt_{i}_text", container.get_prompt())
            settings.setValue(
                f"prompt_{i}_text_secondary", container.get_prompt_secondary()
            )

        settings.endGroup()
        settings.sync()

    def restore_prompt_containers_from_settings(self):
        """Restore additional prompt containers from QSettings."""
        # Clear existing containers first
        for container in list(self._prompt_containers.values()):
            self.ui.additional_prompts_container_layout.removeWidget(container)
            container.deleteLater()
        self._prompt_containers.clear()

        settings = QSettings()
        settings.beginGroup("sd_additional_prompts")

        count = settings.value("count", 0, type=int)

        for i in range(count):
            prompt_id = settings.value(f"prompt_{i}_id", i, type=int)
            prompt_text = settings.value(f"prompt_{i}_text", "", type=str)
            prompt_text_secondary = settings.value(
                f"prompt_{i}_text_secondary", "", type=str
            )

            # Create and add the container
            prompt_container = PromptContainerWidget()
            prompt_container.prompt_id = prompt_id
            prompt_container.set_prompt(prompt_text)
            prompt_container.set_prompt_secondary(prompt_text_secondary)

            self.ui.additional_prompts_container_layout.addWidget(
                prompt_container
            )
            self._prompt_containers[prompt_id] = prompt_container

            # Connect signals for saving on text change
            self.connect_prompt_container_signals(prompt_container)

        settings.endGroup()
