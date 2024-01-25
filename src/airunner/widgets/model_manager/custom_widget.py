from airunner.enums import ServiceCode
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.model_manager.model_widget import ModelWidget
from airunner.widgets.model_manager.templates.custom_ui import Ui_custom_model_widget

from PyQt6 import QtWidgets

from airunner.workers.model_scanner_worker import ModelScannerWorker


class CustomModelWidget(BaseWidget):
    initialized = False
    widget_class_ = Ui_custom_model_widget
    model_widgets = []
    spacer = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.show_items_in_scrollarea()
        self.initialized = True
        self.model_scanner_worker = self.create_worker(ModelScannerWorker)
        self.model_scanner_worker.add_to_queue("scan_for_models")
    
    def action_button_clicked_scan_for_models(self):
        self.model_scanner_worker.add_to_queue("scan_for_models")
   
    def show_items_in_scrollarea(self, search=None):
        if self.spacer:
            self.ui.scrollAreaWidgetContents.layout().removeItem(self.spacer)
        for child in self.ui.scrollAreaWidgetContents.children():
            if isinstance(child, ModelWidget):
                child.deleteLater()
        if search:
            models = self.get_service("ai_models_find")(search, default=False)
        else:
            models = self.get_service("ai_models_find")(default=False)
        for model_widget in self.model_widgets:
            model_widget.deleteLater()
        self.model_widgets = []
        for index, model in enumerate(models):
            version = model['version']
            category = model['category']
            pipeline_action = model["pipeline_action"]
            pipeline_class = self.get_service(ServiceCode.GET_PIPELINE_CLASSNAME)(
                pipeline_action, version, category)

            model_widget = ModelWidget(
                path=model["path"],
                branch=model["branch"],
                version=version,
                category=category,
                pipeline_action=pipeline_action,
                pipeline_class=pipeline_class,
            )

            model_widget.ui.name.setChecked(model["enabled"])

            self.ui.scrollAreaWidgetContents.layout().addWidget(
                model_widget)

            self.model_widgets.append(model_widget)
        
        if not self.spacer:
            self.spacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.ui.scrollAreaWidgetContents.layout().addItem(self.spacer)

    def mode_type_changed(self, val):
        print("mode_type_changed", val)
    
    def toggle_all_toggled(self, val):
        print("toggle_all_toggled", val)
    
    def search_text_edited(self, val):
        val = val.strip()
        if val == "":
            val = None
        self.show_items_in_scrollarea(val)