def validate_path(path) -> bool:
    """
    Validates the provided file path to ensure it is secure against common security threats
    like path traversal. Raises ValueError if an invalid path is detected.

    Parameters:
        path (str): The file path to validate.

    Returns:
        str: The original path if it is deemed safe.

    Raises:
        ValueError: If the path contains dangerous patterns.
    """
    import re
    # Disallow characters that might indicate insecure paths
    if re.search(r'[<>:"\\|?*]', path):  # Removed '/' from the pattern
        print(f"Invalid characters in path: {path}")
        raise ValueError("Invalid characters in path.")
    # Block path traversal and absolute paths
    if '..' in path or path.startswith(('/', '\\')):
        raise ValueError("Path traversal attempt detected.")
    return True
