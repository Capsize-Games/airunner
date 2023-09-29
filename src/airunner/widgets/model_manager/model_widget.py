from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.model_manager.templates.model_ui import Ui_model_widget


class ModelWidget(BaseWidget):
    widget_class_ = Ui_model_widget

    def set_properties(self, **kwargs):
        for key, value in kwargs.items():
            self.setProperty(key, value)
            setattr(
                self.ui,
                key,
                value
            )
