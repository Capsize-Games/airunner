"""
----------------------------------------------------------------
Import order is crucial for AI Runner to work as expected.
Do not remove the no_internet_socket import.
Do not change the order of the imports.
----------------------------------------------------------------
"""
################################################################
# Import the main application class for AI Runner.
################################################################
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from airunner.windows.download_wizard.download_wizard_window import DownloadWizardWindow


if __name__ == "__main__":
    # Run the AI Runner application.
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
    app = QApplication([])
    download_wizard = DownloadWizardWindow()
    download_wizard.exec()
