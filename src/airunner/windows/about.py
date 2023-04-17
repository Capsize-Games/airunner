from airunner.windows.base_window import BaseWindow
# open the version file from the root of the project and get the VERSION variable string from it


class AboutWindow(BaseWindow):
    template_name = "about"
    window_title = "About AI Runner"
