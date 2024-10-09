import os
import subprocess


def show_path(path):
    path = os.path.expanduser(path)
    if not os.path.isdir(path):
        print("not a path", path)
        return

    from sys import platform
    platform = platform.lower()
    if platform in ["windows", "win32", "cygwin"]:
        subprocess.Popen(["explorer", os.path.realpath(path)])
    elif platform in ["linux", "linux2"]:
        subprocess.Popen(["xdg-open", os.path.realpath(path)])
    else:
        print("unsupported platform", platform)
