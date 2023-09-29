from airunner.pyqt.widgets.base_widget import BaseWidget
from airunner.pyqt.widgets.model_manager.templates.import_ui import Ui_import_model_widget


class ImportWidget(BaseWidget):
    widget_class_ = Ui_import_model_widget
    model_widgets = []