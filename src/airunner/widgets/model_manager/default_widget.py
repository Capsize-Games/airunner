import threading

from PySide6 import QtCore
from PySide6.QtCore import QTimer

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.model_manager.model_widget import ModelWidget
from airunner.widgets.model_manager.templates.default_ui import Ui_default_model_widget
from PySide6 import QtWidgets
from airunner.windows.main.ai_model_mixin import AIModelMixin
from airunner.windows.main.pipeline_mixin import PipelineMixin


class DefaultModelWidget(
    BaseWidget,
    PipelineMixin,
    AIModelMixin
):
    widget_class_ = Ui_default_model_widget
    model_widgets = []

    def __init__(self, *args, **kwargs):
        self.initialized = False
        PipelineMixin.__init__(self)
        AIModelMixin.__init__(self)
        super().__init__(*args, **kwargs)
        self.spacer = None
        self.initialized = False
        self.__thread = threading.Thread(target=self.__do_show)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(
            50,
            self.__do_show
        )

    def __do_show(self):
        if not self.initialized:
            self.show_items_in_scrollarea()
            # find how many models are set to enabled = False
            self.ui.toggle_all.blockSignals(True)
            disabled_models = self.ai_model_get_disabled_default()
            if len(disabled_models) == 0:
                self.ui.toggle_all.setCheckState(QtCore.Qt.CheckState.Checked)
            elif len(disabled_models) < len(self.ai_models_find(default=True)):
                self.ui.toggle_all.setCheckState(QtCore.Qt.CheckState.PartiallyChecked)
            else:
                self.ui.toggle_all.setCheckState(QtCore.Qt.CheckState.Unchecked)
            self.ui.toggle_all.blockSignals(False)
            self.initialized = True

    def show_items_in_scrollarea(self, search=None):
        if self.spacer:
            self.ui.scrollAreaWidgetContents.layout().removeItem(self.spacer)
        for child in self.ui.scrollAreaWidgetContents.children():
            if isinstance(child, ModelWidget):
                child.deleteLater()
        if search:
            # search by name
            models = self.ai_models_find(search, default=True)
        else:
            models = self.ai_models_find(default=True)
        for model_widget in self.model_widgets:
            model_widget.deleteLater()
        self.model_widgets = []
        for index, model in enumerate(models):
            version = model["version"]
            category = model["category"]
            pipeline_action = model["pipeline_action"]
            pipeline_class = self.get_pipeline_classname(
                pipeline_action,
                version,
                category
            )
            model_widget = ModelWidget(
                path=model["path"],
                branch=model["branch"],
                version=version,
                category=category,
                pipeline_action=pipeline_action,
                pipeline_class=pipeline_class,
            )
            model_widget.ui.delete_button.hide()
            model_widget.ui.name.setChecked(model["enabled"])
            self.ui.scrollAreaWidgetContents.layout().addWidget(model_widget)
            self.model_widgets.append(model_widget)
        if not self.spacer:
            width = 20
            height = 40
            self.spacer = QtWidgets.QSpacerItem(
                width,
                height,
                QtWidgets.QSizePolicy.Policy.Minimum,
                QtWidgets.QSizePolicy.Policy.Expanding
            )
        self.ui.scrollAreaWidgetContents.layout().addItem(self.spacer)

    def mode_type_changed(self, val):
        print("mode_type_changed", val)
    
    def toggle_all_state_change(self, val: int):
        if val == 0:
            # disable all by setting AIModel.enabled to False where is_default=True
            for item in self.ai_models:
                item.enabled = False
                self.update_ai_model(item)
            self.show_items_in_scrollarea()
        elif val == 1:
            # self.ui.toggle_all is a checkbox with tri-state enabled, how can we set it to checked?
            self.ui.toggle_all.setCheckState(QtCore.Qt.CheckState.Checked)
        elif val == 2:
            for item in self.ai_models:
                item.enabled = True
                self.update_ai_model(item)
            self.show_items_in_scrollarea()

    def search_text_changed(self, val):
        val = val.strip()
        if val == "":
            val = None
        self.show_items_in_scrollarea(val)
