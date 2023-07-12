class Themes:
    themes = {
        "dark": {
            "border": "1px solid #121212",
            "border-top": "1px solid #121212",
            "background-color": "#121212",
            "border-light": "border: 1px solid #333333",
            "color": "#333333",
            "thumbnail_label": """
                border: 1px solid #121212;
                border-radius: 0px;
                width: 32px;
                height: 32px;
            """,
            "section_tab_widget": """
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
            """,
            "pipeline": """
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
            """,
            "visible_button": """
                border: 1px solid #333333;
            """,
            "trigger_word": """
                border-top: 1px solid #333333;
                border-radius: 0px;
            """,
            "toolbar_widget": """
                QFrame {
                    background-color: #121212;
                    border-radius: 0px;
                }
            """,
            "footer_widget": """
                border-top: 1px solid #333333;
                border-radius: 0px;
            """,
            "toolmenu_tab_widget": """
                QTabBar::tab { 
                    font-size: 9pt;
                }
                QTabWidget::pane { 
                    border: 0;
                    border-top: 1px solid #121212;
                    border-bottom: 1px solid #121212;
                    border-radius: 0px; 
                }
                QTabBar::tab { 
                    border-radius: 0px; 
                    margin: 0px; 
                    padding: 5px 10px;
                    border: 0px;
                }
                QTabBar::tab:selected { 
                    background-color: #5483d0;
                    color: white;
                    border: 0px;
                }
            """,
            "layer_highlight_style": """
                background-color: #8ab4f7;
                color: #333333;
                border: none; border-radius: 0px;
            """,
            "layer_normal_style": """
                background-color: transparent;
                color: #d2d2d2;
                border: none;
                border-radius: 0px;
            """,
            "center_panel": """
                QTabWidget::pane { 
                    border: 0;
                    border-left: 0;
                    border-radius: 0px;
                    background: #222222;
                    border-bottom: 1px solid #121212;
                }
                QTabBar::tab { 
                    border-radius: 0px; 
                    margin: 0px; 
                    padding: 5px 10px;
                    border: 0px;
                    font-size: 9pt;
                }
                QTabBar::tab:selected {
                    background-color: #5483d0;
                    color: white;
                    border: 0px;
                }
            """,
            "generator_tab": """
                QTabWidget::pane { 
                    border: 0;
                    border-left: 0;
                    border-radius: 0px;
                    background: #222222;
                }
                QTabBar::tab { 
                    border-radius: 0px; 
                    margin: 0px; 
                    padding: 5px 10px;
                    border: 0px;
                    font-size: 9pt;
                }
            """,
            "layer_container_widget": """
                #layers {
                    border: 0px;
                    background-color: #151515;
                }
            """,
            "embeddings_container": """
                background-color: #151515;
            """,
            "lora_container": """
                background-color: #151515;
            """,
            "slider": """
               QSlider::handle:horizontal { 
                   height: 20px;
                   width: 25px;
                   border: 1px solid #5483d0;
                   border-radius: 0px;
               }
               QSlider::handle:horizontal:hover {
                   background-color: #5483d0;
               }
               QSlider::groove:horizontal {
                   height: 25px;
                   background-color: transparent;
                   border: transparent;
                   border: 1px solid #555;
                   border-right: 0px;
                   border-radius: 0px;
               }
               background-color: transparent;
            """,
            "slider_label": """
                font-size: 9pt;
                color: #ffffff;
                font-weight: bold;
            """,
            "slider_spinbox": """
                background-color: #444444;
                border-left: none;
                border-color: #555;
                border-radius: 0px;
            """,
            "header_widget": """
                #frame {
                    border-radius: 0px;
                    border: 0px;
                    border-bottom: 1px solid #333333;
                }
            """,
            "prompt_builder_widget": """
                QTabWidget::pane {
                    border: 0;
                    border-left: 0;
                    border-radius: 0px;
                    background: #222222;
                    border-top: 1px solid #121212;
                }
                QTabBar::tab { 
                    border-radius: 0px; 
                    margin: 0px; 
                    padding: 5px 10px;
                    border: 0px;
                    font-size: 9pt;
                }
                QTabBar::tab:selected {
                    background-color: #5483d0;
                    color: white;
                    border: 0px;
                }
            """,
        },
        "light": {
            "border": "1px solid #d2d2d2",
            "border-top": "1px solid #d2d2d2",
            "background-color": "#f2f2f2",
            "border-light": "border: 1px solid #e2e2e2",
            "color": "#ffffff",
            "thumbnail_label": """
                border: 1px solid #d2d2d2;
                border-radius: 0px;
                width: 32px;
                height: 32px;
            """,
            "section_tab_widget": """
                QTabWidget::pane { 
                    border: 0;
                    border-radius: 0px;
                    border-top: 1px solid #d2d2d2;
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
            """,
            "pipeline": """
                QTabWidget::pane { 
                    border: 0;
                    border-left: 1px solid #d2d2d2;
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
            """,
            "visible_button": """
                border: 1px solid #e2e2e2;
            """,
            "trigger_word": """
                border-top: 1px solid #d2d2d2;
                border-radius: 0px;
            """,
            "toolbar_widget": """
                QFrame {
                    background-color: #f2f2f2;
                    border-radius: 0px;
                }
            """,
            "footer_widget": """
                border-top: 1px solid #d2d2d2;
                border-radius: 0px;
            """,
            "toolmenu_tab_widget": """
                QTabBar::tab { 
                    font-size: 9pt;
                }
                QTabWidget::pane { 
                    border: 0;
                    border-top: 1px solid #d2d2d2;
                    border-bottom: 1px solid #d2d2d2;
                    border-radius: 0px; 
                }
                QTabBar::tab { 
                    border-radius: 0px; 
                    margin: 0px; 
                    padding: 5px 10px;
                    border: 0px;
                }
                QTabBar::tab:selected { 
                    background-color: #5483d0;
                    color: white;
                    border: 0px;
                }
            """,
            "layer_highlight_style": """
                background-color: #d2d2d2;
                color: #000;
                border: none; 
                border-radius: 0px;
            """,
            "layer_normal_style": """
                background-color: transparent;
                color: #666;
                border: none;
                border-radius: 0px;
            """,
            "center_panel": """
                QTabWidget::pane { 
                    border: 0;
                    border-left: 0;
                    border-radius: 0px;
                    background: #f2f2f2;
                    border-bottom: 1px solid #d2d2d2;
                }
                QTabBar::tab { 
                    border-radius: 0px; 
                    margin: 0px; 
                    padding: 5px 10px;
                    border: 0px;
                    font-size: 9pt;
                }
                QTabBar::tab:selected {
                    background-color: #5483d0;
                    color: white;
                    border: 0px;
                }
            """,
            "generator_tab": """
                QTabWidget::pane { 
                    border: 0;
                    border-left: 0;
                    border-radius: 0px;
                    background: #f2f2f2;
                }
                QTabBar::tab { 
                    border-radius: 0px; 
                    margin: 0px; 
                    padding: 5px 10px;
                    border: 0px;
                    font-size: 9pt;
                }
            """,
            "layer_container_widget": """
                #layers {
                    border: 0px;
                    background-color: #f2f2f2;
                }
            """,
            "embeddings_container": """
                background-color: #f2f2f2;
            """,
            "lora_container": """
                background-color: #f2f2f2;
            """,
            "slider": """
               QSlider::handle:horizontal { 
                   height: 20px;
                   width: 25px;
                   border: 1px solid #5483d0;
                   border-radius: 0px;
               }
               QSlider::handle:horizontal:hover {
                   background-color: #5483d0;
               }
               QSlider::groove:horizontal {
                   height: 25px;
                   background-color: transparent;
                   border: transparent;
                   border: 1px solid #e2e2e2;
                   border-right: 0px;
                   border-radius: 0px;
               }
               background-color: transparent;
            """,
            "slider_label": """
                font-size: 9pt;
                color: #ffffff;
            """,
            "slider_spinbox": """
                background-color: #a2a2a2;
                border-left: none;
                border-color: #c2c2c2;
                border-radius: 0px;
            """,
            "header_widget": """
                #frame {
                    border-radius: 0px;
                    border: 0px;
                    border-bottom: 1px solid #e2e2e2;
                }
            """,
            "prompt_builder_widget": """
                QTabWidget::pane {
                    border: 0;
                    border-left: 0;
                    border-radius: 0px;
                    background: #f2f2f2;
                    border-top: 1px solid #d2d2d2;
                }
                QTabBar::tab { 
                    border-radius: 0px; 
                    margin: 0px; 
                    padding: 5px 10px;
                    border: 0px;
                    font-size: 9pt;
                }
                QTabBar::tab:selected {
                    background-color: #5483d0;
                    color: white;
                    border: 0px;
                }
            """,
        },
        "all": {
            "border-radius": "0px",
            "font-size": "9pt",
            "layer_widget": """
                font-size: 9pt
            """,
            "lora_widget": """
                font-size: 9pt
            """,
        },
    }

    def __init__(self, settings_manager):
        self.settings_manager = settings_manager

    def dark_mode_enabled(self):
        return self.settings_manager.settings.dark_mode_enabled.get()

    def css(self, styles):
        theme_name = "light"
        if self.dark_mode_enabled():
            theme_name = "dark"
        try:
            return self.themes.get(theme_name, {}).get(styles, self.themes.get("all", {}).get(styles, ""))
        except KeyError:
            return ""
