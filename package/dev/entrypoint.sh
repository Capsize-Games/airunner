#!/bin/bash
set -e
set -x

# Set up Wayland environment variables
export QT_QPA_PLATFORM=wayland
export QT_WAYLAND_DISABLE_WINDOWDECORATION=1
export QT_QPA_PLATFORMTHEME=gtk3
export GDK_BACKEND=wayland
export XDG_SESSION_TYPE=wayland

echo "===== Wayland Setup Information ====="
echo "User: $(whoami)"
echo "XDG_SESSION_TYPE: $XDG_SESSION_TYPE"
echo "QT_QPA_PLATFORM: $QT_QPA_PLATFORM"
echo "GDK_BACKEND: $GDK_BACKEND"

pip install --no-cache-dir pip setuptools wheel --upgrade
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install python packages at runtime
pip install --no-cache-dir -e .[nvidia,gui,linux,dev,art,llm,llm_weather,tts] \
 -U langchain-community
pip install -U timm
python3 -c "import nltk; nltk.download('punkt')"
rm -rf .cache/pip

# Modify the script to handle interactive sessions properly
if [ "$#" -eq 0 ]; then
  echo "No command provided. Starting an interactive shell..."
  exec bash
else
  echo "Executing command: $@"
  exec "$@"
fi