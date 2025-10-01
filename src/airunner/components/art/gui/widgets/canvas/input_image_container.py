from airunner.enums import SignalCode
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.art.gui.widgets.canvas.templates.input_image_container_ui import (
    Ui_input_image_container,
)
from airunner.components.art.gui.widgets.canvas.input_image import InputImage


class InputImageContainer(BaseWidget):
    widget_class_ = Ui_input_image_container

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.MASK_GENERATOR_WORKER_RESPONSE_SIGNAL: self.on_mask_generator_worker_response_signal,
            SignalCode.MASK_UPDATED: self.on_mask_generator_worker_response_signal,
            SignalCode.CANVAS_IMAGE_UPDATED_SIGNAL: self.on_canvas_image_updated_signal,
        }
        super().__init__(*args, **kwargs)
        self.input_image = None
        self.mask_image = None
        self.generated_image = None

    @property
    def settings_key(self):
        return self.property("settings_key")

    def on_mask_generator_worker_response_signal(self, _message):
        if self.mask_image:
            self.mask_image.on_mask_generator_worker_response_signal()

    def on_canvas_image_updated_signal(self, *_args):
        # When the main canvas image updates, refresh input image if linked
        try:
            if self.input_image and getattr(
                self.input_image.current_settings,
                "use_grid_image_as_input",
                False,
            ):
                self.input_image.load_image_from_grid()
            if self.generated_image and getattr(
                self.generated_image.current_settings,
                "use_grid_image_as_input",
                False,
            ):
                self.generated_image.load_image_from_grid()
            if self.mask_image and getattr(
                self.mask_image.current_settings,
                "use_grid_image_as_input",
                False,
            ):
                self.mask_image.load_image_from_grid()
        except Exception:
            # Non-fatal; UI will refresh on next explicit action
            pass

    def showEvent(self, event):
        settings_key = self.settings_key
        self._set_label()
        if self.input_image is None:
            self.input_image = InputImage(settings_key=self.settings_key)
            self.ui.tabWidget.addTab(self.input_image, "Input Image")

        if (
            self.generated_image is None
            and settings_key == "controlnet_settings"
        ):
            self.generated_image = InputImage(
                settings_key=self.settings_key, use_generated_image=True
            )
            self.ui.tabWidget.addTab(self.generated_image, "Generated Image")
        elif self.mask_image is None and settings_key == "outpaint_settings":
            self.mask_image = InputImage(
                settings_key=self.settings_key, is_mask=True
            )
            self.ui.tabWidget.addTab(self.mask_image, "Mask")

    def _set_label(self):
        settings_key = self.settings_key
        if settings_key == "outpaint_settings":
            label = "Inpaint / Outpaint"
        elif settings_key == "controlnet_settings":
            label = "Controlnet"
        else:
            label = "Image-to-Image"
        self.ui.label.setText(label)
