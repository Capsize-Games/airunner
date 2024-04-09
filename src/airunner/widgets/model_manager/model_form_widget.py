from PySide6 import QtWidgets

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.model_manager.templates.model_form_ui import Ui_model_form_widget

class ModelFormWidget(BaseWidget):
    widget_class_ = Ui_model_form_widget
    model_widgets = []

    def set_model_form_data(
        self, 
        categories, 
        actions, 
        diffuser_model_versions, 
        category, 
        pipeline_action, 
        pipeline_class, 
        diffuser_model_version, 
        path, 
        model_name,
        model_data,
        model_type
    ):
        self.ui.category.clear()
        self.ui.category.addItems(categories)
        self.ui.category.setCurrentText(category)
        self.ui.pipeline_action.clear()
        self.ui.pipeline_action.addItems(actions)
        self.ui.pipeline_action.setCurrentText(pipeline_action)
        self.ui.model_name.setText(model_name)
        self.ui.diffuser_model_version.clear()
        self.ui.diffuser_model_version.addItems(diffuser_model_versions)
        self.ui.diffuser_model_version.setCurrentText(diffuser_model_version)
        self.ui.model_type.clear()
        self.ui.model_type.addItems(["Checkpoint", "LORA", "Embedding", "VAE", "Controlnet", "Pose"])
        self.ui.enabled.setChecked(True)
        self.ui.path_line_edit.setText(path)

        # set current model type
        if model_type == "TextualInversion":
            model_type = "Embedding"
        self.ui.model_type.setCurrentText(model_type)

        allowCommercialUse = model_data["allowCommercialUse"]
        if type(allowCommercialUse) == list:
            allowCommercialUse = ", ".join(allowCommercialUse)

        # self.ui.model_data.show()
        #
        # if data is None:
        #     self.ui.model_data.hide()

        self.ui.poi.setText(str(model_data["poi"]))
        self.ui.require_credit.setText(str(model_data["allowNoCredit"]))
        self.ui.allow_commercial_use.setText(str(allowCommercialUse))
        self.ui.allow_derivatives.setText(str(model_data["allowDerivatives"]))
        self.ui.allow_different_license.setText(str(model_data["allowDifferentLicense"]))