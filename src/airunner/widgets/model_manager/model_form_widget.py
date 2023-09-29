from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.model_manager.templates.model_form_ui import Ui_model_form_widget


class ModelFormWidget(BaseWidget):
    widget_class_ = Ui_model_form_widget
    model_widgets = []