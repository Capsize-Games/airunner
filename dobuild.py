import os
import urllib.request
import json


def install_latest(repo, deps=True):
    url = f'https://api.github.com/repos/{repo}/releases/latest'
    with urllib.request.urlopen(url) as response:
        data = response.read().decode('utf-8')
    data = json.loads(data)
    tag_name = data["tag_name"]
    tar_url = f'https://github.com/{repo}/archive/{tag_name}.tar.gz'
    install = f'python3 -m pip install {tar_url}'
    if not deps:
        install +=" --no-deps"
    os.system(install)


def clone(repo):
    # clone repo into /app
    os.system(f'git clone https://github.com/{repo}.git /app/{repo.split("/")[1]}')


# remove diffusers
os.system("python3 -m pip uninstall diffusers")
# install repos
install_latest("Capsize-Games/aihandler")
install_latest("w4ffl35/diffusers", False)
install_latest("w4ffl35/transformers", False)
# change into /app/airunner and update
os.chdir("/app/airunner")
os.system("git checkout master")
os.system("git pull")
os.system("pip install -e . --no-deps")
os.system("python3 -m pip uninstall nvidia-cublas-cu11")
os.system("python3 -m pip install bitsandbytes-cuda102")
