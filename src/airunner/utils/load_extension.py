import os
import sys


def load_extension(extension_dir):
    # Create a subdirectory for the installed libraries
    install_dir = os.path.join(extension_dir, "libs")
    os.makedirs(install_dir, exist_ok=True)

    # Read the dependencies file
    with open(os.path.join(extension_dir, "dependencies.txt")) as f:
        dependencies = f.read().splitlines()

    # Install the dependencies
    for url in dependencies:
        install_library_from_url(url, install_dir)

    # Add the directory to sys.path
    sys.path.append(install_dir)

    # Now you can import any library that was in the extension's dependencies


