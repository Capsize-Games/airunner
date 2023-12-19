from PyQt6 import QtWidgets

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
        model_data
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
        self.ui.pipeline_class_line_edit.setText(pipeline_class)
        self.ui.enabled.setChecked(True)
        self.ui.path_line_edit.setText(path)

        # clear the table
        self.ui.model_data_table.clearContents()
        self.ui.model_data_table.setRowCount(5)
        self.ui.model_data_table.setItem(0, 0, QtWidgets.QTableWidgetItem("POI"))
        self.ui.model_data_table.setItem(1, 0, QtWidgets.QTableWidgetItem("Allow No Credit"))
        self.ui.model_data_table.setItem(2, 0, QtWidgets.QTableWidgetItem("Allow Commercial Use"))
        self.ui.model_data_table.setItem(3, 0, QtWidgets.QTableWidgetItem("Allow Derivatives"))
        self.ui.model_data_table.setItem(4, 0, QtWidgets.QTableWidgetItem("Allow Different License"))

        self.ui.model_data_table.setItem(0, 1, QtWidgets.QTableWidgetItem(str(model_data["poi"])))
        self.ui.model_data_table.setItem(1, 1, QtWidgets.QTableWidgetItem(str(model_data["allowNoCredit"])))
        self.ui.model_data_table.setItem(2, 1, QtWidgets.QTableWidgetItem(str(model_data["allowCommercialUse"])))
        self.ui.model_data_table.setItem(3, 1, QtWidgets.QTableWidgetItem(str(model_data["allowDerivatives"])))
        self.ui.model_data_table.setItem(4, 1, QtWidgets.QTableWidgetItem(str(model_data["allowDifferentLicense"])))