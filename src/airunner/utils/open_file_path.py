from PySide6.QtWidgets import QFileDialog


def open_file_path(label="Import Image", directory="", file_type="Image Files (*.png *.jpg *.jpeg)"):
    return QFileDialog.getOpenFileName(
        None, label, directory, file_type
    )


