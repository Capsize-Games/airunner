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
    var_block_pattern = r"/\*\s*VARIABLES\s*\*/(.+?)/\*\s*END_VARIABLES\s*\*/"
    var_pattern = r"@[\w-]+"

    def get_variable_value(var_name, contents):
        var_pattern = re.escape(var_name) + r"\s*:\s*([^;]+);"
        match = re.search(var_pattern, contents)
        if match:
            return match.group(1).strip()
        else:
            return var_name

    def process_file(file_path, output_file, variables):
        with open(file_path, "r") as f:
            contents = f.read()
        # Replace any include statements with the contents of the included file
        contents = re.sub(
            r'\$include\("(.+)"\)',
            lambda m: process_file(m.group(1), output_file, variables),
            contents,
        )
        # Replace any variables with their values
        for match in re.finditer(var_pattern, contents):
            var_name = match.group(0)
            if var_name in variables:
                contents = contents.replace(var_name, variables[var_name])
        output_file.write(contents)

    def process_manifest(manifest_path, output_dir):
        with open(manifest_path, "r") as f:
            contents = f.read()
        output_path = os.path.join(output_dir, "styles.qss")
        variables = {}
        qss_files = []
        # Support ../master.qss as a manifest entry
        for filename in contents.splitlines():
            file_path = os.path.abspath(
                os.path.join(os.path.dirname(manifest_path), filename.strip())
            )
            # If manifest entry is ../master.qss and file exists, use it
            if filename.strip() == "../master.qss" and os.path.isfile(
                file_path
            ):
                qss_files.append(file_path)
                continue
            if os.path.isfile(file_path) and filename.endswith(".qss"):
                with open(file_path, "r") as input_file:
                    input_contents = input_file.read()
                var_block_match = re.search(
                    var_block_pattern, input_contents, flags=re.DOTALL
                )
                if var_block_match:
                    var_block_contents = var_block_match.group(1)
                    for match in re.finditer(var_pattern, var_block_contents):
                        var_name = match.group(0)
                        if var_name not in variables:
                            variables[var_name] = get_variable_value(
                                var_name, var_block_contents
                            )
                # Only add to qss_files if it's not just a variable file
                if (
                    not var_block_match
                    or input_contents.replace(
                        var_block_match.group(0), ""
                    ).strip()
                ):
                    qss_files.append(file_path)
        with open(output_path, "w") as output_file:
            for file_path in qss_files:
                process_file(file_path, output_file, variables)
        # Remove variable blocks from the output file
        with open(output_path, "r") as f:
            contents = f.read()
        contents = re.sub(var_block_pattern, "", contents, flags=re.DOTALL)
        with open(output_path, "w") as f:
            f.write(contents)

    def process_directory(directory_path):
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            if os.path.isdir(file_path):
                process_directory(file_path)
            elif os.path.isfile(file_path) and filename == "manifest.txt":
                output_dir = os.path.dirname(file_path)
                process_manifest(file_path, output_dir)

    # Process all manifest files in the styles directory and its subdirectories
    script_dir = os.path.dirname(os.path.abspath(__file__))
    styles_dir = os.path.abspath(
        os.path.join(script_dir, "..", "gui", "styles")
    )
    process_directory(styles_dir)


def qss_var_to_css_var(qss_var):
    # Converts @primary-color to --primary-color
    return qss_var.replace("@", "--")


def parse_qss_variables(qss_path):
    # Extracts variables from a QSS variable file
    with open(qss_path, "r") as f:
        content = f.read()
    var_block = re.search(
        r"/\*\s*VARIABLES\s*\*/(.+?)/\*\s*END_VARIABLES\s*\*/",
        content,
        re.DOTALL,
    )
    if not var_block:
        return {}
    var_lines = var_block.group(1).splitlines()
    variables = {}
    for line in var_lines:
        line = line.strip()
        if line.startswith("@") and ":" in line:
            name, value = line.split(":", 1)
            # Always use the value from the current file, do not override if already present
            variables[qss_var_to_css_var(name.strip())] = value.strip(" ;")
    return variables


def write_css_variables(variables, out_path):
    with open(out_path, "w") as f:
        f.write(
            f"/* {os.path.basename(out_path)} - auto-generated from QSS */\n:root {{\n"
        )
        for k, v in variables.items():
            f.write(f"    {k}: {v};\n")
        f.write("}\n")


def build_all_theme_css():
    styles_dir = Path(__file__).parent.parent / "gui" / "styles"
    # Output directories for both home_stage and conversations
    output_targets = [
        Path(__file__).parent.parent
        / "components"
        / "home_stage"
        / "gui"
        / "static"
        / "css",
        Path(__file__).parent.parent
        / "components"
        / "chat"
        / "gui"
        / "static"
        / "css",
    ]
    print(f"[DEBUG] Output targets: {output_targets}")
    for theme_dir in styles_dir.iterdir():
        if not theme_dir.is_dir():
            continue
        var_file = theme_dir / "variables.qss"
        if var_file.exists():
            theme_name = theme_dir.name.replace("_theme", "")
            variables = parse_qss_variables(var_file)
            for out_dir in output_targets:
                out_dir.mkdir(parents=True, exist_ok=True)
                out_var = out_dir / f"variables-{theme_name}.css"
                print(f"[DEBUG] Writing variables to {out_var}")
                write_css_variables(variables, out_var)
                # Optionally, generate a theme css file (placeholder)
                out_theme = out_dir / f"theme-{theme_name}.css"
                print(f"[DEBUG] Writing theme to {out_theme}")
                with open(out_theme, "w") as f:
                    f.write(
                        f"/* theme-{theme_name}.css - auto-generated placeholder */\n"
                    )
                    f.write(
                        "body {\n    background: var(--dark-color);\n    color: var(--light-color);\n}\n"
                    )
                    f.write(
                        ".grid-item {\n    color: var(--light-color);\n    background: var(--dark-color);\n}\n"
                    )
                    f.write(
                        "#home-top, #home-bottom {\n    background: var(--dark-color);\n}\n"
                    )
                    f.write(
                        ".font-color, .text, .content, .main-content, .sidebar, .header, .footer {\n    color: var(--light-color);\n}\n"
                    )


if __name__ == "__main__":
    build_all_theme_css()


class SignalEmitter(QObject):
    file_changed = Signal()
