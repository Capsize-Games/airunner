import os


from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.gif.gif_widget import GifWidget
from airunner.widgets.gif.templates.gif_panel_ui import Ui_gif_panel_widget


class GifPanelWidget(BaseWidget):
    widget_class_ = Ui_gif_panel_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        gif_path = self.settings_manager.path_settings.gif_path
        for root, dirs, files in os.walk(gif_path):
            for file in files:
                if file.endswith(".gif"):
                    gif_widget = GifWidget(self)
                    gif_widget.set_gif(os.path.join(root, file))
                    self.ui.scrollAreaWidgetContents.layout().addWidget(gif_widget)