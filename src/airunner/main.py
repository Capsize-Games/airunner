"""
----------------------------------------------------------------
Import order is crucial for AI Runner to work as expected.
Do not remove the no_internet_socket import.
Do not change the order of the imports.
----------------------------------------------------------------
"""
################################################################
# Importing this module ensures that the internet is completely
# disabled for the AI Runner application.
################################################################
from airunner.security import no_internet_socket

################################################################
# Importing this restricts access to potentially dangerous OS
# operations, such as system calls and subprocess invocations.
################################################################
from airunner.security import restrict_os_access

################################################################
# Import the main application class for AI Runner.
################################################################
from airunner.app import App


if __name__ == "__main__":
    App()
