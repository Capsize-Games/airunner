from airunner.pyqt.widgets.base_widget import BaseWidget
from airunner.pyqt.widgets.model_manager.templates.default_ui import Ui_default_model_widget


class DefaultModelWidget(BaseWidget):
    widget_class_ = Ui_default_model_widget
    model_widgets = []