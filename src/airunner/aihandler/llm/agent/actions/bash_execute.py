import subprocess


def bash_execute(command: str) -> str:
    """
    Executes a bash command.

    This is an extremely unsafe operation and should be used with caution.
    This allows an LLM to execute arbitrary bash commands.
    By default this is disabled in the settings.

    :param command: str
    :return: str
    """
    try:
        command = command.split(" ")
        result = subprocess.check_output(command, shell=False)
        return result.decode("utf-8")
    except Exception as e:
        return str(e)
