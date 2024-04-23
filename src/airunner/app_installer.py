####################################################################################################
# Do not remove the following import statement or change
# the order of the imports.
####################################################################################################
from tcog_utils.security import set_huggingface_env_variables
import sys
import signal
from PySide6.QtCore import (
    QObject,
)
from PySide6.QtGui import (
    Qt,
    QWindow
)
from PySide6.QtWidgets import (
    QApplication,
)
from airunner.mediator_mixin import MediatorMixin
from airunner.windows.download_wizard.download_wizard_window import DownloadWizardWindow
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.windows.setup_wizard.setup_wizard_window import SetupWizard
from airunner.aihandler.logger import Logger


class AppInstaller(
    QObject,
    SettingsMixin,
    MediatorMixin
):
    """
    The main application class for AI Runner.
    This class can be run as a GUI application or as a socket server.
    """
    def __init__(
        self
    ):
        """
        Initialize the application and run as a GUI application or a socket server.
        """

        self.wizard = None
        self.download_wizard = None
        self.app = None
        self.logger = Logger(prefix=self.__class__.__name__)

        """
        Mediator and Settings mixins are initialized here, enabling the application
        to easily access the application settings dictionary.
        """
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        super(AppInstaller, self).__init__()

        self.start()
        sys.exit(0)

    @property
    def do_show_setup_wizard(self) -> bool:
        """
        This flag is used to determine if the setup wizard should be displayed.
        If the setup wizard has not been dcompleted, various agreements have not been accepted,
        or the paths have not been initialized, the setup wizard will be displayed.
        :return: bool
        """
        return (
            self.settings["run_setup_wizard"] or
            not self.settings["paths_initialized"] or
            not self.settings["agreements"]["user"] or
            not self.settings["agreements"]["stable_diffusion"] or
            not self.settings["agreements"]["airunner"]
        )

    @property
    def do_show_download_wizard(self) -> bool:
        """
        This flag is used to determine if the download wizard should be displayed.
        If the download wizard has not been completed, the download wizard will be displayed.
        :return: bool
        """
        return not self.settings["download_wizard_completed"]

    def start(self):
        """
        Conditionally initialize and display the setup wizard.
        :return:
        """
        signal.signal(signal.SIGINT, self.signal_handler)
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
        self.app = QApplication([])

        self.wizard = SetupWizard()
        self.wizard.exec()

        # Quit the application if the setup wizard was not completed
        if self.do_show_setup_wizard:
            sys.exit(0)

        if self.do_show_download_wizard:
            print("STARTING DOWNLOAD WIZARD")
            self.download_wizard = DownloadWizardWindow(self.wizard.setup_settings)
            self.download_wizard.exec()
            print("continuing")



    def run(self):
        """
        Run as a GUI application.
        A splash screen is displayed while the application is loading
        and a main window is displayed once the application is ready.

        Override this method to run the application in a different mode.
        """

        # Continue with application execution
        splash = self.display_splash_screen(self.app)

        # Show the main application window
        QTimer.singleShot(
            50,
            partial(
                self.show_main_application,
                self.app,
                splash
            )
        )
        sys.exit(self.app.exec())

    @staticmethod
    def signal_handler(
        _signal,
        _frame
    ):
        """
        Handle the SIGINT signal in a clean way.
        :param _signal:
        :param _frame:
        :return: None
        """
        print("\nExiting...")
        try:
            app = QApplication.instance()
            app.quit()
            sys.exit(0)
        except Exception as e:
            print(e)
            sys.exit(0)

    @staticmethod
    def display_splash_screen(app):
        """
        Display a splash screen while the application is loading.
        :param app:
        :return:
        """
        screens = QGuiApplication.screens()
        try:
            screen = screens.at(0)
        except AttributeError:
            screen = screens[0]
        pixmap = QPixmap("images/splashscreen.png")
        splash = QSplashScreen(
            screen,
            pixmap,
            QtCore.Qt.WindowType.WindowStaysOnTopHint
        )
        splash.show()
        # make message white
        splash.showMessage(
            f"Loading AI Runner v{get_version()}",
            QtCore.Qt.AlignmentFlag.AlignBottom | QtCore.Qt.AlignmentFlag.AlignCenter,
            QtCore.Qt.GlobalColor.white
        )
        app.processEvents()
        return splash

