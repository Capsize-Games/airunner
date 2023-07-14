import sys
import os
sys.path.append('Z:\\app\\airunner')
version = open('Z:\\app\\VERSION').read().strip()
print(f"Deploying {version} to itch.io")
os.system(f"C:\\Python310\\Scripts\\butler.exe push Z:\\app\\dist\\airunner capsizegames/ai-runner:windows-rc --userversion {version}")
