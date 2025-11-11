"""
Dialog for confirming disabling the NSFW filter, with a 'do not show again' checkbox.
"""

from PySide6.QtWidgets import QMessageBox, QCheckBox


def show_nsfw_warning_dialog(parent, show_again_default=True):
    """Show a warning dialog about disabling the NSFW filter.

    Args:
        parent: The parent widget.
        show_again_default: Whether the 'do not show again' box is checked by default.
    Returns:
        (confirmed: bool, do_not_show_again: bool)
    """
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle("Disable Safety Checker Warning")
    msg_box.setText(
        (
            "WARNING\n\n"
            "You are attempting to disable the safety checker (NSFW filter).\n"
            "It is strongly recommended that you keep this enabled at all times.\n"
            "The Safety Checker prevents potentially harmful content from being displayed.\n"
            "Only disable it if you are sure the Image model you are using is not capable of generating "
            "harmful content.\n"
            "Disabling the safety checker is intended as a last resort for continual false positives and as a "
            "research feature.\n"
            "\n\n"
            "Are you sure you want to disable the filter?"
        )
    )
    msg_box.setStandardButtons(
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    msg_box.setDefaultButton(QMessageBox.StandardButton.No)
    checkbox = QCheckBox("Do not show this warning again")
    checkbox.setChecked(not show_again_default)
    msg_box.setCheckBox(checkbox)
    result = msg_box.exec()
    confirmed = result == QMessageBox.StandardButton.Yes
    do_not_show_again = checkbox.isChecked()
    return confirmed, do_not_show_again
