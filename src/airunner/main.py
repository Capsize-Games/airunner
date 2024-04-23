"""
----------------------------------------------------------------
Import order is crucial for AI Runner to work as expected.
Do not remove the no_internet_socket import.
Do not change the order of the imports.
----------------------------------------------------------------
"""
from nullscream import install_nullscream
install_nullscream(blacklist=["huggingface_hub"])

################################################################
# Importing this module ensures that the internet is completely
# disabled for the AI Runner application.
################################################################
from lockdown.network import no_internet_socket

################################################################
# Importing this restricts access to potentially dangerous OS
# operations, such as system calls and subprocess invocations.
################################################################
from lockdown.os.restrict_os_access import RestrictOSAccess
restrict_os_access = RestrictOSAccess()
restrict_os_access.install()

################################################################
# Import the main application class for AI Runner.
################################################################
from airunner.app import App


if __name__ == "__main__":
    App(restrict_os_access=restrict_os_access)
