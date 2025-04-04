from PySide6.QtWidgets import QFileDialog


def open_file_path(parent=None, label="Import Image", directory="", file_type="Image Files (*.png *.jpg *.jpeg)"):
    return QFileDialog.getOpenFileName(
        parent, label, directory, file_type
    )
