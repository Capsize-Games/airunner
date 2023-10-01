from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.deterministic.templates.deterministic_widget_ui import Ui_deterministic_widget


class DeterministicWidget(BaseWidget):
    widget_class_ = Ui_deterministic_widget

    @property
    def batch_size(self):
        return self.ui.images_per_batch.value()

    @property
    def category(self):
        return self.ui.category.text()
