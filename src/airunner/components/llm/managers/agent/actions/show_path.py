import os
from PySide6.QtWidgets import QFileDialog


def show_path(path):
    path = os.path.expanduser(path)
    if not os.path.isdir(path):
        print(f"Error: {path} is not a valid directory")  # Debug statement
        return

    # Use QFileDialog to open a file browser dialog
    file_dialog = QFileDialog()
    file_dialog.setFileMode(QFileDialog.Directory)
    file_dialog.setDirectory(path)
    # file_dialog.setOption(QFileDialog.ShowDirsOnly, True)

    if file_dialog.exec():
        selected_directory = file_dialog.selectedFiles()[0]
    else:
        print("User canceled the file dialog")  # Debug statement
