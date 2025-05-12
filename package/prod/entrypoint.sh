#!/bin/bash
set -e
set -x

# Debugging: Check if pyenv directory exists
echo "=== PYENV DEBUGGING ==="
echo "Current user: $(whoami)"
echo "Checking if pyenv is installed..."

if [ ! -d "$HOME/.pyenv" ]; then
  echo "Pyenv directory NOT found at $HOME/.pyenv - Creating it"
  mkdir -p $HOME/.pyenv/bin
  git clone --depth=1 https://github.com/pyenv/pyenv.git $HOME/.pyenv
  cd $HOME/.pyenv && src/configure && make -C src
fi

if [ -d "$HOME/.pyenv/bin" ]; then
  echo "Pyenv bin directory exists at $HOME/.pyenv/bin"
  ls -la $HOME/.pyenv/bin
else
  echo "Pyenv bin directory NOT found at $HOME/.pyenv/bin - Creating it"
  mkdir -p $HOME/.pyenv/bin
  # Try to copy executables from libexec if they exist
  if [ -d "$HOME/.pyenv/libexec" ]; then
    echo "Found libexec directory, copying pyenv executable"
    cp $HOME/.pyenv/libexec/pyenv $HOME/.pyenv/bin/
    chmod +x $HOME/.pyenv/bin/pyenv
  fi
fi

# Set up pyenv environment regardless of .bashrc
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"

# Try to initialize pyenv if executable exists
if [ -f "$PYENV_ROOT/bin/pyenv" ]; then
  echo "pyenv executable found, initializing"
  eval "$($PYENV_ROOT/bin/pyenv init --path)" || echo "pyenv init --path failed"
  eval "$($PYENV_ROOT/bin/pyenv init -)" || echo "pyenv init - failed" 
elif [ -f "$PYENV_ROOT/libexec/pyenv" ]; then
  echo "Using libexec/pyenv instead"
  eval "$($PYENV_ROOT/libexec/pyenv init --path)" || echo "libexec pyenv init --path failed"
  eval "$($PYENV_ROOT/libexec/pyenv init -)" || echo "libexec pyenv init - failed"
else
  echo "No pyenv executable found in bin or libexec"
fi

echo "Current PATH: $PATH"

# Source bashrc to load other configurations
if [ -f /home/appuser/.bashrc ]; then
  echo "Loading configurations from .bashrc"
  . /home/appuser/.bashrc || echo "Error sourcing .bashrc"
  
  # Debugging: Check PATH after sourcing bashrc
  echo "PATH after sourcing bashrc: $PATH"
fi

# Final check for pyenv
if command -v pyenv >/dev/null 2>&1; then
  echo "pyenv is available in PATH"
  pyenv --version
  pyenv versions
else
  echo "pyenv is STILL NOT available in PATH after all attempts"
  # Last resort - try to find pyenv anywhere
  find $HOME/.pyenv -name pyenv -type f -executable | while read f; do
    echo "Found executable pyenv at: $f"
    $f --version || echo "Cannot run $f"
  done
fi

# Set PYTHONUSERBASE to ensure pip installs packages into the correct directory
export PYTHONUSERBASE=/home/appuser/.local/share/airunner/python
export PATH=/home/appuser/.local/share/airunner/python/bin:/home/appuser/.local/share/airunner/python/bin:$PATH
export PATH=$PYTHONUSERBASE/bin:$PATH

# Remove PIP_USER to avoid conflicts with --prefix
unset PIP_USER

# Ensure pip uses the correct cache directory
export PIP_CACHE_DIR=$AIRUNNER_HOME_DIR/.cache/pip

echo "PATH set to $PATH"
echo "PIP_CACHE_DIR set to $PIP_CACHE_DIR"

# Diagnostic information
echo "PYTHONUSERBASE set to $PYTHONUSERBASE"
echo "User: $(whoami)"

# Ensure the directory structure exists
mkdir -p $PYTHONUSERBASE/{bin,lib,share}

# Set up Wayland environment variables
export QT_QPA_PLATFORM=wayland
export QT_WAYLAND_DISABLE_WINDOWDECORATION=1
export QT_QPA_PLATFORMTHEME=gtk3
export GDK_BACKEND=wayland
export XDG_SESSION_TYPE=wayland

echo "===== Wayland Setup Information ====="
echo "XDG_SESSION_TYPE: $XDG_SESSION_TYPE"
echo "QT_QPA_PLATFORM: $QT_QPA_PLATFORM"
echo "GDK_BACKEND: $GDK_BACKEND"

# Handle interactive sessions
if [ "$#" -eq 0 ]; then
  echo "No command provided. Starting an interactive shell..."
  exec bash
else
  echo "Executing command: $@"
  exec "$@"
fi