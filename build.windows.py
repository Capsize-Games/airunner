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



def get_latest_version_tag(repo):
    url = f'https://api.github.com/repos/{repo}/releases/latest'
    with urllib.request.urlopen(url) as response:
        data = response.read().decode('utf-8')
    data = json.loads(data)
    tag_name = data["tag_name"]
    # strip the v
    if tag_name.startswith("v"):
        tag_name = tag_name[1:]
    return tag_name



def clone(repo):
    # clone repo into /app
    os.system(f'Z:\\cmd\\git.exe clone https://github.com/{repo}.git /app/{repo.split("/")[1]}')


# remove diffusers
os.system("C:\\Python310\\python.exe -m pip uninstall diffusers -y")
# install repos
install_latest("w4ffl35/diffusers")
install_latest("w4ffl35/transformers")
install_latest("Capsize-Games/aihandler", branch="develop-windows")
clone("Capsize-Games/airunner")
version = get_latest_version_tag("Capsize-Games/airunner")
os.system("C:\\Python310\\python.exe -m pip install bitsandbytes-cuda102")