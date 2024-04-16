"""
----------------------------------------------------------------
Import order is crucial for AI Runner to work as expected.
Do not remove the no_internet_socket import.
Do not change the order of the imports.
Importing this module ensures that the internet is completely
disabled for the AI Runner application.
See the no_internet_socket module for more information.
----------------------------------------------------------------
"""
from airunner.utils import no_internet_socket
from airunner.app import App


if __name__ == "__main__":
    App()
