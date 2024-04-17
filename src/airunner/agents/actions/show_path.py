import os
import subprocess

from sys import platform


def show_path(self, path):
    if not os.path.isdir(path):
        return
    if platform.system() == "Windows":
        subprocess.Popen(["explorer", os.path.realpath(path)])
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", os.path.realpath(path)])
    else:
        subprocess.Popen(["xdg-open", os.path.realpath(path)])