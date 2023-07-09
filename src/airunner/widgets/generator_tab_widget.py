from airunner.widgets.base_widget import BaseWidget


class GeneratorTabWidget(BaseWidget):
    name = "generator_tab"

    def set_stylesheet(self):
        super().set_stylesheet()
        self.sectionTabWidget.setStyleSheet(self.app.css("section_tab_widget"))
        self.stableDiffusionTabWidget.setStyleSheet(self.app.css("pipeline"))
        self.kandinskyTabWidget.setStyleSheet(self.app.css("pipeline"))
