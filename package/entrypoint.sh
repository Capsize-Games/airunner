#!/bin/bash
set -e
set -x

# Set PYTHONUSERBASE to ensure pip installs packages into the correct directory
export PYTHONUSERBASE=/home/appuser/.local/share/airunner/python
echo "PYTHONUSERBASE set to $PYTHONUSERBASE"

# Ensure the directory structure exists (but don't try to chmod mounted volumes)
mkdir -p $PYTHONUSERBASE/{bin,lib,share}

# Diagnostic information
echo "User: $(whoami)"
echo "PYTHONUSERBASE: $PYTHONUSERBASE"
echo "PIP_USER: $PIP_USER"
pip list

# Diagnostic information for X11 setup
echo "===== X11 Setup Diagnostic Information ====="
echo "DISPLAY: $DISPLAY"
echo "XAUTHORITY: $XAUTHORITY"
echo "Checking X11 socket directory:"
ls -la /tmp/.X11-unix/ || echo "X11 socket directory not found"
echo "Checking if .Xauthority exists:"
ls -la $XAUTHORITY 2>/dev/null || echo ".Xauthority not found"

# Check if we can connect to the X server
echo "Testing X connection with xdpyinfo:"
if xdpyinfo >/dev/null 2>&1; then
  echo "X connection successful!"
else
  echo "X connection failed"
fi

# Use --prefix to explicitly specify installation location
pip install --no-cache-dir --prefix $PYTHONUSERBASE pip setuptools wheel --upgrade
pip install --no-cache-dir --prefix $PYTHONUSERBASE torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Check if AIRUNNER_ENABLE_OPEN_VOICE==1
if [ "$AIRUNNER_ENABLE_OPEN_VOICE" == "1" ]; then
  echo "Installing OpenVoice and MeloTTS..."
  # Check if OpenVoice exists
  if [ ! -d "OpenVoice" ]; then
    git clone https://github.com/myshell-ai/OpenVoice.git
  fi
  cd OpenVoice
  pip install --no-cache-dir --prefix $PYTHONUSERBASE .
  cd ..
  rm -rf OpenVoice

  # Check if MeloTTS exists
  if [ ! -d "MeloTTS" ]; then
    git clone https://github.com/myshell-ai/MeloTTS.git
  fi
  cd MeloTTS
  git checkout v0.1.2
  pip install --no-cache-dir --prefix $PYTHONUSERBASE .
  cd ..
  rm -rf MeloTTS

  echo "Downloading unidic..."
  python3 -m unidic download
  echo "Unidic download complete."
  exit 0
else
  echo "Uninstalling OpenVoice and MeloTTS..."
  pip uninstall myshell-openvoice -y
  pip uninstall melotts -y
fi

# Install python packages at runtime
pip install --no-cache-dir --prefix $PYTHONUSERBASE -e .[nvidia,gui,linux,dev,art,llm,llm_weather,tts] \
 -U langchain-community \
 -U mediapipe
pip install --no-cache-dir --prefix $PYTHONUSERBASE -U timm
python3 -c "from accelerate.utils import write_basic_config; write_basic_config(mixed_precision='fp16')"
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