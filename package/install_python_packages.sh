cd /app

export PATH=/home/appuser/.local/bin:$PATH

# Check if torch is installed before continuing
if python3 -c "import torch" 2>/dev/null; then
  echo "Torch is already installed."
else
  echo "Torch is not installed. Installing torch, torchvision, and torchaudio..."
  pip install -v torch torchvision torchaudio
fi

# # Check if AIRUNNER_ENABLE_OPEN_VOICE==1
if [ "$AIRUNNER_ENABLE_OPEN_VOICE" == "1" ]; then
  if python3 -c "import openvoice" 2>/dev/null; then
    echo "OpenVoice is already installed."
  else
    echo "OpenVoice is not installed. Installing OpenVoice..."
    # Check if OpenVoice exists
    if [ ! -d "OpenVoice" ]; then
      git clone https://github.com/myshell-ai/OpenVoice.git
    fi
    cd OpenVoice
    pip install -v .
    cd ..
    rm -rf OpenVoice
  fi

  # Check if MeloTTS exists
  if python3 -c "import melo" 2>/dev/null; then
    echo "MeloTTS is already installed."
  else
    echo "MeloTTS is not installed. Installing MeloTTS..."
    if [ ! -d "MeloTTS" ]; then
      git clone https://github.com/myshell-ai/MeloTTS.git
    fi
    cd MeloTTS
    git checkout v0.1.2
    pip install -v .
    cd ..
    rm -rf MeloTTS
  fi

  echo "Downloading unidic..."
  python3 -m unidic download
  echo "Unidic download complete."
  exit 0
else
  echo "Uninstalling OpenVoice and MeloTTS..."
  pip uninstall myshell-openvoice -y
  pip uninstall melotts -y
fi

# Check if airunner is installed and which version, if not installed or outdated, install the latest version
if python3 -c "import airunner" 2>/dev/null; then
  echo "Airunner is already installed."
  INSTALLED_VERSION=$(pip show airunner | grep Version | cut -d ' ' -f 2)
  REQUIRED_VERSION=$(grep 'version=' /app/setup.py | sed -n "s/.*version=['\"]\([^'\"]*\)['\"].*/\1/p")
  echo "Installed version: $INSTALLED_VERSION"
  echo "Required version: $REQUIRED_VERSION"
  if [ "$INSTALLED_VERSION" != "$REQUIRED_VERSION" ]; then
    echo "Airunner version $INSTALLED_VERSION is installed, but version $REQUIRED_VERSION is required."
    pip install -v -e .[all_dev]
    pip install -v -U langchain-community
    pip install -v -U mediapipe
    pip install -v -U timm
  else
    echo "Airunner version $INSTALLED_VERSION is already installed."
  fi
else
  echo "Airunner is not installed. Installing the latest version..."
  pip install -v -e .[all_dev]
  pip install -v -U langchain-community
  pip install -v -U mediapipe
  pip install -v -U timm
fi

if [ -f "/home/appuser/nltk_data/tokenizers/punkt/english.pickle" ]; then
  echo "NLTK punkt tokenizer is already installed."
else
  echo "NLTK punkt tokenizer is not installed. Installing..."
  python3 -c "import nltk; nltk.download('punkt')"
fi

if [ -f "/home/appuser/.local/share/airunner/.cache/huggingface/accelerate/default_config.yaml" ]; then
  echo "Accelerate config file already exists."
else
  echo "Accelerate config file does not exist. Creating..."
  python3 -c "from accelerate.utils import write_basic_config; write_basic_config(mixed_precision='fp16')"
fi