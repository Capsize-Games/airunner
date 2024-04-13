import os


def get_venv_python_executable():
    """
    Gets the python executable from the venv.
    :return: executable path
    """
    venv_python_executable = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "venv",
        "../../bin",
        "python",
    )
    if not os.path.exists(venv_python_executable):
        venv_python_executable = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "venv",
            "Scripts",
            "python.exe",
        )
    if not os.path.exists(venv_python_executable):
        venv_python_executable = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "venv",
            "../../bin",
            "python3",
        )
    if not os.path.exists(venv_python_executable):
        venv_python_executable = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "venv",
            "Scripts",
            "python3.exe",
        )
    if not os.path.exists(venv_python_executable):
        raise Exception("Could not find python executable in venv")
    return venv_python_executable
