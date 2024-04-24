"""
----------------------------------------------------------------
Import order is crucial for AI Runner to work as expected.
Do not remove the no_internet_socket import.
Do not change the order of the imports.
----------------------------------------------------------------
"""
import facehuggershield.huggingface


################################################################
# Import the main application class for AI Runner.
################################################################
from airunner.app import App

if __name__ == "__main__":
    App(restrict_os_access=None)
