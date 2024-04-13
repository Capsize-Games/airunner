import subprocess
import urllib.request
import sys

def install_library_from_url(url, install_dir):
    # Download the wheel file
    wheel_file = urllib.request.urlretrieve(url)[0]
    # Install the library
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--target", install_dir, wheel_file])

