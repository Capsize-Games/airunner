from airunner.windows.base_window import BaseWindow


class SetupWizard(BaseWindow):
    template_name = "setup_wizard"
    window_title = "Setup Wizard"
    _current_step = 1

    @property
    def current_step(self):
        return self._current_step

    @current_step.setter
    def current_step(self, value):
        if value < 1:
            value = 1
        self._current_step = value
        self.set_step()

    def initialize_window(self):
        description = ""
        input_variable_name = ""
        input_variable_type = ""
        if self.current_step == 1:
            description = "Choose the base path"
            input_variable_name = "base_path"
            input_variable_type = "string"

        self.template.description.setText(description)
        self.template.step.setText(f"Step {self.current_step}")
        self.template.back_button.clicked.connect(self.back)
        self.template.next_button.clicked.connect(self.next)

    def back(self):
        self.set_step(self.current_step - 1)

    def next(self):
        self.set_step(self.current_step + 1)
