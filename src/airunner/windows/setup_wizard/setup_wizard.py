from PySide6.QtCore import Slot
from PySide6.QtWidgets import QWizard, QWizardPage, QVBoxLayout, QLabel

from airunner.mediator_mixin import MediatorMixin
from airunner.widgets.export_preferences.export_preferences_widget import ExportPreferencesWidget
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.windows.setup_wizard.templates.airunner_license_ui import Ui_airunner_license
from airunner.windows.setup_wizard.templates.path_settings_ui import Ui_PathSettings
from airunner.windows.setup_wizard.templates.stable_diffusion_license_ui import Ui_stable_diffusion_license
from airunner.windows.setup_wizard.templates.user_agreement_ui import Ui_user_agreement


class BaseWizard(QWizardPage, MediatorMixin, SettingsMixin):
    class_name_ = None
    widget_class_ = None

    def __init__(self):
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        super(BaseWizard, self).__init__()
        if self.class_name_:
            self.ui = self.class_name_()
            self.ui.setupUi(self)
        if self.widget_class_:
            widget = self.widget_class_()
            layout = QVBoxLayout()
            layout.addWidget(widget)
            self.setLayout(layout)
        self.initialize_form()

    def initialize_form(self):
        """
        Override this function to initialize form based on specific page in question.
        :return:
        """
        pass

    def save_settings(self):
        """
        Override this function to save settings based on specific page in question.
        :return:
        """
        pass

    def nextId(self):
        self.save_settings()
        return super().nextId()



class SetupWizard(QWizard):
    def __init__(self):
        super(SetupWizard, self).__init__()

        self.addPage(WelcomePage())
        self.addPage(PathSettings())
        self.addPage(MetaDataSettings())
        # self.addPage(ModelDownloadPage())
        self.addPage(StableDiffusionLicense())
        self.addPage(AIRunnerLicense())
        self.addPage(UserAgreement())
        self.addPage(FinalPage())
        self.setWindowTitle("AI Runner Setup Wizard")


class WelcomePage(BaseWizard):
    def __init__(self):
        super(WelcomePage, self).__init__()

        self.setTitle("Welcome")
        layout = QVBoxLayout()
        label = QLabel("Welcome to the AI Runner setup wizard. Click Next to continue.")
        layout.addWidget(label)
        self.setLayout(layout)


class PathSettings(BaseWizard):
    class_name_ = Ui_PathSettings

    def initialize_form(self):
        self.ui.base_path.setText(self.settings["path_settings"]["base_path"])

    def save_settings(self):
        settings = self.settings
        settings["path_settings"]["base_path"] = self.ui.base_path.text()
        self.settings = settings


class MetaDataSettings(BaseWizard):
    widget_class_ = ExportPreferencesWidget


# class ModelDownloadPage(BaseWizard):
#     widget_class_ = ModelDownloadWidget


class AgreementPage(BaseWizard):
    def __init__(self):
        super(AgreementPage, self).__init__()
        self.user_agreement_clicked = False

    @Slot(bool)
    def agreement_clicked(self, val):
        self.user_agreement_clicked = val

    def nextId(self):
        if self.user_agreement_clicked:
            return super().nextId()


class StableDiffusionLicense(AgreementPage):
    class_name_ = Ui_stable_diffusion_license


class AIRunnerLicense(AgreementPage):
    class_name_ = Ui_airunner_license


class UserAgreement(AgreementPage):
    class_name_ = Ui_user_agreement


class FinalPage(BaseWizard):
    def __init__(self):
        super(FinalPage, self).__init__()

        self.setTitle("Setup Complete")
        layout = QVBoxLayout()
        label = QLabel("Setup is complete. Click Finish to close the wizard.")
        layout.addWidget(label)
        self.setLayout(layout)
