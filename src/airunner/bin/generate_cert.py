import os
import subprocess


def main():
    script_path = os.path.join(os.path.dirname(__file__), "generate_cert.sh")
    subprocess.run(["bash", script_path], check=True)
