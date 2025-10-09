from typing import List
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

from airunner.components.art.data.ai_models import AIModels
from airunner.components.art.data.generator_settings import GeneratorSettings
from airunner.enums import (
    SignalCode,
    GeneratorSection,
    ImageGenerator,
    StableDiffusionVersion,
)
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.art.gui.widgets.stablediffusion.templates.stable_diffusion_settings_ui import (
    Ui_stable_diffusion_settings_widget,
)
from airunner.components.application.gui.windows.main.pipeline_mixin import (
    PipelineMixin,
)
from airunner.utils.application.create_worker import create_worker
from airunner.components.application.workers.model_scanner_worker import (
    ModelScannerWorker,
)
from airunner.settings import AIRUNNER_ART_ENABLED
from airunner.utils.settings.get_qsettings import get_qsettings
from airunner.utils.model_utils.model_utils import (
    get_stable_diffusion_model_storage_path,
)
import threading
import os


class StableDiffusionSettingsWidget(BaseWidget, PipelineMixin):
    widget_class_ = Ui_stable_diffusion_settings_widget

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.AI_MODELS_CREATE_SIGNAL: self.on_models_changed_signal,
            SignalCode.APPLICATION_MAIN_WINDOW_LOADED_SIGNAL: self.update_form,
        }
        super().__init__(*args, **kwargs)
        self._versions: List[str] = []
        self._models: List[AIModels] = []
        self._current_action: str = ""
        self.ui.custom_model.blockSignals(True)
        self.ui.custom_model.setText(self.generator_settings.custom_path)
        self.ui.custom_model.blockSignals(False)
        PipelineMixin.__init__(self)
        self.model_scanner_worker = create_worker(ModelScannerWorker)

        self._load_versions_combobox()
        self._load_pipelines_combobox()
        self._load_models_combobox()
        self._load_schedulers_combobox()

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
                "generator_name", ImageGenerator.STABLEDIFFUSION.value
            )
            self.ui.ddim_eta_slider_widget.hide()
            self.ui.frames_slider_widget.hide()
        except RuntimeError as e:
            if AIRUNNER_ART_ENABLED:
                self.logger.error(f"Error updating form: {e}")

        self.model_scanner_worker.add_to_queue("scan_for_models")

        try:
            self.ui.use_compel.setChecked(self.generator_settings.use_compel)
        except RuntimeError as e:
            if AIRUNNER_ART_ENABLED:
                self.logger.error(f"Error updating compel: {e}")

        if self.generator_settings.model is None:
            self._update_model_id()

    @Slot(bool)
    def on_use_compel_toggled(self, val: bool):
        self.update_generator_settings(use_compel=val)

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

    @Slot(str)
    def on_model_currentTextChanged(self, val: str):
        self._update_model_id()
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

    def on_scheduler_currentTextChanged(self, name):
        self.update_generator_settings(scheduler=name)
        self.api.art.change_scheduler(name)

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
        elif val == GeneratorSection.UPSCALER.value:
            val = GeneratorSection.UPSCALER.value

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
        elif val == GeneratorSection.UPSCALER.value:
            from airunner.enums import StableDiffusionVersion

            updated_kwargs["version"] = (
                StableDiffusionVersion.X4_UPSCALER.value
            )
            # When switching to upscaler we clear model so it reselects properly
            updated_kwargs["model"] = None
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
        # First update version in settings (does not touch model/pipeline yet)
        self.update_generator_settings(version=val)
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
        self._load_models_combobox()
        self.api.art.model_changed(
            model=chosen_model_id, version=val, pipeline=chosen_pipeline
        )

    def _load_pipelines_combobox(self):
        self.ui.pipeline.blockSignals(True)
        self.ui.pipeline.clear()

        if (
            self.generator_settings.version
            == StableDiffusionVersion.X4_UPSCALER.value
        ):
            pipeline_names = [GeneratorSection.UPSCALER.value]
            self.update_generator_settings(
                pipeline_action=GeneratorSection.UPSCALER.value
            )
        else:
            pipeline_names = [
                f"{GeneratorSection.TXT2IMG.value} / {GeneratorSection.IMG2IMG.value}",
                f"{GeneratorSection.INPAINT.value} / {GeneratorSection.OUTPAINT.value}",
            ]
            # Do not force-overwrite pipeline action unless coming from upscaler
            if (
                self.generator_settings.pipeline_action
                == GeneratorSection.UPSCALER.value
            ):
                self.update_generator_settings(
                    pipeline_action=GeneratorSection.TXT2IMG.value
                )

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
            pipelines = self.get_pipelines(
                category=ImageGenerator.STABLEDIFFUSION.value
            )
            self._versions = set(
                [pipeline["version"] for pipeline in pipelines]
            )
        return list(self._versions)

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
        ):
            self.action = self.generator_settings.pipeline_action

            image_generator = ImageGenerator.STABLEDIFFUSION.value
            pipeline = self.generator_settings.pipeline_action
            version = self.generator_settings.version

            if (
                self.generator_settings.pipeline_action
                == GeneratorSection.UPSCALER.value
            ):
                pipeline_actions = [GeneratorSection.UPSCALER.value]
            else:
                pipeline_actions = [GeneratorSection.TXT2IMG.value]

                if pipeline == GeneratorSection.INPAINT.value:
                    pipeline_actions.append(GeneratorSection.INPAINT.value)

            self.models = AIModels.objects.filter(
                AIModels.category == image_generator,
                AIModels.pipeline_action.in_(pipeline_actions),
                AIModels.version == version,
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

    def _load_schedulers_combobox(self):
        self.ui.scheduler.blockSignals(True)
        scheduler_names = [s.display_name for s in self.schedulers]
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
