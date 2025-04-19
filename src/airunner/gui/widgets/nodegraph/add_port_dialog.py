from PySide6.QtWidgets import (
    QLineEdit,
    QDialog,
    QFormLayout,
    QDialogButtonBox,
)


class AddPortDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Port")
        layout = QFormLayout(self)

        self.port_name_input = QLineEdit(self)
        self.port_type_input = QLineEdit(
            self
        )  # Simple text for now, could be dropdown

        layout.addRow("Port Name:", self.port_name_input)
        layout.addRow("Port Type (optional):", self.port_type_input)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def get_port_info(self):
        return self.port_name_input.text(), self.port_type_input.text()
