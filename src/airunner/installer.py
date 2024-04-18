################################################################
# Importing this module sets the Hugging Face environment
# variables for the application.
################################################################
from airunner.security.set_huggingface_env_variables import set_huggingface_environment_variables
set_huggingface_environment_variables(allow_downloads=True)
################################################################
# Import the main application class for AI Runner.
################################################################
from airunner.app_installer import AppInstaller


if __name__ == "__main__":
    AppInstaller()
