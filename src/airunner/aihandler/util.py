import os
import io
import importlib
import zipfile
import requests
from aihandler.qtvar import ExtensionVar


def get_extensions_from_url(app):
    """
    extension CSV format:
        name,description,repo,version,reviewed,official
        LoRA,Adds support for LoRA,Capsize-Games/airunner-lora,1.0.0,true,true
    """
    url = "https://raw.githubusercontent.com/Capsize-Games/airunner-extensions/master/extensions.txt"
    available_extensions = []
    try:
        response = requests.get(url)
        if response.status_code == 200:
            extensions = response.text.splitlines()
            headers = extensions.pop(0)
            headers = headers.split(",")
            for extension in extensions:
                extension = extension.split(",")
                available_extensions.append(ExtensionVar(
                    app,
                    name=extension[headers.index("name")],
                    description=extension[headers.index("description")],
                    repo=extension[headers.index("repo")],
                    version=extension[headers.index("version")],
                    reviewed=extension[headers.index("reviewed")] == "true",
                    official=extension[headers.index("official")] == "true",
                    enabled=False
                ))
    except requests.exceptions.RequestException as e:
        print("Unable to load extensions")
    return available_extensions


def get_extensions_from_path(path):
    # check for extensions via subfolders under path
    available_extensions = []
    for f in os.listdir(path):
        if os.path.isdir(os.path.join(path, f)):
            # build extension details from {path}/setup.py
            try:
                # read setup.py from the extensions folder
                with open(os.path.join(path, f, "setup.py"), "r") as setup_file:
                    setup = setup_file.read()
                # get the name
                name = setup.split("name=")[1].split(",")[0].replace('"', "").replace("'", "")
                description = setup.split("description=")[1].split(",")[0].replace('"', "").replace("'", "")
                repo = setup.split("url=")[1].split(",")[0].replace('"', "").replace("'", "")
                version = setup.split("version=")[1].split(",")[0].replace('"', "").replace("'", "")
                reviewed = False
                official = False
                available_extensions.append(ExtensionVar(
                    None,
                    name=name,
                    description=description,
                    repo=repo,
                    version=version,
                    reviewed=reviewed,
                    official=official,
                    enabled=False
                ))
            except Exception as e:
                print(e)
                print(f"Unable to load extension {f}")
    return available_extensions



def download_extension(github_url, extension_path):
    """
    Downloads the extension from the repo and installs it into the extensions folder.
    :param repo:
    :param extension_path:
    :return:
    """
    try:
        # download the extension
        # download the latest release zip and extract it into the extensions folder
        # get the latest release
        repo_name = github_url.split("/")[-1]
        url = f"{github_url}/releases/latest"
        response = requests.get(url)
        if response.status_code == 200:
            # get the latest release zip
            latest_release_url = response.url
            # replace "tag" with "tags" in latest_release_url
            latest_release_url = latest_release_url.replace("/releases/tag/", "/archive/refs/tags/")
            response = requests.get(f"{latest_release_url}.zip")
            if response.status_code == 200:
                # extract the zip into the extensions folder
                with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                    # extract the contents of zip folder into extension_path + repo_name
                    zip_ref.extractall(extension_path)
                    # the above extracts into extension_path/<repo_name>-<version> but we want
                    # extension_path/<repo_name> so we need to move the contents of the extracted
                    # folder into extension_path/<repo_name>
                    # get the name of the extracted folder
                    # create repo_name if it doesn't exist
                    if not os.path.exists(os.path.join(extension_path, repo_name)):
                        os.mkdir(os.path.join(extension_path, repo_name))
                    extracted_folder = os.path.join(extension_path, zip_ref.namelist()[0])
                    # move the contents of the extracted folder into extension_path/<repo_name>
                    for f in os.listdir(extracted_folder):
                        os.rename(os.path.join(extracted_folder, f), os.path.join(extension_path, repo_name, f))
                    # delete the extracted folder
                    os.rmdir(extracted_folder)
                    # zip_ref.extractall(extension_path)
            else:
                print("Something went wrong", response.status_code)
    except requests.exceptions.RequestException as e:
        print("Unable to download extension")


def import_extension_class(extension_repo, extension_path, file_name, class_name):
    try:
        for f in os.listdir(extension_path):
            if os.path.isfile(os.path.join(extension_path, f)) and f == file_name:
                module_name = file_name[:-3]
                spec = importlib.util.spec_from_file_location(module_name, os.path.join(extension_path, file_name))
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return getattr(module, class_name)
    except FileNotFoundError as e:
        print(e)
        print("Unable to import extension class")
