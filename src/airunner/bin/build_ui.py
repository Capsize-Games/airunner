"""
A class which builds the UI for the application.

This is a stand alone function which:

1. Recursively finds all *.ui files under src/airunner/
2. Runs `pyside6-uic -o <file_name>_ui.py <file_name>.ui` on each *.ui file, only if the .ui file is newer than the corresponding _ui.py file or the _ui.py file does not exist
3. Runs `pyside6-rcc -o resources.py resources.qrc`
4. Runs process_qss to build styles.qss for each theme from variables.qss + master.qss

The function will run using the venv python interpreter
"""

import os
import re
import subprocess
from pathlib import Path

from airunner.bin.process_qss import build_all_theme_css, generate_resources, process_qss


def adjust_resource_imports(input_file, output_file):
    """
    Adjusts resource imports in the generated *_ui.py file.
    Checks if the file exists before processing to avoid errors.
    """
    if not os.path.exists(input_file):
        print(f"Warning: {input_file} does not exist. Skipping resource import adjustment.")
        return
    
    try:
        pattern = re.compile(r"^import (.+_rc)$", re.MULTILINE)
        replacement = r"import airunner.\1"
        with open(input_file, "r") as file:
            content = file.read()
        adjusted_content = re.sub(pattern, replacement, content)
        with open(output_file, "w") as file:
            file.write(adjusted_content)
    except (IOError, OSError) as e:
        print(f"Error adjusting resource imports for {input_file}: {e}. Skipping.")


def build_ui():
    """Builds all UI files in the project if needed."""
    base_path = Path(__file__).parent.parent
    print(f"Base path: {base_path}")
    ui_files = list(base_path.glob("**/*.ui"))
    print(f"Found {len(ui_files)} .ui files")
    for ui_file in ui_files:
        print(f"Processing: {ui_file}")
        ui_file_py = ui_file.with_name(ui_file.stem + "_ui.py")
        print(f"Target: {ui_file_py}")
        # Only build if .ui is newer than _ui.py or _ui.py does not exist
        if (
            not ui_file_py.exists()
            or ui_file.stat().st_mtime > ui_file_py.stat().st_mtime
        ):
            print(f"Building {ui_file_py} from {ui_file}")
            result = subprocess.run(
                [
                    "pyside6-uic",
                    "-o",
                    str(ui_file_py),
                    str(ui_file),
                ],
                cwd=ui_file.parent,
                capture_output=True,
                text=True
            )
            print(f"Subprocess return code: {result.returncode}")
            if result.stdout:
                print(f"Stdout: {result.stdout}")
            if result.stderr:
                print(f"Stderr: {result.stderr}")
            # Check if the subprocess succeeded and the file was created
            if result.returncode == 0 and ui_file_py.exists():
                print(f"Successfully generated {ui_file_py}")
                adjust_resource_imports(ui_file_py, ui_file_py)
            else:
                print(f"Error: Failed to generate {ui_file_py} from {ui_file}. Skipping adjustment.")
        else:
            print(f"Skipping {ui_file} as {ui_file_py} is up to date")


def main():
    print("main() called in build_ui.py")
    build_ui()
    generate_resources()
    # Build QSS for both themes
    process_qss()
    build_all_theme_css()