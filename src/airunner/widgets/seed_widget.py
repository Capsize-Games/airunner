from functools import partial

from PIL import Image

from airunner.utils import image_to_pixmap
from airunner.widgets.base_widget import BaseWidget


class SeedWidget(BaseWidget):
    name = "seed_widget"
    icons = {
        "random_button": "049-dice",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.template.random_button.clicked.connect(self.handle_seed_random_clicked)
        self.template.lineEdit.setText(str(self.app.seed))
        self.template.lineEdit.textChanged.connect(self.handle_seed_value_changed)

        self.template.random_button.setChecked(self.app.settings.random_seed.get())
        self.template.lineEdit.setEnabled(not self.app.settings.random_seed.get())

        self.set_stylesheet()

    def update_seed(self):
        self.lineEdit.setText(str(self.app.seed))

    def handle_seed_random_clicked(self, value):
        self.app.settings.random_seed.set(value)
        self.template.lineEdit.setEnabled(not value)

    def handle_seed_value_changed(self, value):
        self.app.seed = value


class LatentsSeedWidget(SeedWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.template.label.setText("Image Seed")
        self.update_seed()
        self.template.random_button.setChecked(self.app.settings.random_latents_seed.get())
        self.template.lineEdit.setEnabled(not self.app.settings.random_latents_seed.get())

    def update_seed(self):
        self.lineEdit.setText(str(self.app.latents_seed))

    def handle_seed_random_clicked(self, value):
        self.app.settings.random_latents_seed.set(value)
        self.template.lineEdit.setEnabled(not value)

    def handle_seed_value_changed(self, value):
        self.app.latents_seed = value