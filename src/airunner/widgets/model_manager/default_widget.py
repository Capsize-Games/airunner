from PyQt6 import QtCore

from airunner.data.session_scope import session_scope
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.model_manager.model_widget import ModelWidget
from airunner.widgets.model_manager.templates.default_ui import Ui_default_model_widget
from PyQt6 import QtWidgets



class DefaultModelWidget(BaseWidget):
    widget_class_ = Ui_default_model_widget
    model_widgets = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.show_items_in_scrollarea()
        # find how many models are set to enabled = FAlse
        self.ui.toggle_all.blockSignals(True)
        disabled_models = self.app.ai_model_get_disabled_default()
        if len(disabled_models) == 0:
            self.ui.toggle_all.setCheckState(QtCore.Qt.CheckState.Checked)
        elif len(disabled_models) < len(self.app.find_models(default=True)):
            self.ui.toggle_all.setCheckState(QtCore.Qt.CheckState.PartiallyChecked)
        else:
            self.ui.toggle_all.setCheckState(QtCore.Qt.CheckState.Unchecked)
        self.ui.toggle_all.blockSignals(False)

    spacer = None

    def show_items_in_scrollarea(self, search=None):
        if self.spacer:
            self.ui.scrollAreaWidgetContents.layout().removeItem(self.spacer)
        for child in self.ui.scrollAreaWidgetContents.children():
            if isinstance(child, ModelWidget):
                child.deleteLater()
        with session_scope() as session:
            if search:
                # search by name
                models = self.app.find_models(search, default=True)
            else:
                models = self.app.find_models(default=True)
            for model_widget in self.model_widgets:
                model_widget.deleteLater()
            self.model_widgets = []
            for index, model in enumerate(models):
                version = model["version"]
                category = model["category"]
                pipeline_action = model["pipeline_action"]
                pipeline_class = self.app.get_pipeline_classname(pipeline_action, version, category)
                model_widget = ModelWidget(
                    path=model["path"],
                    branch=model["branch"],
                    version=version,
                    category=category,
                    pipeline_action=pipeline_action,
                    pipeline_class=pipeline_class,
                )
                model_widget.ui.delete_button.hide()
                model_widget.ui.edit_button.deleteLater()
                model_widget.ui.name.setChecked(model["enabled"])
                self.ui.scrollAreaWidgetContents.layout().addWidget(model_widget)
                self.model_widgets.append(model_widget)
        if not self.spacer:
            self.spacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.ui.scrollAreaWidgetContents.layout().addItem(self.spacer)

    def mode_type_changed(self, val):
        print("mode_type_changed", val)
    
    def toggle_all_state_change(self, val: int):
        if val == 0:
            # disable all by setting AIModel.enabled to False where is_default=True
            for item in self.app.ai_model_get_all():
                item["enabled"] = False
                self.app.ai_model_update(item)
            self.show_items_in_scrollarea()
        elif val == 1:
            # self.ui.toggle_all is a checkbox with tri-state enabled, how can we set it to checked?
            self.ui.toggle_all.setCheckState(QtCore.Qt.CheckState.Checked)
        elif val == 2:
            for item in self.app.ai_model_get_all():
                item["enabled"] = True
                self.app.ai_model_update(item)
            self.show_items_in_scrollarea()
            
    
    def search_text_changed(self, val):
        val = val.strip()
        if val == "":
            val = None
        self.show_items_in_scrollarea(val)