# Copyright (C) 2023 Capsize LLC.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR BSD-3-Clause
from PyQt6.QtWidgets import QWidget
from PySide6.QtDesigner import QPyDesignerCustomWidgetCollection

# Set PYSIDE_DESIGNER_PLUGINS to point to this directory and load the plugin
from airunner.pyqt.widgets.generator_form.generatorform import Ui_generator_form
from airunner.pyqt.widgets.generator_form.generatorformplugin import GeneratorFormPlugin

if __name__ == '__main__':
    QPyDesignerCustomWidgetCollection.addCustomWidget(GeneratorFormPlugin())


class GeneratorForm(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = Ui_generator_form()
        self.ui.setupUi(self)
