from airunner.components.home_stage.gui.widgets.templates.home_stage_ui import (
    Ui_home_stage_widget,
)
from airunner.gui.widgets.base_widget import BaseWidget


class HomeStageWidget(BaseWidget):

    widget_class_ = Ui_home_stage_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def showEvent(self, event):
        super().showEvent(event)
        # Render the home page template in the webEngineView
        try:
            # Assuming a render_template method exists in BaseWidget (like ConversationWidget)
            self.render_template(self.ui.webEngineView, "home.jinja2.html")
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(f"Failed to render home template: {e}")
            else:
                print(f"Failed to render home template: {e}")

    def set_theme(self, theme_name: str):
        """
        Set the theme for the home widget by updating the CSS in the webEngineView.
        This will call the setTheme JS function in the loaded HTML.
        """
        if hasattr(self.ui, "webEngineView"):
            # This will call the JS function in the webEngineView
            js = f"window.setTheme && window.setTheme('{theme_name}');"
            self.ui.webEngineView.page().runJavaScript(js)
