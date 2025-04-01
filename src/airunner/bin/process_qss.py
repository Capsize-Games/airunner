import os
import re
import subprocess
from pathlib import Path

from PySide6.QtCore import QObject, Signal


def build_ui(path):
    """Build the UI for the application."""
    # recursively iterate over directories in path
    print("Building UI at path", path)
    ui_files = Path(__file__).parent.parent.joinpath(path).glob("**/*.ui")
    for ui_file in ui_files:

        print("Generating", ui_file)
        ui_file = str(ui_file)
        ui_file_dir = os.path.dirname(ui_file)
        ui_file_py = ui_file.replace(".ui", "_ui.py")
        print(f"Generating {ui_file_py}")
        subprocess.run(
            [
                "pyuic6",
                "-o",
                ui_file_py,
                ui_file,
            ],
            cwd=ui_file_dir,
            )


def generate_resources():
    print("Generating resources.py")
    here = os.path.dirname(os.path.abspath(__file__))
    subprocess.run(
        [
            "pyside6-rcc",
            "-o",
            os.path.join(here, "..", "gui", "resources", "feather_rc.py"),
            os.path.join(here, "..", "gui", "resources", "feather.qrc"),
        ],
        cwd=str(Path(__file__).parent.parent),
    )


def build_templates(path):
    build_ui(path)
    generate_resources()


def process_qss(_path=None):
    # Define the regular expression pattern for variables
    var_block_pattern = r'/\*\s*VARIABLES\s*\*/(.+?)/\*\s*END_VARIABLES\s*\*/'
    var_pattern = r'@[\w-]+'

    def process_file(file_path, output_file, variables):
        """Process a single QSS file and write the output to the output file."""
        with open(file_path, 'r') as f:
            contents = f.read()

        # Replace any include statements with the contents of the included file
        contents = re.sub(r'\$include\("(.+)"\)', lambda m: process_file(m.group(1), output_file, variables), contents)

        # Replace any variables with their values
        for match in re.finditer(var_pattern, contents):
            var_name = match.group(0)
            if var_name in variables:
                contents = contents.replace(var_name, variables[var_name])

        # Write the processed contents to the output file
        output_file.write(contents)

    def process_manifest(manifest_path, output_dir):
        """Process a single manifest file and write the output to the output file."""
        with open(manifest_path, 'r') as f:
            contents = f.read()

        # Process each QSS file listed in the manifest
        output_path = os.path.join(output_dir, 'styles.qss')
        print(output_path)
        variables = {}
        with open(output_path, 'w') as output_file:
            for filename in contents.splitlines():
                file_path = os.path.join(os.path.dirname(manifest_path), filename.strip())
                if os.path.isfile(file_path) and filename.endswith('.qss'):
                    with open(file_path, 'r') as input_file:
                        input_contents = input_file.read()
                    var_block_match = re.search(var_block_pattern, input_contents, flags=re.DOTALL)
                    if var_block_match:
                        var_block_contents = var_block_match.group(1)
                        for match in re.finditer(var_pattern, var_block_contents):
                            var_name = match.group(0)
                            if var_name not in variables:
                                variables[var_name] = get_variable_value(var_name, var_block_contents)
                    process_file(file_path, output_file, variables)
        # Remove variable blocks from the output file
        with open(output_path, 'r') as f:
            contents = f.read()
        contents = re.sub(var_block_pattern, '', contents, flags=re.DOTALL)
        with open(output_path, 'w') as f:
            f.write(contents)

    def get_variable_value(var_name, contents):
        """Get the value of a variable by searching for its definition in the contents."""
        var_pattern = re.escape(var_name) + r'\s*:\s*([^;]+);'
        match = re.search(var_pattern, contents)
        if match:
            return match.group(1).strip()
        else:
            return var_name

    def process_directory(directory_path):
        """Recursively process all manifest files in a directory and its subdirectories."""
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            if os.path.isdir(file_path):
                process_directory(file_path)
            elif os.path.isfile(file_path) and filename == 'manifest.txt':
                output_dir = os.path.dirname(file_path)
                process_manifest(file_path, output_dir)

    # Process all manifest files in the styles directory and its subdirectories
    process_directory(os.path.join(os.getcwd(), 'styles'))


class SignalEmitter(QObject):
    file_changed = Signal()
