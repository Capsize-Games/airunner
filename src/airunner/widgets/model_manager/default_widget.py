from airunner.data.models import AIModel
from airunner.utils import get_session
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.model_manager.model_widget import ModelWidget
from airunner.widgets.model_manager.templates.default_ui import Ui_default_model_widget


class DefaultModelWidget(BaseWidget):
    widget_class_ = Ui_default_model_widget
    model_widgets = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.show_items_in_scrollarea()

    def show_items_in_scrollarea(self):
        session = get_session()
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
    
    def toggle_all_toggled(self, val):
        print("toggle_all_toggled", val)
    
    def search_text_changed(self, val):
        print("search text changed", val)