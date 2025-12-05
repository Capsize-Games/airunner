from typing import List, Optional
from PySide6.QtCore import Slot, Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QDialog,
    QVBoxLayout,
    QLabel,
    QCheckBox,
    QDialogButtonBox,
    QProgressDialog,
)

import torch

from airunner.components.art.data.ai_models import AIModels
from airunner.utils.vram_utils import (
    estimate_vram_from_path,
    get_available_precisions,
    PRECISION_DISPLAY_NAMES,
    is_precision_safe_for_vram,
)
from airunner.utils.model_dtype_utils import detect_model_dtype
from airunner.components.art.data.schedulers import Schedulers
from airunner.enums import (
    SignalCode,
    GeneratorSection,
    ImageGenerator,
    StableDiffusionVersion,
    Scheduler,
)
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.art.gui.widgets.stablediffusion.templates.stable_diffusion_settings_ui import (
    Ui_stable_diffusion_settings_widget,
)
from airunner.components.application.gui.windows.main.pipeline_mixin import (
    PipelineMixin,
)
from airunner.settings import AIRUNNER_ART_ENABLED
from airunner.utils.settings.get_qsettings import get_qsettings
from airunner.utils.model_utils.model_utils import (
    get_stable_diffusion_model_storage_path,
)
import threading
import os


# Versions that use FlowMatchEulerDiscreteScheduler (FLUX and Z-Image)
FLOW_MATCH_VERSIONS = (
    StableDiffusionVersion.FLUX_DEV.value,
    StableDiffusionVersion.FLUX_SCHNELL.value,
    StableDiffusionVersion.Z_IMAGE_TURBO.value,
    StableDiffusionVersion.Z_IMAGE_BASE.value,
)

# Mapping from version to generator_name
VERSION_TO_GENERATOR: dict[str, str] = {
    StableDiffusionVersion.FLUX_DEV.value: ImageGenerator.FLUX.value,
    StableDiffusionVersion.FLUX_SCHNELL.value: ImageGenerator.FLUX.value,
    StableDiffusionVersion.Z_IMAGE_TURBO.value: ImageGenerator.ZIMAGE.value,
    StableDiffusionVersion.Z_IMAGE_BASE.value: ImageGenerator.ZIMAGE.value,
    StableDiffusionVersion.SDXL1_0.value: ImageGenerator.STABLEDIFFUSION.value,
    StableDiffusionVersion.SDXL_TURBO.value: ImageGenerator.STABLEDIFFUSION.value,
    StableDiffusionVersion.SDXL_LIGHTNING.value: ImageGenerator.STABLEDIFFUSION.value,
    StableDiffusionVersion.SDXL_HYPER.value: ImageGenerator.STABLEDIFFUSION.value,
    StableDiffusionVersion.X4_UPSCALER.value: ImageGenerator.STABLEDIFFUSION.value,
}

# All flow-match scheduler options (for FLUX/Z-Image dropdown)
# Only includes schedulers that work correctly with flow-match models
FLOW_MATCH_SCHEDULERS = (
    Scheduler.FLOW_MATCH_EULER.value,
    Scheduler.FLOW_MATCH_LCM.value,
)

# Default flow-match scheduler
FLOW_MATCH_SCHEDULER_NAME = Scheduler.FLOW_MATCH_EULER.value

# Version-specific parameter constraints
VERSION_CONSTRAINTS = {
    StableDiffusionVersion.Z_IMAGE_TURBO.value: {
        "guidance_scale_max": 5.0,
        "steps_max": 20,
    },
    StableDiffusionVersion.Z_IMAGE_BASE.value: {
        "guidance_scale_max": 5.0,
        "steps_max": 50,
    },
    StableDiffusionVersion.FLUX_DEV.value: {
        "guidance_scale_max": 3.5,
        "steps_max": 50,
    },
    StableDiffusionVersion.FLUX_SCHNELL.value: {
        "guidance_scale_max": 3.5,
        "steps_max": 4,
    },
}


class StableDiffusionSettingsWidget(BaseWidget, PipelineMixin):
    widget_class_ = Ui_stable_diffusion_settings_widget

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.AI_MODELS_CREATE_SIGNAL: self.on_models_changed_signal,
            SignalCode.APPLICATION_MAIN_WINDOW_LOADED_SIGNAL: self.update_form,
        }
        super().__init__(*args, **kwargs)
        self._version: str = ""
        self._versions: List[str] = []
        self._models: List[AIModels] = []
        self._current_action: str = ""
        self.ui.custom_model.blockSignals(True)
        self.ui.custom_model.setText(self.generator_settings.custom_path)
        self.ui.custom_model.blockSignals(False)
        PipelineMixin.__init__(self)

        self._load_versions_combobox()
        self._load_pipelines_combobox()
        self._load_models_combobox()
        self._load_schedulers_combobox()
        self._load_precision_combobox()

    def showEvent(self, event):
        super().showEvent(event)
        self.update_form()

    def update_form(self):
        steps = self.generator_settings.steps
        scale = self.generator_settings.scale

        current_steps = self.get_form_element("steps_widget").property(
            "current_value"
        )
        current_scale = self.get_form_element("scale_widget").property(
            "current_value"
        )

        if steps != current_steps:
            self.get_form_element("steps_widget").setProperty(
                "current_value", steps
            )

        if scale != current_scale:
            self.get_form_element("scale_widget").setProperty(
                "current_value", scale
            )

        try:
            self.ui.seed_widget.setProperty(
                "generator_section", self.generator_settings.pipeline_action
            )
            self.ui.seed_widget.setProperty(
                "generator_name", ImageGenerator.FLUX.value
            )
            self.ui.ddim_eta_slider_widget.hide()
            self.ui.frames_slider_widget.hide()
        except RuntimeError as e:
            if AIRUNNER_ART_ENABLED:
                self.logger.error(f"Error updating form: {e}")

        try:
            self.ui.use_compel.setChecked(self.generator_settings.use_compel)
        except RuntimeError as e:
            if AIRUNNER_ART_ENABLED:
                self.logger.error(f"Error updating compel: {e}")

        # Toggle Compel visibility based on model version
        self._toggle_compel_visibility()
        
        # Update version-dependent UI (pipeline visibility, constraints, schedulers)
        self._update_version_dependent_ui()

        if self.generator_settings.model is None:
            self._update_model_id()

    @Slot(bool)
    def on_use_compel_toggled(self, val: bool):
        self.update_generator_settings(use_compel=val)

        if val:
            self.ui.clip_skip_slider_widget.hide()
        else:
            self.ui.clip_skip_slider_widget.show()

    def _toggle_compel_visibility(self):
        """Show/hide Compel checkbox based on whether the model supports it.

        FLUX and Z-Image models don't support Compel prompt weighting.
        """
        version = self.generator_settings.version
        if version in FLOW_MATCH_VERSIONS:
            self.ui.use_compel.hide()
        else:
            self.ui.use_compel.show()

    def _update_version_dependent_ui(self):
        """Update UI elements based on the current version.
        
        This handles:
        - Showing/hiding pipeline dropdown (FLUX/Z-Image don't have inpaint/outpaint)
        - Updating guidance scale and steps constraints
        - Updating scheduler dropdown
        """
        version = self.generator_settings.version
        
        # Hide pipeline dropdown for FLUX/Z-Image (they only support txt2img currently)
        if version in FLOW_MATCH_VERSIONS:
            self.ui.groupBox_3.hide()  # Pipeline groupbox
        else:
            self.ui.groupBox_3.show()
        
        # Update parameter constraints based on version
        constraints = VERSION_CONSTRAINTS.get(version, {})
        
        # Update guidance scale max (default 100.0 for other versions)
        guidance_max = constraints.get("guidance_scale_max", 100.0)
        self.ui.scale_widget.setProperty("spinbox_maximum", guidance_max)
        self.ui.scale_widget.setProperty("slider_maximum", int(guidance_max * 100))
        
        # Update steps max (default 200 for other versions)
        steps_max = constraints.get("steps_max", 200)
        self.ui.steps_widget.setProperty("spinbox_maximum", float(steps_max))
        self.ui.steps_widget.setProperty("slider_maximum", steps_max)
        
        # Reload schedulers to filter based on version
        self._load_schedulers_combobox()

    @Slot()
    def on_browse_button_clicked(self):
        # Use QFileDialog to get the file path
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select custom model"),
            self.generator_settings.custom_path
            or "",  # Start in current custom path or home
            self.tr("Model Files (*.safetensors)"),
        )
        if not file_path:
            return

        qsettings = get_qsettings()
        dont_ask_key = "import_model_dont_ask_again"
        dont_ask = qsettings.value(dont_ask_key, False, type=bool)

        if not dont_ask:
            dialog = QDialog(self)
            dialog.setWindowTitle(self.tr("Import Model"))
            layout = QVBoxLayout(dialog)
            label = QLabel(
                self.tr(
                    "Do you want to import this model to the AI Runner folder?"
                )
            )
            layout.addWidget(label)
            checkbox = QCheckBox(self.tr("Do not ask again"))
            layout.addWidget(checkbox)
            buttons = QDialogButtonBox(
                QDialogButtonBox.Yes | QDialogButtonBox.No
            )
            layout.addWidget(buttons)
            result = []

            def on_accept():
                result.append(True)
                dialog.accept()

            def on_reject():
                result.append(False)
                dialog.reject()

            buttons.accepted.connect(on_accept)
            buttons.rejected.connect(on_reject)
            dialog.exec()
            if checkbox.isChecked():
                qsettings.setValue(dont_ask_key, True)
            if not result or not result[0]:
                # User chose No
                self.ui.custom_model.blockSignals(True)
                self.ui.custom_model.setText(file_path)
                self.ui.custom_model.blockSignals(False)
                self.update_generator_settings(custom_path=file_path)
                return
        # If we get here, import to AI Runner folder
        filename = os.path.basename(file_path)
        dest_path = get_stable_diffusion_model_storage_path(
            self.generator_settings.version,
            self.generator_settings.pipeline_action,
            filename,
        )
        progress = QProgressDialog(
            self.tr("Importing model..."), None, 0, 100, self
        )
        progress.setWindowTitle(self.tr("Importing Model"))
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        # Check if the source file is in a whitelisted directory (main thread only!)
        whitelisted_roots = [
            os.path.expanduser("~"),
            "/tmp",
            "/etc",
            "/dev",
            "/proc",
        ]
        abs_file_path = os.path.abspath(file_path)
        if not any(
            abs_file_path.startswith(root) for root in whitelisted_roots
        ):
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.critical(
                self,
                self.tr("Permission Denied"),
                self.tr(
                    "The selected file is outside allowed directories. Please move it to your home directory or /tmp and try again."
                ),
            )
            return

        def copy_with_progress(src, dst):
            total = os.path.getsize(src)
            copied = 0
            bufsize = 1024 * 1024
            with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
                while True:
                    buf = fsrc.read(bufsize)
                    if not buf:
                        break
                    fdst.write(buf)
                    copied += len(buf)
                    percent = int((copied / total) * 100)
                    progress.setValue(percent)
            progress.setValue(100)

        def do_copy():
            try:
                copy_with_progress(file_path, dest_path)
            finally:
                progress.close()
                self.ui.custom_model.blockSignals(True)
                self.ui.custom_model.setText(dest_path)
                self.ui.custom_model.blockSignals(False)
                self.update_generator_settings(custom_path=dest_path)

        thread = threading.Thread(target=do_copy)
        thread.start()

    @Slot(str)
    def on_custom_model_currentTextChanged(self, val: str):
        self.update_generator_settings(custom_path=val)
        # Reload precision combobox since model changed
        self._load_precision_combobox()

    @Slot(str)
    def on_model_currentTextChanged(self, val: str):
        self._update_model_id()
        # Reload precision combobox to show VRAM estimates for new model
        self._load_precision_combobox()
        self.api.art.model_changed(model=val)

    def _update_model_id(self):
        index = self.ui.model.currentIndex()
        model_id = self.ui.model.itemData(index)
        self.update_generator_settings(model=model_id)

        # Automatically switch pipeline action to match the selected model
        if model_id:
            model = AIModels.objects.filter_first(AIModels.id == model_id)
            if model and model.pipeline_action:
                current_pipeline = self.generator_settings.pipeline_action
                if current_pipeline != model.pipeline_action:
                    # Update the pipeline action to match the model
                    self.update_generator_settings(
                        pipeline_action=model.pipeline_action
                    )
                    # Update the UI pipeline dropdown to match the model's pipeline
                    pipeline_display_text = None
                    if model.pipeline_action == GeneratorSection.TXT2IMG.value:
                        pipeline_display_text = f"{GeneratorSection.TXT2IMG.value} / {GeneratorSection.IMG2IMG.value}"
                    elif (
                        model.pipeline_action == GeneratorSection.INPAINT.value
                    ):
                        pipeline_display_text = f"{GeneratorSection.INPAINT.value} / {GeneratorSection.OUTPAINT.value}"

                    if pipeline_display_text:
                        pipeline_index = self.ui.pipeline.findText(
                            pipeline_display_text
                        )
                        if pipeline_index >= 0:
                            self.ui.pipeline.blockSignals(True)
                            self.ui.pipeline.setCurrentIndex(pipeline_index)
                            self.ui.pipeline.blockSignals(False)
                    # Reload models for the new pipeline action
                    self._load_models_combobox()

    @Slot(str)
    def on_pipeline_currentTextChanged(self, val: str):
        if (
            val
            == f"{GeneratorSection.TXT2IMG.value} / {GeneratorSection.IMG2IMG.value}"
        ):
            val = GeneratorSection.TXT2IMG.value
        elif (
            val
            == f"{GeneratorSection.INPAINT.value} / {GeneratorSection.OUTPAINT.value}"
        ):
            val = GeneratorSection.INPAINT.value

        generator_settings = self.generator_settings
        updated_kwargs = {"pipeline_action": val}
        selected_model_id = generator_settings.model
        if val == GeneratorSection.TXT2IMG.value:
            model = AIModels.objects.filter_first(
                AIModels.id == selected_model_id
            )
            if (
                model
                and model.pipeline_action == GeneratorSection.INPAINT.value
            ):
                # Need a compatible txt2img model for current version
                new_model = AIModels.objects.filter_first(
                    AIModels.version == generator_settings.version,
                    AIModels.pipeline_action == val,
                    AIModels.enabled.is_(True),
                    AIModels.is_default.is_(False),
                )
                selected_model_id = new_model.id if new_model else None
                updated_kwargs["model"] = selected_model_id
        self.logger.debug(
            "Pipeline change -> version=%s pipeline=%s model(before)=%s model(after)=%s",
            generator_settings.version,
            val,
            generator_settings.model,
            selected_model_id,
        )
        self.update_generator_settings(**updated_kwargs)
        self._load_models_combobox()
        # Notify with explicit model id if known.
        self.api.art.model_changed(model=selected_model_id, pipeline=val)

    @Slot(str)
    def on_version_currentTextChanged(self, val):
        # Record previous for logging
        prev_version = self.generator_settings.version
        prev_pipeline = self.generator_settings.pipeline_action
        prev_model = self.generator_settings.model
        # Determine the generator_name for this version
        generator_name = VERSION_TO_GENERATOR.get(val, ImageGenerator.FLUX.value)
        # First update version and generator_name in settings
        self.update_generator_settings(version=val, generator_name=generator_name)
        self.api.widget_element_changed("sd_version", "version", val)
        self._load_pipelines_combobox()
        generator_settings = self.generator_settings
        pipeline = generator_settings.pipeline_action
        # Try to find a model matching current pipeline
        model = AIModels.objects.filter_first(
            AIModels.version == val,
            AIModels.pipeline_action == pipeline,
            AIModels.enabled.is_(True),
            AIModels.is_default.is_(False),
        )
        chosen_model_id = None
        chosen_pipeline = pipeline
        if model is not None:
            chosen_model_id = model.id
        else:
            # fallback to txt2img
            fallback_model = AIModels.objects.filter_first(
                AIModels.version == val,
                AIModels.pipeline_action == GeneratorSection.TXT2IMG.value,
                AIModels.enabled.is_(True),
                AIModels.is_default.is_(False),
            )
            if fallback_model is not None:
                chosen_model_id = fallback_model.id
                chosen_pipeline = GeneratorSection.TXT2IMG.value
        # Apply combined update once
        self.update_generator_settings(
            model=chosen_model_id, pipeline_action=chosen_pipeline
        )
        self.logger.debug(
            "Version change prev(version=%s pipeline=%s model=%s) -> new(version=%s pipeline=%s model=%s)",
            prev_version,
            prev_pipeline,
            prev_model,
            val,
            chosen_pipeline,
            chosen_model_id,
        )
        self._toggle_compel_visibility()
        self._update_version_dependent_ui()
        self._load_models_combobox()
        self.api.art.model_changed(
            model=chosen_model_id, version=val, pipeline=chosen_pipeline
        )

    def _load_pipelines_combobox(self):
        self.ui.pipeline.blockSignals(True)
        self.ui.pipeline.clear()
        pipeline_names = [
            f"{GeneratorSection.TXT2IMG.value} / {GeneratorSection.IMG2IMG.value}",
            f"{GeneratorSection.INPAINT.value} / {GeneratorSection.OUTPAINT.value}",
        ]

        current_pipeline = self.generator_settings.pipeline_action
        if current_pipeline != "":
            if current_pipeline == GeneratorSection.TXT2IMG.value:
                current_pipeline = f"{GeneratorSection.TXT2IMG.value} / {GeneratorSection.IMG2IMG.value}"
            elif current_pipeline == GeneratorSection.INPAINT.value:
                current_pipeline = f"{GeneratorSection.INPAINT.value} / {GeneratorSection.OUTPAINT.value}"

        self.ui.pipeline.addItems(pipeline_names)
        self.ui.pipeline.setCurrentText(current_pipeline)
        self.ui.pipeline.blockSignals(False)

    @property
    def versions(self) -> List[str]:
        if len(self._versions) == 0:
            versions_set = set()
            for image_generator in ImageGenerator:
                pipelines = self.get_pipelines(category=image_generator.value)
                versions_set.update(
                    [pipeline["version"] for pipeline in pipelines]
                )
            self._versions = list(versions_set)
        return self._versions

    @property
    def version(self) -> str:
        return self._version

    @version.setter
    def version(self, value: str):
        self._version = value

    def _load_versions_combobox(self):
        self.ui.version.blockSignals(True)
        self.ui.version.clear()
        self.ui.version.addItems(self.versions)
        current_version = self.generator_settings.version
        if current_version != "":
            self.ui.version.setCurrentText(current_version)
        self.ui.version.blockSignals(False)

    def on_models_changed_signal(self):
        try:
            self._load_pipelines_combobox()
            self._load_versions_combobox()
            self._load_models_combobox()
            self._load_schedulers_combobox()
        except RuntimeError as e:
            if AIRUNNER_ART_ENABLED:
                self.logger.error(f"Error loading models: {e}")

    def clear_models(self):
        self.ui.model.clear()

    @property
    def action(self) -> str:
        return self._current_action

    @action.setter
    def action(self, value: str):
        self._current_action = value

    @property
    def models(self) -> List[AIModels]:
        if (
            self.generator_settings.pipeline_action != self.action
            or len(self._models) == 0
            or self.generator_settings.version != self.version
        ):
            self.action = self.generator_settings.pipeline_action
            self.version = self.generator_settings.version

            # Determine the correct category based on version
            from airunner.components.application.workers.model_scanner_worker import (
                get_category_for_version,
            )
            image_generator = get_category_for_version(self.version)

            pipeline_actions = [GeneratorSection.TXT2IMG.value]

            if self.action == GeneratorSection.INPAINT.value:
                pipeline_actions.append(GeneratorSection.INPAINT.value)

            self.models = AIModels.objects.filter(
                AIModels.category == image_generator,
                AIModels.pipeline_action.in_(pipeline_actions),
                AIModels.version == self.version,
                AIModels.enabled.is_(True),
                AIModels.is_default.is_(False),
            )
        return self._models

    @models.setter
    def models(self, value: List[AIModels]):
        self._models = value

    def _load_models_combobox(self):
        self.logger.info("Loading models")
        self.ui.model.blockSignals(True)
        self.clear_models()

        generator_settings = self.generator_settings
        models = self.models

        model_id = generator_settings.model
        if model_id is None and len(models) > 0:
            current_model = models[0]
            self.update_generator_settings(model=current_model.id)

        for model in models:
            self.ui.model.addItem(model.name, model.id)

        if model_id:
            index = self.ui.model.findData(model_id)
            if index != -1:
                self.ui.model.setCurrentIndex(index)
        self.ui.model.blockSignals(False)

    @property
    def schedulers(self):
        """Get schedulers filtered by version.
        
        FLUX and Z-Image models support multiple flow-match schedulers:
        - Flow Match Euler (default)
        - Flow Match Euler Karras (Karras sigma schedule)
        - Flow Match Euler Stochastic (SDE-like behavior)
        - Flow Match Heun (2nd order, higher quality)
        - Flow Match LCM (Latent Consistency)
        
        Other versions support all non-flow-match schedulers.
        """
        all_schedulers = Schedulers.objects.all()
        version = self.generator_settings.version
        
        if version in FLOW_MATCH_VERSIONS:
            # Return all flow-match scheduler variants for FLUX/Z-Image
            return [
                s for s in all_schedulers 
                if s.display_name in FLOW_MATCH_SCHEDULERS
            ]
        
        # For other versions, return all schedulers except flow-match ones
        return [
            s for s in all_schedulers 
            if s.display_name not in FLOW_MATCH_SCHEDULERS
        ]

    def _load_schedulers_combobox(self):
        self.ui.scheduler.blockSignals(True)
        schedulers = self.schedulers
        scheduler_names = [s.display_name for s in schedulers]
        self.ui.scheduler.clear()
        self.ui.scheduler.addItems(scheduler_names)

        current_scheduler = self.generator_settings.scheduler
        if current_scheduler != "":
            self.ui.scheduler.setCurrentText(current_scheduler)
        else:
            self.generator_settings.scheduler = self.ui.scheduler.currentText()
        self.update_generator_settings(
            scheduler=self.generator_settings.scheduler
        )
        self.ui.scheduler.blockSignals(False)

    @Slot(str)
    def on_scheduler_currentTextChanged(self, name):
        self.update_generator_settings(scheduler=name)
        self.api.art.change_scheduler(name)

    def _get_current_model_path(self) -> Optional[str]:
        """Get the path of the currently selected model.
        
        Returns:
            Model path string or None if no model selected.
        """
        model_id = self.generator_settings.model
        if model_id is None:
            return None
        
        model = AIModels.objects.filter_first(AIModels.id == model_id)
        if model is None:
            return None
        
        return model.path

    def _load_precision_combobox(self):
        """Load precision options into the precision dropdown.
        
        Precision options are filtered based on the model's native dtype.
        Models can only be loaded at their native precision or LOWER
        (can't add information that isn't in the model).
        
        VRAM estimates are shown for each precision option based on
        the model's file size and the selected precision.
        
        Available options (when applicable):
        - 4-bit: Lowest memory, uses BitsAndBytes NF4 quantization
        - 8-bit: Low memory, uses BitsAndBytes 8-bit quantization  
              NOTE: Not available for Z-Image/FLUX on <=16GB cards (requires >20GB)
        - FP8: 8-bit float, good quality with low memory (requires Hopper/Ada GPU)
              NOTE: Not available for Z-Image/FLUX (text encoder incompatible)
        - BF16 (bfloat16): Best quality/speed balance, recommended for most models
        - FP16 (float16): Lower memory usage, good compatibility
        - FP32 (float32): Highest precision but uses most memory
        """
        self.ui.precision.blockSignals(True)
        self.ui.precision.clear()
        
        # Get model path and detect native dtype
        model_path = self._get_current_model_path()
        native_dtype = "bfloat16"  # Default assumption
        
        if model_path:
            native_dtype = detect_model_dtype(model_path)
            self.logger.debug(f"Detected native dtype: {native_dtype} for model: {model_path}")
        
        # Get available precisions based on native dtype
        available_precisions = get_available_precisions(native_dtype)
        
        # Get available VRAM
        available_vram_gb = 0.0
        if torch.cuda.is_available():
            try:
                available_vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            except Exception:
                pass
        
        # Filter precision options for Z-Image/FLUX based on VRAM
        version = self.generator_settings.version
        is_large_model = version in FLOW_MATCH_VERSIONS
        
        if is_large_model:
            # FP8 is not supported for Z-Image/FLUX (text encoder doesn't support it)
            if "float8" in available_precisions:
                available_precisions.remove("float8")
            
            # 8-bit requires >20GB VRAM for Z-Image/FLUX models
            # On 16GB cards, 8-bit still uses ~14GB leaving no room for VAE decode
            if available_vram_gb <= 20 and "8bit" in available_precisions:
                available_precisions.remove("8bit")
                self.logger.debug(f"Removed 8-bit option: {available_vram_gb:.1f}GB VRAM insufficient for Z-Image/FLUX")
        
        # Precision options ordered from lowest memory to highest
        # Only include options that are valid for this model
        precision_order = ["4bit", "8bit", "float8", "bfloat16", "float16", "float32"]
        
        for precision in precision_order:
            if precision not in available_precisions:
                continue
            
            display_name = PRECISION_DISPLAY_NAMES.get(precision, precision)
            
            # Add VRAM estimate if model path is available
            if model_path:
                estimate = estimate_vram_from_path(
                    model_path, precision, native_dtype
                )
                if estimate:
                    # Check if this precision is safe for current VRAM
                    if available_vram_gb > 0 and not is_precision_safe_for_vram(estimate, available_vram_gb):
                        # Add warning indicator for risky precision settings
                        display_name = f"⚠️ {display_name} ({estimate})"
                    else:
                        display_name = f"{display_name} ({estimate})"
            
            self.ui.precision.addItem(display_name, precision)
        
        # Restore current selection from settings
        current_dtype = getattr(self.generator_settings, "dtype", "bfloat16") or "bfloat16"
        
        # If current dtype is not available, pick the best available option
        if current_dtype not in available_precisions:
            # For Z-Image/FLUX on low VRAM, default to 4-bit
            if is_large_model and available_vram_gb <= 20 and "4bit" in available_precisions:
                new_dtype = "4bit"
            elif native_dtype in available_precisions:
                new_dtype = native_dtype
            elif available_precisions:
                new_dtype = available_precisions[0]  # First available
            else:
                new_dtype = "bfloat16"  # Fallback
            
            self.logger.warning(
                f"Current dtype {current_dtype} not available for model "
                f"(native: {native_dtype}, VRAM: {available_vram_gb:.1f}GB). "
                f"Defaulting to {new_dtype}."
            )
            current_dtype = new_dtype
            self.update_generator_settings(dtype=current_dtype)
        
        # Find and select the saved dtype
        for i in range(self.ui.precision.count()):
            if self.ui.precision.itemData(i) == current_dtype:
                self.ui.precision.setCurrentIndex(i)
                break
        
        self.ui.precision.blockSignals(False)

    @Slot(str)
    def on_precision_currentTextChanged(self, val: str):
        """Handle precision selection change.
        
        Updates the generator settings with the selected dtype/precision.
        This affects how the model is loaded.
        """
        # Get the actual dtype value from item data
        index = self.ui.precision.currentIndex()
        dtype = self.ui.precision.itemData(index)
        if not dtype:
            return
        
        self.logger.info(f"Precision changed to: {dtype}")
        self.update_generator_settings(dtype=dtype)
        
        # Notify that model settings changed (may need to reload)
        self.api.art.model_changed(
            model=self.generator_settings.model,
            version=self.generator_settings.version,
            pipeline=self.generator_settings.pipeline_action,
        )
