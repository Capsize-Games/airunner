import os


def create_airunner_paths(path_settings: dict):
    """
    This function creates directories based on the paths provided in the path_settings dictionary.

    The function validates the paths, sanitizes them by removing "..", checks if the application has
    the necessary permissions to create a directory in the specified path, and handles any exceptions
    that might occur when creating the directory.

    Parameters:
    path_settings (dict): A dictionary where the keys are the names of the paths and the values are
    the paths themselves.

    Returns:
    None
    """
    print("Creating directories...")

    for k, path in path_settings.items():
        # Path sanitization
        path = path.replace('..', '')

        # Permission check and directory creation
        try:
            if not os.path.exists(path):
                os.makedirs(path)
        except PermissionError:
            print(f"No permission to create directory at {path}")
        except Exception as e:
            print(f"Failed to create directory {path}: {e}")
