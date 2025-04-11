# Set PIP_CACHE_DIR to ensure pip uses a persistent cache
export PIP_CACHE_DIR=/home/appuser/.local/share/airunner/.cache/pip
echo "PIP_CACHE_DIR set to $PIP_CACHE_DIR"

# Check if torch is installed before continuing
if python3 -c "import torch" 2>/dev/null; then
  echo "Torch is already installed."
else
  echo "Torch is not installed. Installing torch, torchvision, and torchaudio..."
  pip install -v --cache-dir $PIP_CACHE_DIR --prefix $PYTHONUSERBASE torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
fi

# Check if AIRUNNER_ENABLE_OPEN_VOICE==1
if [ "$AIRUNNER_ENABLE_OPEN_VOICE" == "1" ]; then
  echo "Installing OpenVoice and MeloTTS..."
  # Check if OpenVoice exists
  if [ ! -d "OpenVoice" ]; then
    git clone https://github.com/myshell-ai/OpenVoice.git
  fi
  cd OpenVoice
  pip install -v --cache-dir $PIP_CACHE_DIR --prefix $PYTHONUSERBASE .
  cd ..
  rm -rf OpenVoice

  # Check if MeloTTS exists
  if [ ! -d "MeloTTS" ]; then
    git clone https://github.com/myshell-ai/MeloTTS.git
  fi
  cd MeloTTS
  git checkout v0.1.2
  pip install -v --cache-dir $PIP_CACHE_DIR --prefix $PYTHONUSERBASE .
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

# Check if airunner is installed and which version, if not installed or outdated, install the latest version
if python3 -c "import airunner" 2>/dev/null; then
  echo "Airunner is already installed."
  INSTALLED_VERSION=$(python3 -c "import airunner; print(airunner.__version__)")
  REQUIRED_VERSION=$(grep 'version=' /app/setup.py | cut -d "'" -f 2)
  if [ "$INSTALLED_VERSION" != "$REQUIRED_VERSION" ]; then
    echo "Airunner version $INSTALLED_VERSION is installed, but version $REQUIRED_VERSION is required."
    pip install -v --cache-dir $PIP_CACHE_DIR --prefix $PYTHONUSERBASE -e .[all_dev] \
        -U langchain-community \
        -U mediapipe
    pip install -v --cache-dir $PIP_CACHE_DIR --prefix $PYTHONUSERBASE -U timm
  else
    echo "Airunner version $INSTALLED_VERSION is already installed."
  fi
else
  pip install -v --cache-dir $PIP_CACHE_DIR --prefix $PYTHONUSERBASE -e .[all_dev] \
      -U langchain-community \
      -U mediapipe
  pip install -v --cache-dir $PIP_CACHE_DIR --prefix $PYTHONUSERBASE -U timm
fi

python3 -c "import nltk; nltk.download('punkt')"
python3 -c "from accelerate.utils import write_basic_config; write_basic_config(mixed_precision='fp16')"