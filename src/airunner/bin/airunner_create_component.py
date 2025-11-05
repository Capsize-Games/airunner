"""
CLI tool to scaffold a new component directory in src/airunner/components/.
Usage: airunner-create-component <component_name>
"""

import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        print("Usage: airunner-create-component <component_name>")
        sys.exit(1)
    name = sys.argv[1]
    if not name.isidentifier():
        print(f"Invalid component name: {name}")
        sys.exit(1)
    base = (
        Path(__file__).resolve().parent.parent.parent
        / "airunner"
        / "components"
    )
    dst = base / name
    if dst.exists():
        print(f"Component '{name}' already exists.")
        sys.exit(1)
    # Create directory structure
    (dst / "gui" / "static" / "css").mkdir(parents=True, exist_ok=True)
    (dst / "gui" / "static" / "html").mkdir(parents=True, exist_ok=True)
    (dst / "gui" / "static" / "js").mkdir(parents=True, exist_ok=True)
    (dst / "gui" / "widgets" / "templates").mkdir(parents=True, exist_ok=True)
    # Create files
    (dst / "__init__.py").touch()
    (dst / "gui" / "__init__.py").touch()
    (dst / "gui" / "widgets" / f"{name}_widget.py").touch()
    (dst / "gui" / "widgets" / "templates" / f"{name}.ui").touch()
    # README
    (dst / "README.md").write_text(
        f"# {name.capitalize()} Component\n\nDescribe the {name} component here.\n"
    )
    print(f"Component '{name}' created at {dst}")


if __name__ == "__main__":
    main()
