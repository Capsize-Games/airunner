import os


def install_latest(repo, branch="master"):
    # Clone the repository
    os.chdir('Z:\\')
    os.system(f'C:\\cmd\\git.exe clone https://github.com/{repo}.git')

    # Change directory to the cloned repository
    repo_name = repo.split('/')[-1]
    os.chdir(repo_name)

    # Fetch all the tags in the repository
    os.system('C:\\cmd\\git.exe fetch --tags')

    # Get the latest tag on the specified branch or on all branches
    os.system(f'C:\\cmd\\git.exe checkout {branch}')
    tags = os.popen('C:\\cmd\\git.exe tag --merged').read().splitlines()
    latest_tag = None
    for tag in tags:
        if branch is None or tag.startswith(f'v{branch}-'):
            if latest_tag is None or tag > latest_tag:
                latest_tag = tag
    if latest_tag:
        latest_tag = latest_tag.strip()
        # Switch to the latest tag
        os.system(f'C:\\cmd\\git.exe checkout {latest_tag}')

    # Install the package
    os.system(f'C:\\Python310\\python.exe -m pip install .')


def clone(repo):
    # clone repo into /app
    os.system(f'C:\\cmd\\git.exe clone https://github.com/{repo}.git /app/{repo.split("/")[1]}')

clone("Capsize-Games/airunner")
os.chdir("Z:\\app\\airunner")
os.system("C:\\cmd\\git.exe checkout master")
os.system("C:\\cmd\\git.exe pull")
os.system("C:\\Python310\\python.exe -m pip install .")
os.system("C:\\Python310\\python.exe -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 --upgrade")
