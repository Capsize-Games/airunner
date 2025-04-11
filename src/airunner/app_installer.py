####################################################################################################
# Do not remove the following import statement or change
# the order of the imports.
####################################################################################################
import sys
import signal

from PySide6.QtCore import (
    QObject
)
from PySide6.QtGui import (
    Qt
)
from PySide6.QtWidgets import (
    QApplication
)

from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.gui.windows.download_wizard.download_wizard_window import DownloadWizardWindow
from airunner.gui.windows.main.settings_mixin import SettingsMixin
from airunner.gui.windows.setup_wizard.setup_wizard_window import SetupWizardWindow


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
        self,
        close_on_cancel: bool = True
    ):
        """
        Initialize the application and run as a GUI application or a socket server.
        """

        self.wizard = None
        self.download_wizard = None
        self.app = None
        self.close_on_cancel = close_on_cancel

        """
        Mediator and Settings mixins are initialized here, enabling the application
        to easily access the application settings dictionary.
        """
        super().__init__()

        self.start()

    @property
    def do_show_setup_wizard(self) -> bool:
        """
        This flag is used to determine if the setup wizard should be displayed.
        If the setup wizard has not been completed, various agreements have not been accepted,
        or the paths have not been initialized, the setup wizard will be displayed.
        :return: bool
        """
        return (
            (
                # self.wizard.setup_settings["paths_initialized"] and
                self.application_settings.user_agreement_checked and
                self.application_settings.stable_diffusion_agreement_checked and
                self.application_settings.airunner_agreement_checked
            )
        )

    def start(self):
        """
        Conditionally initialize and display the setup wizard.
        :return:
        """
        signal.signal(signal.SIGINT, self.signal_handler)
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])

        self.wizard = SetupWizardWindow()
        self.wizard.exec()

        if self.wizard.canceled:
            print("canceled")
            self.cancel()
            return

        self.download_wizard = DownloadWizardWindow()
        self.download_wizard.exec()

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
            AppInstaller.quit()
            sys.exit(0)
        except Exception as e:
            print(e)
            sys.exit(0)

    def cancel(self):
        self.wizard.close()
        if self.download_wizard:
            self.download_wizard.close()
        if self.close_on_cancel:
            self.quit()
            sys.exit(0)

    @staticmethod
    def quit():
        app = QApplication.instance()
        app.quit()
