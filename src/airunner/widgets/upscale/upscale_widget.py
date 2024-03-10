from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.upscale.templates.upscale_widget_ui import Ui_upscale_widget


class UpscaleWidget(BaseWidget):
    widget_class_ = Ui_upscale_widget

    def model_changed(self, val):
        pass

    def face_enhance_toggled(self, val):
        pass

    def upscale_amount_changed(self, val):
        pass

    def upscale_clicked(self):
        pass
