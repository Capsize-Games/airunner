#!/bin/bash
set -e
set -x

# Try to find Python 3.13.3 - check various possible locations
PYTHON_CMD=""

# Check common locations for Python 3.13.3
if [ -x "/usr/local/bin/python3.13" ]; then
    PYTHON_CMD="/usr/local/bin/python3.13"
    echo "Found Python at /usr/local/bin/python3.13"
elif [ -x "/usr/local/bin/python" ]; then
    PYTHON_CMD="/usr/local/bin/python"
    echo "Found Python at /usr/local/bin/python"
elif [ -x "/usr/bin/python3.13" ]; then
    PYTHON_CMD="/usr/bin/python3.13"
    echo "Found Python at /usr/bin/python3.13"
elif command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
    echo "Using python3 from PATH"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
    echo "Using python from PATH"
else
    echo "WARNING: Could not find Python 3.13.3. Will attempt to continue anyway."
    PYTHON_CMD="python3"  # Default to python3 and hope for the best
fi

# Check Python version
echo "===== Python Version Check ====="
if [ -n "$PYTHON_CMD" ]; then
    $PYTHON_CMD --version || echo "Failed to get Python version"
    
    # Find pip corresponding to Python
    if [ -x "/usr/local/bin/pip3.13" ]; then
        PIP_CMD="/usr/local/bin/pip3.13"
    elif [ -x "/usr/local/bin/pip" ]; then
        PIP_CMD="/usr/local/bin/pip"
    elif command -v pip3 &>/dev/null; then
        PIP_CMD="pip3"
    else
        PIP_CMD="pip"
    fi
    
    $PIP_CMD --version || echo "Failed to get pip version"
else
    echo "No Python executable found to check version."
fi

# Set PYTHONUSERBASE to ensure pip installs packages into the correct directory
export PYTHONUSERBASE=/home/appuser/.local/share/airunner/python
export PATH=/usr/local/bin:/home/appuser/.local/share/airunner/python/bin:/home/appuser/.local/bin:$PATH
export PATH=$PYTHONUSERBASE/bin:$PATH

# Remove PIP_USER to avoid conflicts with --prefix
unset PIP_USER

# Ensure pip uses the correct cache directory
export PIP_CACHE_DIR=$AIRUNNER_HOME_DIR/.cache/pip

echo "PATH set to $PATH"
echo "PIP_CACHE_DIR set to $PIP_CACHE_DIR"

# Ensure the directory structure exists
mkdir -p $PYTHONUSERBASE/{bin,lib,share}

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

# Install basic packages
$PIP_CMD install --no-cache-dir pip setuptools wheel --upgrade
$PIP_CMD install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# Install python packages at runtime
$PIP_CMD install --no-cache-dir -e .[all_dev] \
 -U langchain-community
$PIP_CMD install -U timm
$PYTHON_CMD -c "import nltk; nltk.download('punkt')"
rm -rf .cache/pip

# Handle interactive sessions
if [ "$#" -eq 0 ]; then
  echo "No command provided. Starting an interactive shell..."
  exec bash
elif [ "$1" == "airunner" ]; then
  echo "Running airunner in development mode..."
  shift # Remove 'airunner' from the arguments
  cd /app && exec $PYTHON_CMD src/airunner/main.py "$@"
else
  echo "Executing command: $@"
  exec "$@"
fi