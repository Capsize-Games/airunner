import os
import urllib.request
import json


os.chdir("/app/airunner")
os.system("git pull")
os.system("python3 -m build")
os.system("cd dist")
os.system("WHL_FILE=$(ls airunner-*.whl)")
os.system("python3 -m pip install build $WHL_FILE")
os.system("python3 -m pip install .")
