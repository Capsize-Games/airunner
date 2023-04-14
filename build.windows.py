import os
import urllib.request
import json


def install_latest(repo, branch="master"):
    # Clone the repository
    os.system(f'Z:\\cmd\\git.exe clone https://github.com/{repo}.git')

    # Change directory to the cloned repository
    repo_name = repo.split('/')[-1]
    os.chdir(repo_name)

    # Fetch all the tags in the repository
    os.system('Z:\\cmd\\git.exe fetch --tags')

    # Get the latest tag on the specified branch or on all branches
    os.system(f'Z:\\cmd\\git.exe checkout {branch}')
    tags = os.popen('Z:\\cmd\\git.exe tag --merged').read().splitlines()
    latest_tag = None
    for tag in tags:
        if branch is None or tag.startswith(f'v{branch}-'):
            if latest_tag is None or tag > latest_tag:
                latest_tag = tag
    if latest_tag:
        latest_tag = latest_tag.strip()
        # Switch to the latest tag
        os.system(f'Z:\\cmd\\git.exe checkout {latest_tag}')

    # Install the package
    os.system(f'C:\\Python310\\python.exe -m pip install .')


def clone(repo):
    # clone repo into /app
    os.system(f'Z:\\cmd\\git.exe clone https://github.com/{repo}.git /app/{repo.split("/")[1]}')


# remove diffusers
os.system("C:\\Python310\\python.exe -m pip uninstall diffusers -y")
# install repos
install_latest("Capsize-Games/aihandler", branch="develop-windows")
os.system("C:\\Python310\\python.exe -m pip install https://github.com/w4ffl35/diffusers/archive/refs/tags/v0.14.0.ckpt_fix.tar.gz")
os.system("C:\\Python310\\python.exe -m pip install https://github.com/w4ffl35/transformers/archive/refs/tags/tensor_fix-v1.0.2.tar.gz")
os.system("C:\\Python310\\python.exe -m pip install bitsandbytes-cuda102")