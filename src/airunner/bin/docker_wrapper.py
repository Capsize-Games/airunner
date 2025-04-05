import os
import sys
import subprocess


def main():
    # Get the path to the docker.sh script
    script_path = os.path.join(os.path.dirname(__file__), "docker.sh")

    # Ensure the script is executable
    if not os.access(script_path, os.X_OK):
        raise PermissionError(f"The script {script_path} is not executable.")

    # Pass all arguments to the shell script
    try:
        subprocess.check_call(["/bin/bash", script_path] + sys.argv[1:])
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()
