from PySide6.QtCore import Slot
from airunner.gui.windows.setup_wizard.age_restriction.templates.age_restriction_ui import Ui_age_restriction_warning
from airunner.gui.windows.setup_wizard.base_wizard import BaseWizard


class AgeRestrictionWarning(BaseWizard):
    class_name_ = Ui_age_restriction_warning

    def __init__(self, *args, **kwargs):
        super(AgeRestrictionWarning, self).__init__(*args, **kwargs)

        self.age_restriction_agreed = False
        self.read_age_restriction_agreement = False

    @Slot(bool)
    def read_agreement_clicked(self, val: bool):
        self.read_age_restriction_agreement = val

    @Slot(bool)
    def age_agreement_clicked(self, val: bool):
        self.age_restriction_agreed = val
