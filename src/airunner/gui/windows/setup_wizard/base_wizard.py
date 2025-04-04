from PySide6.QtWidgets import QWizardPage, QVBoxLayout, QWizard
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.gui.windows.main.settings_mixin import SettingsMixin


class BaseWizard(
    MediatorMixin,
    SettingsMixin,
    QWizardPage,
):
    class_name_ = None
    widget_class_ = None

    def __init__(self, parent: QWizard):
        super().__init__()
        
        if self.class_name_:
            self.ui = self.class_name_()
            self.ui.setupUi(self)

        if self.widget_class_:
            widget = self.widget_class_()
            layout = QVBoxLayout()
            layout.addWidget(widget)
            self.setLayout(layout)

        self.parent = parent

    def initialize_form(self):
        """
        Override this function to initialize form based on specific page in question.
        :return:
        """
        pass
