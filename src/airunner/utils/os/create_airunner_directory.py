import os

from airunner.data.models import PathSettings


def create_airunner_paths(path_settings: PathSettings):
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
    for attr in (
        "base_path",
        "documents_path",
        "ebook_path",
        "image_path",
        "llama_index_path",
        "webpages_path",
        "stt_model_path",
        "tts_model_path",
    ):
        path = getattr(path_settings, attr)
        # Path sanitization
        path = path.replace("..", "")

        # Permission check and directory creation
        try:
            path = os.path.expanduser(path)
            if not os.path.exists(path):
                try:
                    os.makedirs(path, exist_ok=True)
                except FileExistsError:
                    pass
        except PermissionError:
            print(f"No permission to create directory at {path}")
        except Exception as e:
            print(f"Failed to create directory {path}: {e}")
