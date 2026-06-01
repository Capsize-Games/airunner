import os
import sys
from pyflakes.api import checkPath
from pyflakes.reporter import Reporter


class CustomReporter(Reporter):
    """Custom reporter to filter and format pyflakes output."""

    def __init__(self):
        super().__init__(sys.stdout, sys.stderr)

    def flake(self, message):
        if "imported but unused" in str(message):
            print(
                f"{message.filename}:{message.lineno}: "
                f"{message.message % message.message_args}"
            )


def scan_with_pyflakes(target_directory: str):
    if not os.path.exists(target_directory):
        print(
            f"Error: The directory '{target_directory}' does not exist."
        )
        return

    reporter = CustomReporter()
    excluded_suffixes = ("_ui.py", "_rc.py")
    excluded_dirs = {"alembic", "vendor", "__pycache__"}

    for root, dirs, files in os.walk(target_directory):
        dirs[:] = [
            d for d in dirs if d not in excluded_dirs
        ]
        for file in files:
            if file.endswith(".py"):
                if file.endswith(excluded_suffixes):
                    continue
                full_path = os.path.join(root, file)
                checkPath(full_path, reporter=reporter)


if __name__ == "__main__":
    target_path = os.path.join(
        "services", "src", "airunner_services"
    )
    scan_with_pyflakes(target_path)
