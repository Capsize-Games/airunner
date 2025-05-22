from PySide6.QtCore import Slot
from airunner.data.models.application_settings import ApplicationSettings
from airunner.gui.windows.setup_wizard.age_restriction.templates.age_restriction_ui import (
    Ui_age_restriction_warning,
)
from airunner.gui.windows.setup_wizard.user_agreement.agreement_page import (
    AgreementPage,
)


class AgeRestrictionWarning(AgreementPage):
    class_name_ = Ui_age_restriction_warning

    def __init__(self, *args, **kwargs):
        super(AgeRestrictionWarning, self).__init__(*args, **kwargs)

        self.age_restriction_agreed = False
        self.read_age_restriction_agreement = False

    @Slot(bool)
    def read_agreement_clicked(self, val: bool):
        self.read_age_restriction_agreement = val
        self.agreed = val
        self.completeChanged.emit()
        self.update_settings()

    @Slot(bool)
    def age_agreement_clicked(self, val: bool):
        self.age_restriction_agreed = val
        self.update_application_settings(self.setting_key, val)
        self.agreed = val
        self.completeChanged.emit()
        self.update_settings()

    def update_settings(self):
        ApplicationSettings.objects.update(
            ApplicationSettings.objects.first().id,
            age_agreement_checked=(
                self.age_restriction_agreed
                and self.read_age_restriction_agreement
            ),
        )
