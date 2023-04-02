import os
import urllib.request
import json


def install_latest(repo):
    url = f'https://api.github.com/repos/{repo}/releases/latest'
    with urllib.request.urlopen(url) as response:
        data = response.read().decode('utf-8')
    data = json.loads(data)
    tag_name = data["tag_name"]
    tar_url = f'https://github.com/{repo}/archive/{tag_name}.tar.gz'
    os.system(f'python3 -m pip install {tar_url}')


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
    os.system(f'git clone https://github.com/{repo}.git /app/{repo.split("/")[1]}')


# install repos
install_latest("w4ffl35/diffusers")
install_latest("w4ffl35/transformers")
install_latest("Capsize-Games/aihandler")
clone("Capsize-Games/airunner")
version = get_latest_version_tag("Capsize-Games/airunner")
os.system("python3 -m pip uninstall nvidia-cublas-cu11 -y")
os.system("python3 -m pip install bitsandbytes-cuda102 -y")