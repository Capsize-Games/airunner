from PyQt6 import QtCore

from airunner.data.models import AIModel
from airunner.utils import get_session, save_session
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.model_manager.model_widget import ModelWidget
from airunner.widgets.model_manager.templates.default_ui import Ui_default_model_widget


session = get_session()


class DefaultModelWidget(BaseWidget):
    widget_class_ = Ui_default_model_widget
    model_widgets = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.show_items_in_scrollarea()
        # find how many models are set to enabled = FAlse
        self.ui.toggle_all.blockSignals(True)
        disabled_models = session.query(AIModel).filter_by(is_default=True).filter_by(enabled=False).all()
        if len(disabled_models) == 0:
            self.ui.toggle_all.setCheckState(QtCore.Qt.CheckState.Checked)
        elif len(disabled_models) < len(session.query(AIModel).filter_by(is_default=True).all()):
            self.ui.toggle_all.setCheckState(QtCore.Qt.CheckState.PartiallyChecked)
        else:
            self.ui.toggle_all.setCheckState(QtCore.Qt.CheckState.Unchecked)
        self.ui.toggle_all.blockSignals(False)

    def show_items_in_scrollarea(self, search=None):
        for child in self.ui.scrollAreaWidgetContents.children():
            if isinstance(child, ModelWidget):
                child.deleteLater()
        if search:
            # search by name
            models = session.query(AIModel).filter_by(is_default=True).filter(AIModel.name.like(f"%{search}%")).all()
        else:
            models = session.query(AIModel).filter_by(is_default=True).all()
        for model_widget in self.model_widgets:
            model_widget.deleteLater()
        self.model_widgets = []
        for index, model in enumerate(models):
            version = model.version
            category = model.category
            pipeline_action = model.pipeline_action
            pipeline_class = self.settings_manager.get_pipeline_classname(pipeline_action, version, category)
            model_widget = ModelWidget(
                path=model.path,
                branch=model.branch,
                version=version,
                category=category,
                pipeline_action=pipeline_action,
                pipeline_class=pipeline_class,
            )
            model_widget.ui.delete_button.hide()
            model_widget.ui.edit_button.deleteLater()
            model_widget.ui.name.setChecked(model.enabled)
            self.ui.scrollAreaWidgetContents.layout().addWidget(model_widget)
            self.model_widgets.append(model_widget)

    def mode_type_changed(self, val):
        print("mode_type_changed", val)
    
    def toggle_all_state_change(self, val: int):
        if val == 0:
            # disable all by setting AIModel.enabled to False where is_default=True
            session.query(AIModel).filter_by(is_default=True).update({"enabled": False})
            save_session()
            self.show_items_in_scrollarea()
        elif val == 1:
            # self.ui.toggle_all is a checkbox with tri-state enabled, how can we set it to checked?
            self.ui.toggle_all.setCheckState(QtCore.Qt.CheckState.Checked)
        elif val == 2:
            session.query(AIModel).filter_by(is_default=True).update({"enabled": True})
            save_session()
            self.show_items_in_scrollarea()
            
    
    def search_text_changed(self, val):
        val = val.strip()
        if val == "":
            val = None
        self.show_items_in_scrollarea(val)