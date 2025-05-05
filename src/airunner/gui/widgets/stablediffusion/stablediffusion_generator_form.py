from typing import Dict
import json
import re
import time

from PySide6.QtCore import Signal, QRect, QThread, QObject, Slot, QSettings
from PySide6.QtWidgets import QApplication, QWidget

from airunner.data.models import ShortcutKeys, AIModels
from airunner.enums import (
    QualityEffects,
    SignalCode,
    GeneratorSection,
    ImagePreset,
    StableDiffusionVersion,
    ModelStatus,
    ModelType,
    LLMActionType,
)
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.utils.application import random_seed
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.stablediffusion.templates.stablediffusion_generator_form_ui import (
    Ui_stablediffusion_generator_form,
)
from airunner.gui.widgets.stablediffusion.prompt_container_widget import (
    PromptContainerWidget,
)
from airunner.gui.windows.main.settings_mixin import SettingsMixin
from airunner.handlers.llm.llm_response import LLMResponse
from airunner.handlers.stablediffusion.image_request import ImageRequest
from airunner.utils.widgets import load_splitter_settings


class SaveGeneratorSettingsWorker(
    MediatorMixin,
    SettingsMixin,
    QObject,
):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.current_prompt_value = None
        self.current_negative_prompt_value = None
        self.current_secondary_prompt_value = None
        self.current_secondary_negative_prompt_value = None
        self.crops_coords_top_left_x = 0
        self.crops_coords_top_left_y = 0

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

            x = self.parent.ui.crops_coords_top_left_x.text()
            y = self.parent.ui.crops_coords_top_left_y.text()
            x = int(x) if x != "" else 0
            y = int(y) if y != "" else 0

            if self.crops_coords_top_left_x != x:
                self.crops_coords_top_left_x = x
                do_update_settings = True
            if self.crops_coords_top_left_y != y:
                self.crops_coords_top_left_y = y
                do_update_settings = True

            if do_update_settings:
                do_update_settings = False
                generator_settings = self.generator_settings
                generator_settings.prompt = self.current_prompt_value
                generator_settings.negative_prompt = (
                    self.current_negative_prompt_value
                )
                generator_settings.second_prompt = (
                    self.current_secondary_prompt_value
                )
                generator_settings.second_negative_prompt = (
                    self.current_secondary_negative_prompt_value
                )
                generator_settings.crops_coords_top_left = {
                    "x": self.crops_coords_top_left_x,
                    "y": self.crops_coords_top_left_y,
                }
                generator_settings.save()

            time.sleep(0.1)


class StableDiffusionGeneratorForm(BaseWidget):
    widget_class_ = Ui_stablediffusion_generator_form
    changed_signal = Signal(str, object)
    _prompt_containers: Dict[str, QWidget] = {}
    icons = [
        ("chevron-up", "generate_button"),
        ("x-circle", "interrupt_button"),
    ]

    def __init__(self, *args, **kwargs):
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
        self.thread = QThread()
        self.worker = SaveGeneratorSettingsWorker(parent=self)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self._sd_version: str = self.generator_settings.version
        self._toggle_sdxl_form_elements()
        self.toggle_microconditioning(
            self.generator_settings.quality_effects
            == QualityEffects.CUSTOM.value
        )
        self.ui.quality_effects.blockSignals(True)
        self.ui.quality_effects.clear()
        self.ui.quality_effects.addItems(
            [effect.value for effect in QualityEffects]
        )
        self.ui.quality_effects.setCurrentText(
            self.generator_settings.quality_effects
        )
        self.ui.quality_effects.blockSignals(False)

    @property
    def is_sd_xl_or_turbo(self) -> bool:
        return (
            self._sd_version == StableDiffusionVersion.SDXL1_0.value
            or self._sd_version == StableDiffusionVersion.SDXL_TURBO.value
        )

    @Slot()
    def on_generate_button_clicked(self):
        self.handle_generate_button_clicked()

    @Slot()
    def on_interrupt_button_clicked(self):
        self.api.art.interrupt_image_generation()

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
            if data.get("column_name") in ("use_compel",):
                self._toggle_compel_form_elements(data.get("value", True))

    def on_widget_element_changed(self, data: Dict):
        self._toggle_compel_form_elements(self.generator_settings.use_compel)

        if data.get("element") in ("sd_version",):
            self._sd_version = data.get("version")
            self._toggle_sdxl_form_elements()

    def _toggle_compel_form_elements(self, value: bool):
        self.logger.info("Toggle compel form elements")
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
            self.ui.original_size_width.blockSignals(True)
            self.ui.original_size_height.blockSignals(True)
            self.ui.negative_original_size_width.blockSignals(True)
            self.ui.negative_original_size_height.blockSignals(True)
            self.ui.target_size_width.blockSignals(True)
            self.ui.target_size_height.blockSignals(True)
            self.ui.negative_target_size_width.blockSignals(True)
            self.ui.negative_target_size_height.blockSignals(True)
            self.ui.crops_coords_top_left_x.blockSignals(True)
            self.ui.crops_coords_top_left_y.blockSignals(True)
            self.ui.negative_crops_coord_top_left_x.blockSignals(True)
            self.ui.negative_crops_coord_top_left_y.blockSignals(True)
            self.ui.original_size_width.setText(
                str(
                    (self.generator_settings.original_size or {}).get(
                        "width", 0
                    )
                )
            )
            self.ui.original_size_height.setText(
                str(
                    (self.generator_settings.original_size or {}).get(
                        "height", 0
                    )
                )
            )
            self.ui.negative_original_size_width.setText(
                str(
                    (self.generator_settings.negative_original_size or {}).get(
                        "width", 0
                    )
                )
            )
            self.ui.negative_original_size_height.setText(
                str(
                    (self.generator_settings.negative_original_size or {}).get(
                        "height", 0
                    )
                )
            )
            self.ui.target_size_width.setText(
                str(
                    (self.generator_settings.target_size or {}).get("width", 0)
                )
            )
            self.ui.target_size_height.setText(
                str(
                    (self.generator_settings.target_size or {}).get(
                        "height", 0
                    )
                )
            )
            self.ui.negative_target_size_width.setText(
                str(
                    (self.generator_settings.negative_target_size or {}).get(
                        "width", 0
                    )
                )
            )
            self.ui.negative_target_size_height.setText(
                str(
                    (self.generator_settings.negative_target_size or {}).get(
                        "height", 0
                    )
                )
            )
            self.ui.crops_coords_top_left_x.setText(
                str(
                    (self.generator_settings.crops_coords_top_left or {}).get(
                        "x", 0
                    )
                )
            )
            self.ui.crops_coords_top_left_y.setText(
                str(
                    (self.generator_settings.crops_coords_top_left or {}).get(
                        "y", 0
                    )
                )
            )
            self.ui.negative_crops_coord_top_left_x.setText(
                str(
                    (
                        self.generator_settings.negative_crops_coords_top_left
                        or {}
                    ).get("x", 0)
                )
            )
            self.ui.negative_crops_coord_top_left_y.setText(
                str(
                    (
                        self.generator_settings.negative_crops_coords_top_left
                        or {}
                    ).get("y", 0)
                )
            )
            self.ui.original_size_width.blockSignals(False)
            self.ui.original_size_height.blockSignals(False)
            self.ui.negative_original_size_width.blockSignals(False)
            self.ui.negative_original_size_height.blockSignals(False)
            self.ui.target_size_width.blockSignals(False)
            self.ui.target_size_height.blockSignals(False)
            self.ui.negative_target_size_width.blockSignals(False)
            self.ui.negative_target_size_height.blockSignals(False)
            self.ui.crops_coords_top_left_x.blockSignals(False)
            self.ui.crops_coords_top_left_y.blockSignals(False)
            self.ui.negative_crops_coord_top_left_x.blockSignals(False)
            self.ui.negative_crops_coord_top_left_y.blockSignals(False)
        else:
            self.ui.sdxl_settings_container.hide()
            self.ui.secondary_prompt.hide()
            self.ui.secondary_negative_prompt.hide()

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

    def on_keyboard_shortcuts_updated(self):
        self._set_keyboard_shortcuts()

    def on_bot_mood_updated(self, data):
        pass

    def on_generate_image_signal(self, _data):
        self.handle_generate_button_clicked()

    def on_stop_image_generator_progress_bar_signal(self, data: Dict):
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
        # Unload non-Stable Diffusion models
        self.api.art.unload_non_sd(callback=self.unload_llm_callback)
        # Set the prompts in the generator form UI
        data = data["message"]
        self.update_application_settings("working_width", data["width"])
        self.update_application_settings("working_height", data["height"])
        self.update_generator_settings("image_preset", data.get("type", ""))
        prompt = data.get("prompt", None)
        secondary_prompt = data.get("secondary_prompt", None)
        self.ui.prompt.setPlainText(prompt)
        self.ui.secondary_prompt.setPlainText(secondary_prompt)

    def unload_llm_callback(self, _data: dict = None):
        """
        Callback function to be called after the LLM has been unloaded.
        """
        if not self.application_settings.sd_enabled:
            # If SD is not enabled, enable it and then emit a signal to generate the image
            # The callback function is handled by the signal handler for the SD_LOAD_SIGNAL.
            # The finalize function is a callback which is called after the image has been generated.
            self.logger.info(
                "Stable Diffusion is not enabled, enabling it now."
            )
            self.api.art.toggle_sd(
                enabled=True,
                callback=self.handle_generate_button_clicked,
                finalize=self.finalize_image_generated_by_llm,
            )
        else:
            # If SD is already enabled, emit a signal to generate the image.
            # The finalize function is a callback which is called after the image has been generated.
            self.logger.info(
                "Stable Diffusion is already enabled, generating the image."
            )
            self.handle_generate_button_clicked(
                dict(
                    enabled=True, finalize=self.finalize_image_generated_by_llm
                )
            )

    def finalize_image_generated_by_llm(self, _data):
        """
        Callback function to be called after the image has been generated.
        """
        self.api.art.toggle_sd(
            callback=lambda _d: self.load_non_sd(
                callback=lambda _d: self.api.send_llm_text_streamed_signal(
                    LLMResponse(
                        message="Your image has been generated",
                        is_first_message=True,
                        is_end_of_message=True,
                        name=self.chatbot.name,
                        action=LLMActionType.GENERATE_IMAGE,
                    )
                )
            ),
            enabled=False,
        )

    ##########################################################################
    # End LLM Generated Image handlers
    ##########################################################################

    @Slot()
    def handle_add_prompt_clicked(self):
        additional_prompts_container_layout = (
            self.ui.additional_prompts_container_layout
        )
        prompt_container = PromptContainerWidget()
        prompt_container.prompt_id = len(self._prompt_containers.keys())
        additional_prompts_container_layout.addWidget(prompt_container)

        # store prompt container in self._prompt_containers
        self._prompt_containers[prompt_container.prompt_id] = prompt_container

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

    def handle_image_presets_changed(self, val):
        self.update_generator_settings("image_preset", val)

    def do_generate_image_from_image_signal_handler(self, _data):
        self.do_generate()

    def do_generate(self, data=None):
        data = data or {}

        callback = data.get("finalize", None)

        # Update data with additional prompt data from self._prompt_containers
        additional_prompts = [
            {
                "prompt": container.get_prompt(),
                "prompt_secondary": container.get_prompt_secondary(),
            }
            for _prompt_id, container in self._prompt_containers.items()
        ]

        model_path = ""
        model_id = self.generator_settings.model
        if model_id is not None:
            aimodel = AIModels.objects.get(model_id)
            if aimodel is not None:
                model_path = model_path

        if model_path == "":
            if self.generator_settings.model is not None:
                aimodel = AIModels.objects.get(self.generator_settings.model)
            else:
                aimodel = AIModels.objects.first()

            if aimodel is not None:
                model_path = aimodel.path
                self.update_generator_settings("model", aimodel.id)

        image_request = ImageRequest(
            prompt=data.get("prompt", self.ui.prompt.toPlainText()),
            negative_prompt=data.get(
                "negative_prompt", self.ui.negative_prompt.toPlainText()
            ),
            second_prompt=data.get(
                "second_prompt", self.ui.secondary_prompt.toPlainText()
            ),
            second_negative_prompt=data.get(
                "second_negative_prompt",
                self.ui.secondary_negative_prompt.toPlainText(),
            ),
            crops_coords_top_left=self.generator_settings.crops_coords_top_left,
            negative_crops_coords_top_left=self.generator_settings.negative_crops_coords_top_left,
            pipeline_action=self.generator_settings.pipeline_action,
            generator_name=self.generator_name,
            random_seed=self.generator_settings.random_seed,
            model_path=model_path,
            scheduler=self.generator_settings.scheduler,
            version=self.generator_settings.version,
            use_compel=self.generator_settings.use_compel,
            steps=self.generator_settings.steps,
            ddim_eta=self.generator_settings.ddim_eta,
            scale=self.generator_settings.scale / 100,
            seed=self.seed,
            strength=self.generator_settings.strength / 100,
            n_samples=self.generator_settings.n_samples,
            clip_skip=self.generator_settings.clip_skip,
            width=self.application_settings.working_width,
            height=self.application_settings.working_height,
            target_size=self.generator_settings.target_size,
            original_size=self.generator_settings.original_size,
            negative_target_size=self.generator_settings.negative_target_size,
            negative_original_size=self.generator_settings.negative_original_size,
            lora_scale=self.generator_settings.lora_scale,
            additional_prompts=additional_prompts,
            callback=callback,
            image_preset=ImagePreset(self.generator_settings.image_preset),
            quality_effects=(
                QualityEffects(self.generator_settings.quality_effects)
                if self.generator_settings.quality_effects != ""
                and self.generator_settings.quality_effects is not None
                else QualityEffects.STANDARD
            ),
        )

        self.api.art.send_request(image_request=image_request)

    def action_clicked_button_save_prompts(self):
        self.api.art.save_prompt(
            prompt=self.ui.prompt.toPlainText(),
            negative_prompt=self.ui.negative_prompt.toPlainText(),
            secondary_prompt=self.ui.secondary_prompt.toPlainText(),
            secondary_negative_prompt=self.ui.secondary_negative_prompt.toPlainText(),
        )

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

    @Slot(str)
    def on_original_size_width_textChanged(self, val: str):
        val = 0 if val == "" or val is None else val
        original_size = self.generator_settings.original_size
        original_size = original_size or {}
        original_size["width"] = int(val)
        self.update_generator_settings("original_size", original_size)

    @Slot(str)
    def on_original_size_height_textChanged(self, val: str):
        val = 0 if val == "" or val is None else val
        original_size = self.generator_settings.original_size
        original_size = original_size or {}
        original_size["height"] = int(val)
        self.update_generator_settings("original_size", original_size)

    @Slot(str)
    def on_negative_original_size_width_textChanged(self, val: str):
        val = 0 if val == "" or val is None else val
        negative_original_size = self.generator_settings.negative_original_size
        negative_original_size = negative_original_size or {}
        negative_original_size["width"] = int(val)
        self.update_generator_settings(
            "negative_original_size", negative_original_size
        )

    @Slot(str)
    def on_negative_original_size_height_textChanged(self, val: str):
        val = 0 if val == "" or val is None else val
        negative_original_size = self.generator_settings.negative_original_size
        negative_original_size = negative_original_size or {}
        negative_original_size["height"] = int(val)
        self.update_generator_settings(
            "negative_original_size", negative_original_size
        )

    @Slot(str)
    def on_target_size_width_textChanged(self, val: str):
        val = 0 if val == "" or val is None else val
        target_size = self.generator_settings.target_size
        target_size = target_size or {}
        target_size["width"] = int(val)
        self.update_generator_settings("target_size", target_size)

    @Slot(str)
    def on_target_size_height_textChanged(self, val: str):
        val = 0 if val == "" or val is None else val
        target_size = self.generator_settings.target_size
        target_size = target_size or {}
        target_size["height"] = int(val)
        self.update_generator_settings("target_size", target_size)

    @Slot(str)
    def on_negative_target_size_width_textChanged(self, val: str):
        val = 0 if val == "" or val is None else val
        negative_target_size = self.generator_settings.negative_target_size
        negative_target_size = negative_target_size or {}
        negative_target_size["width"] = int(val)
        self.update_generator_settings(
            "negative_target_size", negative_target_size
        )

    @Slot(str)
    def on_negative_target_size_height_textChanged(self, val: str):
        val = 0 if val == "" or val is None else val
        negative_target_size = self.generator_settings.negative_target_size
        negative_target_size = negative_target_size or {}
        negative_target_size["height"] = int(val)
        self.update_generator_settings(
            "negative_target_size", negative_target_size
        )

    @Slot(str)
    def on_crops_coords_top_left_x_textChanged(self, val: str):
        val = 0 if val == "" or val is None else val
        crops_coords_top_left = self.generator_settings.crops_coords_top_left
        crops_coords_top_left = crops_coords_top_left or {}
        crops_coords_top_left["x"] = int(val)
        self.update_generator_settings(
            "crops_coords_top_left", crops_coords_top_left
        )

    @Slot(str)
    def on_crops_coords_top_left_y_textChanged(self, val: str):
        val = 0 if val == "" or val is None else val
        crops_coords_top_left = self.generator_settings.crops_coords_top_left
        crops_coords_top_left = crops_coords_top_left or {}
        crops_coords_top_left["y"] = int(val)
        self.update_generator_settings(
            "crops_coords_top_left", crops_coords_top_left
        )

    @Slot(str)
    def on_negative_crops_coord_top_left_x_textChanged(self, val: str):
        val = 0 if val == "" or val is None else val
        negative_crops_coords_top_left = (
            self.generator_settings.negative_crops_coords_top_left
        )
        negative_crops_coords_top_left = negative_crops_coords_top_left or {}
        negative_crops_coords_top_left["x"] = int(val)
        self.update_generator_settings(
            "negative_crops_coords_top_left", negative_crops_coords_top_left
        )

    @Slot(str)
    def on_negative_crops_coord_top_left_y_textChanged(self, val: str):
        val = 0 if val == "" or val is None else val
        negative_crops_coords_top_left = (
            self.generator_settings.negative_crops_coords_top_left
        )
        negative_crops_coords_top_left = negative_crops_coords_top_left or {}
        negative_crops_coords_top_left["y"] = int(val)
        self.update_generator_settings(
            "negative_crops_coords_top_left", negative_crops_coords_top_left
        )

    @Slot(bool)
    def on_use_refiner_checkbox_toggled(self, val: bool):
        self.update_generator_settings("use_refiner", val)

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
            "use_torch_compile": self.memory_settings.use_torch_compile,
            "use_tiled_vae": self.memory_settings.use_tiled_vae,
            "use_tome_sd": self.memory_settings.use_tome_sd,
            "tome_sd_ratio": self.memory_settings.tome_sd_ratio,
        }

    def handle_quality_effects_changed(self, val):
        self.update_generator_settings("quality_effects", val)
        self.toggle_microconditioning(val == QualityEffects.CUSTOM.value)

    def toggle_microconditioning(self, enabled: bool):
        self.ui.original_size_width.setEnabled(enabled)
        self.ui.original_size_height.setEnabled(enabled)
        self.ui.negative_original_size_width.setEnabled(enabled)
        self.ui.negative_original_size_height.setEnabled(enabled)
        self.ui.target_size_width.setEnabled(enabled)
        self.ui.target_size_height.setEnabled(enabled)
        self.ui.negative_target_size_width.setEnabled(enabled)
        self.ui.negative_target_size_height.setEnabled(enabled)

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
                current = step / total
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
        self.set_form_values()
        self.initialized = True
        self.thread.start()

        load_splitter_settings(self.ui, ["generator_form_splitter"])

        # Restore prompt containers when widget is shown
        self.restore_prompt_containers_from_settings()

    def hideEvent(self, event):
        """When widget is hidden, save prompt containers."""
        super().hideEvent(event)
        self.save_prompt_containers_to_settings()

    def closeEvent(self, event):
        """When widget is closed, save prompt containers."""
        self.save_prompt_containers_to_settings()
        super().closeEvent(event)

    def set_form_values(self, _data=None):
        self.ui.prompt.blockSignals(True)
        self.ui.negative_prompt.blockSignals(True)
        self.ui.secondary_prompt.blockSignals(True)
        self.ui.secondary_negative_prompt.blockSignals(True)
        self.ui.image_presets.blockSignals(True)
        self.ui.quality_effects.blockSignals(True)

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

        image_presets = [preset.value for preset in ImagePreset]
        self.ui.image_presets.addItems(image_presets)
        self.ui.image_presets.setCurrentIndex(
            self.ui.image_presets.findText(
                self.generator_settings.image_preset
            )
        )

        self.ui.quality_effects.setCurrentText(
            self.generator_settings.quality_effects
        )

        self.ui.prompt.blockSignals(False)
        self.ui.negative_prompt.blockSignals(False)
        self.ui.secondary_prompt.blockSignals(False)
        self.ui.secondary_negative_prompt.blockSignals(False)
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

        settings.endGroup()
