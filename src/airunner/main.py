"""
----------------------------------------------------------------
Import order is crucial for AI Runner to work as expected.
Do not remove the no_internet_socket import.
Do not change the order of the imports.
----------------------------------------------------------------
"""
################################################################
# Importing this module sets the Hugging Face environment
# variables for the application.
################################################################
import facehuggershield
facehuggershield.huggingface.activate(show_stdout=True)

################################################################
# Import the main application class for AI Runner.
################################################################
from airunner.app import App


if __name__ == "__main__":

    App(
        restrict_os_access=None,
        defendatron=facehuggershield.huggingface.defendatron
    )
