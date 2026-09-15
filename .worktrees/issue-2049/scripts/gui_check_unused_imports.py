import os
import sys
from pyflakes.api import checkPath
from pyflakes.reporter import Reporter

class CustomReporter(Reporter):
    """Custom reporter to filter and format pyflakes output."""
    def __init__(self):
        # Pass standard output and error streams to the base constructor
        super().__init__(sys.stdout, sys.stderr)

    def flake(self, message):
        # Filter for unused import warnings
        if "imported but unused" in str(message):
            print(f"{message.filename}:{message.lineno}: {message.message % message.message_args}")

def scan_with_pyflakes(target_directory: str):
    if not os.path.exists(target_directory):
        print(f"Error: The directory '{target_directory}' does not exist.")
        return

    reporter = CustomReporter()
    excluded_suffixes = ('_ui.py', '_rc.py')
    
    for root, _, files in os.walk(target_directory):
        for file in files:
            if file.endswith('.py'):
                if file.endswith(excluded_suffixes):
                    continue
                
                full_path = os.path.join(root, file)
                checkPath(full_path, reporter=reporter)

if __name__ == "__main__":
    # Target the src/airunner directory relative to the current working directory
    target_path = os.path.join("src", "airunner")
    scan_with_pyflakes(target_path)