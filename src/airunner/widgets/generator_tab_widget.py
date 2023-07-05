from airunner.widgets.base_widget import BaseWidget


class GeneratorTabWidget(BaseWidget):
    name = "generator_tab"

    def set_stylesheet(self):
        super().set_stylesheet()
        section_tab_widget_styles = """
            QTabWidget::pane { 
                border: 0;
                border-radius: 0px;
                border-top: 1px solid #121212;
            }
            QTabBar::tab {
                border-radius: 0px; 
                margin: 0px;
                padding: 5px 10px;
                border: 0px;
            }
            QTabBar::tab::first {
                margin-left: 26px;
            }
            QTabBar::tab:selected { 
                background-color: #5483d0;
                color: white;
                border: 0px;
            }
        """
        pipeline_styles = """
            QTabWidget::pane { 
                border: 0;
                border-left: 1px solid #121212;
                border-radius: 0px; 
            }
            QTabBar::tab { 
                border-radius: 0px; 
                margin: 0px; 
                padding: 10px 5px;
                border: 0px;
                font-size: 9pt;
                width: 12px;
            }
            QTabBar::tab:selected { 
                background-color: #5483d0;
                color: white;
                border: 0px;
            }
        """
        self.sectionTabWidget.setStyleSheet(section_tab_widget_styles)
        self.stableDiffusionTabWidget.setStyleSheet(pipeline_styles)
        self.kandinskyTabWidget.setStyleSheet(pipeline_styles)