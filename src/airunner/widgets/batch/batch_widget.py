from abc import ABC

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.batch.templates.batch_widget_ui import Ui_batch_widget


class BatchWidget(BaseWidget, ABC):
    widget_class_ = Ui_batch_widget
