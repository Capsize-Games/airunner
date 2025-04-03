def get_version():
    version = None

    try:
        with open("./VERSION", "r") as f:
            version = f.read()
    except Exception as _e:
        pass

    if not version:
        try:
            # attempt to get from setup.py file in current directory (works for compiled python only)
            with open("./setup.py", "r") as f:
                version = f.read().strip()
                version = version.split("version=")[1].split(",")[0]
        except Exception as _e:
            pass

    if not version:
        # attempt to get from parent directory (works for uncompiled python only)
        try:
            with open("../../setup.py", "r") as f:
                version = f.read().strip()
                version = version.split("version=")[1].split(",")[0]
        except Exception as _e:
            pass
    if version:
        # remove anything other than numbers and dots
        version = "".join([c for c in version if c in "0123456789."])
        return version
    return ""
