import os.path
import re


def get_full_file_path(
    file_path: str,
    file_name: str,
    path_settings: dict,
    section: str,
    logger
) -> str:
    """
    Gets the full file path.
    :param file_path:
    :param path_settings:
    :param logger:
    :return:
    """
    # Validate the input
    if not isinstance(file_path, str) or not re.match(r'^[\w\-./]+$', file_path):
        logger.error(f"Invalid file path {file_path}")
        return None

    if not os.path.isabs(file_path):
        file_path = os.path.join(path_settings[f"{section}_model_path"], file_path, file_name)
        file_path = os.path.expanduser(file_path)
        file_path = os.path.abspath(file_path)  # Get the absolute path and resolve any symbolic links

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        logger.error(f"File path {file_path} does not exist or is not a file")
        return None

    return file_path
