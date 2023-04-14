from airunner.windows.base_window import BaseWindow
# open the version file from the root of the project and get the VERSION variable string from it
with open("../../version.py", "r") as f:
    VERSION = f.read().split("=")[1].strip().replace('"', "")



class AboutWindow(BaseWindow):
    template_name = "about"
    window_title = "About AI Runner"

    def initialize_window(self):
        self.template.title.setText(f"AI Runner {VERSION}")
