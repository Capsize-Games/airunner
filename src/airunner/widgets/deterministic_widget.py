from airunner.widgets.base_widget import BaseWidget


class DeterministicWidget(BaseWidget):
    name = "deterministic_widget"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # add items to category combobox
        self.template.category.addItems([
            "Style",
            "Color"
        ])
        self.template.generate_batches_button.clicked.connect(self.app.generate_deterministic_callback)

    @property
    def deterministic_style(self):
        return self.template.category.currentText().lower()

    @property
    def batch_size(self):
        # get value from QSpinBox:
        return self.template.images_per_batch.value()

