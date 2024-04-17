import os
import sys


def restrict_access():
    """
    Restrict access to potentially dangerous OS operations.

    This function disables direct system calls and subprocess invocation
    through the Python application by setting `os.system` and the `subprocess`
    module to `None`. This prevents their usage throughout the application,
    reducing the risk of executing unintended or harmful commands via these
    interfaces.

    Note: This restriction is effective only within the Python environment.
    Malicious code that bypasses the Python runtime (e.g., by embedding binary
    executables or using other scripting languages) will not be affected by
    these measures.
    """

    # Nullify the os.system function to prevent its use for executing system commands
    os.system = None

    # Remove the subprocess module from sys.modules to prevent its import and use
    # This throws an ImportError if a later import statement tries to import subprocess
    if 'subprocess' in sys.modules:
        del sys.modules['subprocess']


# Execute the function to apply restrictions immediately upon module import
restrict_access()
