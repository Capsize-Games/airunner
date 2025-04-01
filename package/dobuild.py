import os
import sys
import subprocess
import urllib.request
import json

def run_command(command, description=None):
    """Run a command and print its description and result."""
    if description:
        print(f"{description}...")
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error executing command: {command}")
        print(f"Error output: {result.stderr}")
        sys.exit(result.returncode)
    
    return result.stdout.strip()

def main():
    """Main build process handler."""
    # Change to the airunner directory
    os.chdir("/app/airunner")
    
    # Pull the latest code
    run_command("git pull", "Pulling latest code")
    
    # Build the package
    run_command("python3 -m build", "Building Python package")
    
    # Find the wheel file
    wheel_files_output = run_command("find dist -name 'airunner-*.whl'", "Finding wheel file")
    wheel_files = wheel_files_output.splitlines()
    if len(wheel_files) == 0:
        print("Error: No wheel file found in dist directory")
        sys.exit(1)
    elif len(wheel_files) > 1:
        print("Error: Multiple wheel files found in dist directory")
        for wf in wheel_files:
            print(f"Found wheel file: {wf}")
        sys.exit(1)
    
    wheel_file = wheel_files[0]
    print(f"Found wheel file: {wheel_file}")
    
    # Install the package
    run_command(f"python3 -m pip install --force-reinstall {wheel_file}", "Installing wheel package")
    run_command("python3 -m pip install .", "Installing package in development mode")
    
    print("Build setup completed successfully")

if __name__ == "__main__":
    main()
