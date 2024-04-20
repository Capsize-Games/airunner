import subprocess
from pathlib import Path


def generate_resources():
    print("Generating resources.py")
    subprocess.run(
        [
            "pyside6-rcc",
            "-o",
            "src/airunner/resources_light_rc.py",
            "src/airunner/resources_light.qrc",
        ],
        cwd=str(Path(__file__).parent.parent),
    )
    subprocess.run(
        [
            "pyside6-rcc",
            "-o",
            "src/airunner/resources_dark_rc.py",
            "src/airunner/resources_dark.qrc",
        ],
        cwd=str(Path(__file__).parent.parent),
    )


if __name__ == "__main__":
    generate_resources()
